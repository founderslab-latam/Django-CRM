"""Parse a Chatwoot webhook delivery into a shape the ingest pipeline uses.

Chatwoot puts conversation fields at the top level of a `conversation_*`
payload, but nested under `"conversation"` on a `message_created` payload.
Verified against real deliveries from a self-hosted Chatwoot instance.

A message's `sender` is whoever wrote that message -- on an agent's reply
that's the agent (`type: "user"`), not the customer. The customer is the
conversation's `meta.sender`. Resolution must only ever use the customer,
or the first agent reply the CRM happens to see becomes a "prospect".

Only `conversation_created`, `message_created` and `conversation_resolved`
are handled. Everything else `parse_event` returns `None` for, and the
webhook view acks it with 200 anyway -- same reasoning as the inbound email
pipeline acking a dropped message: the sender already considers it delivered,
and a non-2xx here just earns pointless retries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone as dt_timezone

# Chatwoot's `channel`/`channel_type` string -> this codebase's channel
# choice (see conversations.models.CHANNEL_CHOICES). Instagram/Messenger are
# deliberately absent: they're a later addition, and an unmapped channel
# type is dropped rather than mis-filed as one of these two.
CHANNEL_MAP = {
    "Channel::WebWidget": "live_chat",
    "Channel::Whatsapp": "whatsapp",
}

HANDLED_EVENTS = frozenset(
    {"conversation_created", "message_created", "conversation_resolved"}
)


@dataclass
class ChatwootSender:
    chatwoot_contact_id: int | None
    name: str
    email: str
    phone: str
    sender_type: str


@dataclass
class ChatwootEvent:
    event: str
    account_id: int | None
    conversation_id: int | None
    inbox_id: int | None
    channel: str | None  # already mapped to our choice, or None if unmapped
    status: str
    sender: ChatwootSender | None  # who wrote this message (may be an agent)
    contact: ChatwootSender | None  # the customer on the conversation
    message_id: int | None
    message_type: str | None
    content: str
    occurred_at: datetime


def _parse_timestamp(value) -> datetime:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=dt_timezone.utc)
    if isinstance(value, str):
        try:
            text = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(dt_timezone.utc)


def _parse_sender(raw) -> ChatwootSender | None:
    if not isinstance(raw, dict):
        return None
    return ChatwootSender(
        chatwoot_contact_id=raw.get("id"),
        name=(raw.get("name") or "").strip(),
        email=(raw.get("email") or "").strip(),
        phone=(raw.get("phone_number") or "").strip(),
        sender_type=raw.get("type") or "contact",
    )


def _sender_from(payload: dict) -> ChatwootSender | None:
    return _parse_sender(
        payload.get("sender") or (payload.get("meta") or {}).get("sender")
    )


def _contact_from(payload: dict, conversation: dict) -> ChatwootSender | None:
    meta_sender = _parse_sender((conversation.get("meta") or {}).get("sender"))
    if meta_sender is not None:
        meta_sender.sender_type = "contact"
        return meta_sender
    sender = _parse_sender(payload.get("sender"))
    if sender is not None and sender.sender_type == "contact":
        return sender
    return None


def parse_event(payload: dict) -> ChatwootEvent | None:
    """Return a `ChatwootEvent`, or `None` for an event type we don't act on."""
    event = payload.get("event")
    if event not in HANDLED_EVENTS:
        return None

    account = payload.get("account") or {}
    # `message_created` nests conversation fields; `conversation_created`/
    # `conversation_resolved` carry them at the top level.
    conversation = payload.get("conversation")
    if not isinstance(conversation, dict):
        conversation = payload

    inbox = payload.get("inbox") or {}
    inbox_id = conversation.get("inbox_id") or inbox.get("id")
    raw_channel = conversation.get("channel") or inbox.get("channel_type")

    conversation_id = (
        conversation.get("id") if conversation is not payload else payload.get("id")
    )
    message_id = payload.get("id") if event == "message_created" else None

    return ChatwootEvent(
        event=event,
        account_id=account.get("id"),
        conversation_id=conversation_id,
        inbox_id=inbox_id,
        channel=CHANNEL_MAP.get(raw_channel),
        status=conversation.get("status") or "",
        sender=_sender_from(payload),
        contact=_contact_from(payload, conversation),
        message_id=message_id,
        message_type=payload.get("message_type")
        if event == "message_created"
        else None,
        content=payload.get("content") or "",
        occurred_at=_parse_timestamp(payload.get("created_at")),
    )
