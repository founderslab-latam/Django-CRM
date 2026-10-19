"""Inbound email webhook + admin mailbox CRUD endpoints.

The webhook is intentionally public (no auth). Trust rests on two checks, and
it takes both. The signature alone is not enough:

1. `verify_sns_message` proves the payload was signed by AWS SNS. That rules
   out arbitrary JSON posted at the URL, but note what it does *not* prove:
   anyone with an AWS account can create a topic, so a valid signature only
   says the message came from *some* topic in *some* account.
2. The TopicArn pin (`InboundMailbox.topic_arn`) proves it came from *this
   mailbox's* topic. Without it, anyone who learned a mailbox UUID could point
   their own SNS topic here and have AWS sign forged mail for them, which,
   because the pipeline threads replies onto existing cases, means injecting
   messages into live customer conversations, not just spam tickets.

A mailbox with no pin rejects notifications outright; it acquires one from the
first signature-verified SubscriptionConfirmation and will not silently re-pin.

There is a third, easy-to-miss requirement underneath both: a genuinely
anonymous request carries no `Authorization` header, so `GetProfileAndOrg`
never sets `app.current_org`, and with that context empty RLS's isolation
policy hides every row of every org-scoped table -- `InboundMailbox` included.
`InboundMailbox.objects.filter(pk=mailbox_id)` would therefore find nothing
even for a real, active mailbox, which is why the lookup below goes through
`common.portal_tokens` first: an unscoped `mailbox_id → org` row (registered
on every mailbox save, see `cases.signals`) resolves the org *before* any
org-scoped table is touched, `set_rls_context` runs, and only then is the
mailbox itself read -- under full RLS, which is what actually re-confirms it
exists and is active rather than trusting the unscoped row's say-so.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta

from django.db.models import Count, Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cases.inbound import imap, smtp
from cases.inbound.hosts import MailHostError
from cases.inbound.imap import ImapError
from cases.inbound.parser import parse_raw_email
from cases.inbound.pipeline import ingest
from cases.inbound.smtp import SmtpError
from cases.inbound.sns import (
    SNSVerificationError,
    confirm_subscription,
    verify_sns_message,
)
from cases.models import EmailMessage, InboundMailbox
from cases.serializer import InboundMailboxSerializer, MailboxConnectionTestSerializer
from common.credentials import CredentialError
from common.models import PortalAccessToken
from common.permissions import HasOrgContext, is_org_admin
from common.portal_tokens import portal_token_hash, resolve_portal_org_by_hash
from common.tasks import set_rls_context

logger = logging.getLogger(__name__)

# Window the mailbox page reports ticket counts over.
MAILBOX_WINDOW_DAYS = 30


def _mailbox_analytics(org):
    """Per-mailbox ticket counts + last-received timestamp, plus an org total.

    Both come from the ``EmailMessage.mailbox`` FK (set at ingest since the
    migration): a message records exactly which inbound address it arrived
    through, so these are attributed, not guessed.

    - ``cases_last_30d`` per mailbox = distinct cases *created* in the last 30
      days that have an inbound message through that mailbox (a reply arriving
      at the address for an older case is not a new ticket, so we anchor on the
      case's ``created_at``).
    - ``last_received_at`` per mailbox = the newest inbound message's
      ``received_at`` (any message, including dropped ones, the address still
      received mail).
    - org ``cases_last_30d`` = distinct such cases across all mailboxes (not a
      sum, so a case cross-posted to two addresses is not double counted).

    All scoped to ``org`` explicitly (RLS is inert in dev/test).
    """
    cutoff = timezone.now() - timedelta(days=MAILBOX_WINDOW_DAYS)
    inbound = EmailMessage.objects.filter(
        org=org, direction="inbound", mailbox__isnull=False
    )
    created = (
        inbound.filter(case__isnull=False, case__created_at__gte=cutoff)
        .values("mailbox_id")
        .annotate(n=Count("case", distinct=True))
    )
    cases_by_mailbox = {str(row["mailbox_id"]): row["n"] for row in created}
    last = inbound.values("mailbox_id").annotate(last=Max("received_at"))
    last_by_mailbox = {str(row["mailbox_id"]): row["last"] for row in last}
    total_cases = (
        inbound.filter(case__isnull=False, case__created_at__gte=cutoff)
        .values("case")
        .distinct()
        .count()
    )
    return cases_by_mailbox, last_by_mailbox, total_cases


def _admin_required():
    return Response(
        {"error": True, "errors": _("Admin access required")},
        status=status.HTTP_403_FORBIDDEN,
    )


def _topic_rejected():
    """Deliberately as opaque as the signature failure. A caller probing the
    webhook shouldn't learn whether a mailbox is pinned or to what."""
    return Response(
        {"error": True, "errors": _("Signature verification failed")},
        status=status.HTTP_403_FORBIDDEN,
    )


class InboundMailboxWebhookView(APIView):
    """Public endpoint where AWS SNS POSTs for one configured mailbox.

    URL: `/api/cases/inbound/<mailbox_id>/`. The mailbox lookup also acts as
    the org boundary, the URL embeds the per-mailbox UUID so the webhook
    can't be confused for one belonging to a different tenant.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["InboundEmail"],
        request=inline_serializer(
            name="SNSInboundPayload",
            fields={
                "Type": serializers.CharField(),
                "Message": serializers.CharField(),
                "Signature": serializers.CharField(),
                "SigningCertURL": serializers.CharField(),
            },
        ),
        responses={
            200: inline_serializer(
                name="InboundWebhookResponse",
                fields={
                    "ok": serializers.BooleanField(),
                    "case_id": serializers.CharField(allow_null=True, required=False),
                    "dropped": serializers.BooleanField(required=False),
                    "reason": serializers.CharField(required=False),
                },
            )
        },
    )
    def post(self, request, mailbox_id, *args, **kwargs):
        # With no Authorization header, `app.current_org` is still empty here
        # -- RLS hides InboundMailbox under that context regardless of what
        # the ORM filter asks for, so a direct `.filter(pk=mailbox_id)` would
        # find nothing even for a real, active mailbox. Resolve the org from
        # the unscoped lookup first; see the module docstring.
        org_id = resolve_portal_org_by_hash(
            portal_token_hash(str(mailbox_id)), PortalAccessToken.INBOUND_MAILBOX
        )
        if org_id is None:
            # Don't leak which UUIDs exist; return a generic 404.
            return Response(
                {"error": True, "errors": _("Mailbox not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        # The webhook bypasses RLSContextMiddleware, so set it manually before
        # any ORM read/write touches an org-scoped table.
        set_rls_context(org_id)

        # Re-read under full RLS now that context is set. This is the real
        # check -- the unscoped row above only says a mailbox with this id
        # once existed in this org, not that it still does or is active.
        mailbox = (
            InboundMailbox.objects.filter(pk=mailbox_id, is_active=True)
            .select_related("org")
            .first()
        )
        if mailbox is None:
            return Response(
                {"error": True, "errors": _("Mailbox not found")},
                status=status.HTTP_404_NOT_FOUND,
            )

        if mailbox.provider != "ses":
            # Other providers wired into the same URL space land here.
            return Response(
                {
                    "error": True,
                    "errors": _("Provider %(provider)r not yet supported")
                    % {"provider": mailbox.provider},
                },
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        # SNS posts the JSON body in `request.body`. DRF may have parsed it.
        try:
            payload = (
                request.data
                if isinstance(request.data, dict)
                else json.loads(request.body or b"{}")
            )
        except (ValueError, TypeError):
            return Response(
                {"error": True, "errors": _("Body is not valid JSON")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verify_sns_message(payload)
        except SNSVerificationError as exc:
            logger.warning(
                "SNS verification failed for mailbox=%s: %s", mailbox.id, exc
            )
            return Response(
                {"error": True, "errors": _("Signature verification failed")},
                status=status.HTTP_403_FORBIDDEN,
            )

        # A valid signature only proves the message came from *some* SNS topic
        # in *some* AWS account. Pin it to this mailbox's topic, or anyone who
        # learns the mailbox UUID can have AWS sign forged mail for them.
        msg_type = payload.get("Type")
        topic_arn = payload.get("TopicArn") or ""
        pinned = mailbox.topic_arn or ""
        if pinned:
            if topic_arn != pinned:
                logger.warning(
                    "SNS TopicArn mismatch for mailbox=%s: got %r",
                    mailbox.id,
                    topic_arn,
                )
                return _topic_rejected()
        elif msg_type == "SubscriptionConfirmation" and topic_arn:
            # Trust-on-first-use: the confirmation is signature-verified above,
            # and this is the only moment a mailbox can acquire its pin.
            mailbox.topic_arn = topic_arn
            mailbox.save(update_fields=["topic_arn"])
            logger.info("Pinned mailbox=%s to TopicArn=%r", mailbox.id, topic_arn)
        else:
            # Unpinned mailbox, and this message can't establish a pin.
            logger.warning(
                "Rejecting SNS message for unpinned mailbox=%s (type=%r)",
                mailbox.id,
                msg_type,
            )
            return _topic_rejected()

        if msg_type == "SubscriptionConfirmation":
            try:
                confirm_subscription(payload)
            except Exception:
                logger.exception("SNS subscription confirmation failed")
                return Response(
                    {"error": True, "errors": _("SubscribeURL fetch failed")},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            return Response({"ok": True, "subscribed": True})

        if msg_type == "UnsubscribeConfirmation":  # pragma: no cover: informational
            logger.info("SNS unsubscribe for mailbox=%s", mailbox.id)
            return Response({"ok": True, "unsubscribed": True})

        if msg_type != "Notification":
            return Response(
                {
                    "error": True,
                    "errors": _("Unsupported SNS Type: %(type)r") % {"type": msg_type},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # SES with "SNS Notification with full content" puts the raw RFC-5322
        # email in payload.Message as a plain string. Older SES configurations
        # send a JSON envelope (`{"notificationType":"Received","content":"..."}`);
        # peel that off if we see it.
        raw_message = payload.get("Message", "") or ""
        try:
            envelope = json.loads(raw_message)
            if isinstance(envelope, dict) and "content" in envelope:
                raw_message = envelope.get("content") or ""
        except (ValueError, TypeError):
            pass

        if not raw_message:
            return Response(
                {"error": True, "errors": _("SNS Message body is empty")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        parsed = parse_raw_email(raw_message)
        result = ingest(parsed, mailbox)

        return Response(
            {
                "ok": True,
                "case_id": str(result.case.id) if result.case else None,
                "dropped": result.dropped,
                "reason": result.drop_reason,
                "created_case": result.created_case,
            },
            status=status.HTTP_200_OK,
        )


class InboundMailboxListCreateView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["InboundEmail"], responses={200: InboundMailboxSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        org = request.profile.org
        qs = InboundMailbox.objects.filter(org=org).order_by("address")
        mailboxes = InboundMailboxSerializer(
            qs, many=True, context={"request": request}
        ).data
        cases_by, last_by, total_cases = _mailbox_analytics(org)
        active = 0
        for mbx in mailboxes:
            mid = str(mbx["id"])
            mbx["cases_last_30d"] = cases_by.get(mid, 0)
            received = last_by.get(mid)
            mbx["last_received_at"] = received.isoformat() if received else None
            if mbx["is_active"]:
                active += 1
        totals = {
            "count": len(mailboxes),
            "active": active,
            "cases_last_30d": total_cases,
        }
        return Response({"mailboxes": mailboxes, "totals": totals})

    @extend_schema(
        tags=["InboundEmail"],
        request=InboundMailboxSerializer,
        responses={201: InboundMailboxSerializer},
    )
    def post(self, request, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        org = request.profile.org
        # No webhook secret is generated here. This used to mint a
        # `secrets.token_urlsafe(32)` when the body carried none, and nothing
        # ever compared the result: SES delivery is authenticated by the SNS
        # signature plus the `topic_arn` pin, both handled in
        # `InboundMailboxWebhookView.post`. Now that the field is write-only,
        # a generated value could not be read back either, so every mailbox
        # would carry a secret no one holds. An empty column reads honestly as
        # "not configured", which is also what a future provider integration
        # needs in order to tell configured mailboxes from unconfigured ones.
        serializer = InboundMailboxSerializer(
            data=request.data, context={"org": org, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save(org=org)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InboundMailboxTestConnectionView(APIView):
    """`POST /api/cases/mailboxes/test-connection/`: try the IMAP login +
    folder and the SMTP login with the settings as typed, before saving.
    Admin-only; sends no mail and reads none. Both halves always run, so the
    form can show which one is wrong."""

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["InboundEmail"],
        request=MailboxConnectionTestSerializer,
        responses={
            200: inline_serializer(
                name="MailboxConnectionTestResponse",
                fields={
                    "imap": serializers.DictField(),
                    "smtp": serializers.DictField(),
                },
            )
        },
    )
    def post(self, request, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        serializer = MailboxConnectionTestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data

        stored = None
        if data.get("mailbox_id"):
            stored = InboundMailbox.objects.filter(
                pk=data["mailbox_id"], org=request.profile.org
            ).first()

        def stored_password(field):
            if stored is None:
                return ""
            try:
                if field == "imap":
                    return stored.imap_password()
                return stored.smtp_login()[1] if stored.smtp_username else ""
            except CredentialError:
                return ""

        imap_password = data.get("imap_password") or stored_password("imap")
        smtp_username = data.get("smtp_username") or data["imap_username"]
        smtp_password = data.get("smtp_password") or (
            stored_password("smtp") if data.get("smtp_username") else imap_password
        )

        def outcome(check):
            try:
                check()
            except (ImapError, SmtpError, MailHostError) as exc:
                return {"ok": False, "error": str(exc)}
            return {"ok": True, "error": ""}

        return Response(
            {
                "imap": outcome(
                    lambda: imap.check_connection(
                        data["imap_host"],
                        data.get("imap_port"),
                        data["imap_security"],
                        data["imap_username"],
                        imap_password,
                        data.get("imap_folder") or "INBOX",
                    )
                ),
                "smtp": outcome(
                    lambda: smtp.check_connection(
                        data["smtp_host"],
                        data.get("smtp_port"),
                        data["smtp_security"],
                        smtp_username,
                        smtp_password,
                    )
                ),
            }
        )


class InboundMailboxDetailView(APIView):
    permission_classes = (IsAuthenticated, HasOrgContext)

    def _get_object(self, pk, org):
        return InboundMailbox.objects.filter(pk=pk, org=org).first()

    @extend_schema(tags=["InboundEmail"], responses={200: InboundMailboxSerializer})
    def get(self, request, pk, *args, **kwargs):
        obj = self._get_object(pk, request.profile.org)
        if not obj:
            return Response(
                {"error": True, "errors": _("Mailbox not found")},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            InboundMailboxSerializer(obj, context={"request": request}).data
        )

    @extend_schema(
        tags=["InboundEmail"],
        request=InboundMailboxSerializer,
        responses={200: InboundMailboxSerializer},
    )
    def put(self, request, pk, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        org = request.profile.org
        obj = self._get_object(pk, org)
        if not obj:
            return Response(
                {"error": True, "errors": _("Mailbox not found")},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = InboundMailboxSerializer(
            obj,
            data=request.data,
            partial=True,
            context={"org": org, "request": request},
        )
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["InboundEmail"],
        responses={
            200: inline_serializer(
                name="MailboxDeleteResponse",
                fields={
                    "error": serializers.BooleanField(),
                    "message": serializers.CharField(),
                },
            )
        },
    )
    def delete(self, request, pk, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        obj = self._get_object(pk, request.profile.org)
        if not obj:
            return Response(
                {"error": True, "errors": _("Mailbox not found")},
                status=status.HTTP_404_NOT_FOUND,
            )
        obj.delete()
        return Response({"error": False, "message": _("Mailbox deleted")})
