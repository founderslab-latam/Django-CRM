"""Chatwoot webhook: Live Chat + WhatsApp messages land here.

Public by design, same shape as the inbound-email webhook
(`cases.inbound_views.InboundMailboxWebhookView`) and for the same reason:
the sender (Chatwoot) carries no credential of ours. Unlike AWS SNS, Chatwoot
does not sign its deliveries at all, so the secret in the URL path
(`ChatwootAccount.webhook_token`) is the *only* authentication -- there is no
second, cryptographic factor to pair it with the way SNS's TopicArn pin backs
up its signature. Treat the URL itself as a credential: it must never be
logged, and `webhook_token` is only ever looked up, never returned by any API.

A request with no Authorization header never gets `app.current_org` set by
`GetProfileAndOrg`, and with that context empty RLS's isolation policy hides
every row of every org-scoped table -- `ChatwootAccount` included. A direct
`.filter(webhook_token=...)` would therefore find nothing even for a real,
active account, so the lookup below goes through `common.portal_tokens`
first: an unscoped `webhook_token → org` row (registered on every account
save, see `conversations.signals`) resolves the org *before* any org-scoped
table is touched. Confirmed this failure mode first-hand, live, against this
feature's own webhook, which is what prompted the identical fix on the
inbound-email webhook in `cases/inbound_views.py`.
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import PortalAccessToken
from common.portal_tokens import portal_token_hash, resolve_portal_org_by_hash
from common.tasks import set_rls_context

from .chatwoot_events import parse_event
from .models import ChatwootAccount
from .pipeline import ingest

logger = logging.getLogger(__name__)


class ChatwootWebhookView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["conversations"],
        request=inline_serializer(name="ChatwootWebhookRequest", fields={}),
        responses={
            200: inline_serializer(
                name="ChatwootWebhookResponse",
                fields={
                    "dropped": serializers.BooleanField(),
                    "drop_reason": serializers.CharField(),
                    "conversation_created": serializers.BooleanField(),
                },
            )
        },
    )
    def post(self, request, webhook_token, *args, **kwargs):
        # See the module docstring: resolve the org from the unscoped lookup
        # before touching ChatwootAccount at all, or RLS hides it.
        org_id = resolve_portal_org_by_hash(
            portal_token_hash(webhook_token), PortalAccessToken.CHATWOOT_WEBHOOK
        )
        if org_id is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        set_rls_context(org_id)

        # Re-read under full RLS now that context is set -- the real check.
        # The unscoped row above only says this token once belonged to this
        # org, not that the account is still there or still active.
        account = ChatwootAccount.objects.filter(
            webhook_token=webhook_token, is_active=True
        ).first()
        if account is None:
            # Same body regardless of "unknown token" vs "deactivated
            # account" -- neither should tell an unauthenticated caller which.
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = request.data
        if not isinstance(payload, dict):
            return Response(
                {"detail": "Malformed payload."}, status=status.HTTP_400_BAD_REQUEST
            )

        event = parse_event(payload)
        if event is None:
            # An event type we don't act on yet (contact_created, typing
            # indicators, ...). Ack it so Chatwoot doesn't retry forever.
            return Response({"ignored": True}, status=status.HTTP_200_OK)

        if event.account_id is not None and event.account_id != account.account_id:
            logger.warning(
                "conversations: webhook account_id %s does not match the "
                "token's account %s (org=%s) -- processing anyway, the URL "
                "token is the actual trust boundary here",
                event.account_id,
                account.account_id,
                account.org_id,
            )

        result = ingest(event, account)
        return Response(
            {
                "dropped": result.dropped,
                "drop_reason": result.drop_reason,
                "conversation_created": result.created_conversation,
            },
            status=status.HTTP_200_OK,
        )
