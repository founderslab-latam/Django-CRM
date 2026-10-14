"""Chatwoot webhook: Live Chat + WhatsApp messages land here.

Public by design, same shape as the inbound-email webhook
(`cases.inbound_views.InboundMailboxWebhookView`) and for the same reason:
the sender (Chatwoot) carries no credential of ours. Unlike AWS SNS, Chatwoot
does not sign its deliveries at all, so the secret in the URL path
(`ChatwootAccount.webhook_token`) is the *only* authentication -- there is no
second, cryptographic factor to pair it with the way SNS's TopicArn pin backs
up its signature. Treat the URL itself as a credential: it must never be
logged, and `webhook_token` is only ever looked up, never returned by any API.
"""

from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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
        account = ChatwootAccount.objects.filter(
            webhook_token=webhook_token, is_active=True
        ).first()
        if account is None:
            # Same body regardless of "unknown token" vs "deactivated
            # account" -- neither should tell an unauthenticated caller which.
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        set_rls_context(account.org_id)

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
