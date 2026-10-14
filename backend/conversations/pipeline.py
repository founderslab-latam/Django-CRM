"""Turn one parsed Chatwoot webhook event into mirrored rows.

Shaped after `cases.inbound.pipeline.ingest`: always idempotent on the
provider's own id (a webhook retry must not duplicate a row), and contact/lead
resolution happens exactly once, when the conversation is first seen -- not
re-run on every message, so a conversation's link to a Contact/Lead stays
stable even if Chatwoot later fills in details about the sender.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .chatwoot_events import ChatwootEvent
from .models import ChatwootAccount, ChatwootConversation, ChatwootMessage
from .resolution import resolve_prospect

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    conversation: ChatwootConversation | None
    created_conversation: bool
    message: ChatwootMessage | None
    dropped: bool
    drop_reason: str = ""


def _get_or_create_conversation(event: ChatwootEvent, account: ChatwootAccount):
    """Returns `(conversation, created)`, or `(None, False)` if there isn't
    enough on this event to create one and none exists yet."""
    existing = ChatwootConversation.objects.filter(
        org=account.org,
        chatwoot_account=account,
        chatwoot_conversation_id=event.conversation_id,
    ).first()
    if existing is not None:
        return existing, False

    if event.channel is None:
        logger.warning(
            "conversations: unmapped Chatwoot channel for conversation %s "
            "(account=%s), dropping",
            event.conversation_id,
            account.id,
        )
        return None, False

    sender = event.sender
    resolved = resolve_prospect(
        account.org,
        email=sender.email if sender else "",
        phone=sender.phone if sender else "",
        name=sender.name if sender else "",
        channel=event.channel,
    )
    conversation = ChatwootConversation.objects.create(
        org=account.org,
        chatwoot_account=account,
        chatwoot_conversation_id=event.conversation_id,
        chatwoot_inbox_id=event.inbox_id or 0,
        channel=event.channel,
        contact=resolved.contact,
        lead=resolved.lead,
        status=event.status or "open",
    )
    return conversation, True


def ingest(event: ChatwootEvent, account: ChatwootAccount) -> IngestResult:
    if event.conversation_id is None:
        return IngestResult(
            conversation=None,
            created_conversation=False,
            message=None,
            dropped=True,
            drop_reason="missing_conversation_id",
        )

    with transaction.atomic():
        conversation, created = _get_or_create_conversation(event, account)
        if conversation is None:
            return IngestResult(
                conversation=None,
                created_conversation=False,
                message=None,
                dropped=True,
                drop_reason="unmapped_channel",
            )

        if event.status and conversation.status != event.status:
            conversation.status = event.status

        if event.event == "conversation_resolved" and conversation.resolved_at is None:
            conversation.status = "resolved"
            conversation.resolved_at = timezone.now()

        conversation.save()

        message = None
        if event.event == "message_created" and event.message_id is not None:
            message, _msg_created = ChatwootMessage.objects.update_or_create(
                org=account.org,
                conversation=conversation,
                chatwoot_message_id=event.message_id,
                defaults={
                    "message_type": event.message_type or "incoming",
                    "content": event.content,
                    "sender_name": event.sender.name if event.sender else "",
                    "occurred_at": event.occurred_at,
                },
            )

        return IngestResult(
            conversation=conversation,
            created_conversation=created,
            message=message,
            dropped=False,
        )


__all__ = ["IngestResult", "ingest"]
