"""Authenticated read API for the CRM UI: which Chatwoot conversations belong
to a given Contact or Lead, so a panel on their detail page can list them and
link into Chatwoot's own agent dashboard.

No SSO between BottleCRM and Chatwoot exists yet -- an agent opening
`embed_url` (see `conversations/serializer.py`) needs to already be signed in
to Chatwoot in that browser. Wiring real single sign-on (Chatwoot's Platform
API can mint a one-time login link for an agent) is a follow-up, not
blocking: agents already have Chatwoot accounts during this phase, and a
second login once per browser session is a one-time cost, not a per-visit one.
"""

from __future__ import annotations

from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext, is_org_admin

from .models import ChatwootAccount, ChatwootConversation, ChatwootMessage
from .serializer import ChatwootAccountSerializer, ChatwootConversationSerializer


def _admin_required():
    return Response(
        {"error": True, "errors": _("Admin access required")},
        status=status.HTTP_403_FORBIDDEN,
    )


class ChatwootConversationListView(APIView):
    """`GET /api/conversations/chatwoot/?contact=<id>` or `?lead=<id>`.

    Exactly one of the two is required. Both resolve against the caller's
    own org only -- an id from another tenant answers the same empty list a
    nonexistent id would, rather than a 404 that would confirm whose id
    space it belongs to (consistent with `common.lookups.get_scoped_or_404`'s
    reasoning, applied here as a filter instead of a lookup since there is no
    single object to 404 against).
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["conversations"],
        responses={200: ChatwootConversationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        org = request.profile.org
        contact_id = request.query_params.get("contact")
        lead_id = request.query_params.get("lead")

        if bool(contact_id) == bool(lead_id):
            return Response(
                {"detail": "Pass exactly one of ?contact= or ?lead=."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if contact_id:
            queryset = ChatwootConversation.objects.filter(
                org=org, contact_id=contact_id, contact__org=org
            )
        else:
            queryset = ChatwootConversation.objects.filter(
                org=org, lead_id=lead_id, lead__org=org
            )

        # Empty-content messages are Chatwoot's form prompts (e.g. the
        # "get notified by email" input), nothing a transcript can show.
        transcript = (
            ChatwootMessage.objects.filter(org=org)
            .exclude(content="")
            .order_by("occurred_at", "chatwoot_message_id")
        )
        queryset = (
            queryset.select_related("chatwoot_account")
            .prefetch_related(Prefetch("messages", queryset=transcript))
            .order_by("-created_at")
        )
        return Response(ChatwootConversationSerializer(queryset, many=True).data)


class ChatwootAccountView(APIView):
    """`/api/conversations/account/`: the org's own ChatwootAccount, admin-only
    on every verb -- unlike the conversation list above, nothing here needs
    to be readable by an ordinary member. There is at most one row per org
    (`ChatwootAccount` enforces that with a UniqueConstraint on `org`), and
    unlike `cases.views.ReopenPolicyView`'s singleton it is NOT auto-created
    on first read: `base_url`/`account_id` have no sane default, so GET
    answers `{"account": null}` until an admin actually configures one via
    PUT.
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    def _get(self, org):
        return ChatwootAccount.objects.filter(org=org).first()

    @extend_schema(
        tags=["conversations"],
        responses={200: ChatwootAccountSerializer},
    )
    def get(self, request, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        account = self._get(request.profile.org)
        if account is None:
            return Response({"account": None})
        return Response(
            {
                "account": ChatwootAccountSerializer(
                    account, context={"request": request}
                ).data
            }
        )

    @extend_schema(
        tags=["conversations"],
        request=ChatwootAccountSerializer,
        responses={200: ChatwootAccountSerializer},
    )
    def put(self, request, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        org = request.profile.org
        instance = self._get(org)
        serializer = ChatwootAccountSerializer(
            instance,
            data=request.data,
            partial=instance is not None,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(
                {"error": True, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save(org=org)
        return Response({"account": serializer.data})

    @extend_schema(
        tags=["conversations"],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "error": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            }
        },
    )
    def delete(self, request, *args, **kwargs):
        if not is_org_admin(request.profile):
            return _admin_required()
        account = self._get(request.profile.org)
        if account is None:
            return Response(
                {"error": True, "errors": _("No Chatwoot account configured")},
                status=status.HTTP_404_NOT_FOUND,
            )
        # CASCADEs to every mirrored ChatwootConversation/ChatwootMessage for
        # this org -- disconnecting the integration is meant to take its
        # mirrored history with it, not leave orphaned rows an admin can't
        # see or clean up through any UI.
        account.delete()
        return Response({"error": False, "message": _("Chatwoot account disconnected")})
