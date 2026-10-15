"""Parsing Chatwoot's webhook payload shapes."""

from conversations.chatwoot_events import parse_event

CONVERSATION_CREATED_LIVE_CHAT = {
    "event": "conversation_created",
    "id": 45,
    "inbox_id": 3,
    "status": "open",
    "channel": "Channel::WebWidget",
    "created_at": "2026-10-14T10:00:00.000Z",
    "meta": {
        "sender": {
            "id": 10,
            "name": "Jamie",
            "email": "jamie@example.com",
            "phone_number": None,
            "type": "contact",
        }
    },
    "account": {"id": 7, "name": "Acme"},
}

MESSAGE_CREATED_WHATSAPP = {
    "event": "message_created",
    "id": 501,
    "content": "Hola, necesito ayuda",
    "message_type": "incoming",
    "created_at": "2026-10-14T10:05:00.000Z",
    "conversation": {
        "id": 46,
        "inbox_id": 4,
        "status": "open",
        "channel": "Channel::Whatsapp",
    },
    "sender": {
        "id": 11,
        "name": "+56912345678",
        "email": None,
        "phone_number": "+56912345678",
        "type": "contact",
    },
    "account": {"id": 7},
}

CONVERSATION_RESOLVED = {
    "event": "conversation_resolved",
    "id": 45,
    "inbox_id": 3,
    "status": "resolved",
    "channel": "Channel::WebWidget",
    "account": {"id": 7},
}


class TestParseEvent:
    def test_conversation_created_live_chat(self):
        event = parse_event(CONVERSATION_CREATED_LIVE_CHAT)
        assert event.event == "conversation_created"
        assert event.account_id == 7
        assert event.conversation_id == 45
        assert event.inbox_id == 3
        assert event.channel == "live_chat"
        assert event.status == "open"
        assert event.sender.email == "jamie@example.com"
        assert event.sender.name == "Jamie"
        assert event.message_id is None

    def test_message_created_whatsapp_reads_nested_conversation(self):
        event = parse_event(MESSAGE_CREATED_WHATSAPP)
        assert event.event == "message_created"
        assert (
            event.conversation_id == 46
        )  # from the nested object, not top-level id=501
        assert event.message_id == 501  # top-level id IS the message id here
        assert event.inbox_id == 4
        assert event.channel == "whatsapp"
        assert event.sender.phone == "+56912345678"
        assert event.content == "Hola, necesito ayuda"
        assert event.message_type == "incoming"

    def test_conversation_resolved(self):
        event = parse_event(CONVERSATION_RESOLVED)
        assert event.event == "conversation_resolved"
        assert event.status == "resolved"
        assert event.conversation_id == 45

    def test_unhandled_event_type_is_none(self):
        assert parse_event({"event": "contact_created", "id": 1}) is None

    def test_missing_event_key_is_none(self):
        assert parse_event({"id": 1}) is None

    def test_unmapped_channel_is_none_on_the_event(self):
        payload = {**CONVERSATION_CREATED_LIVE_CHAT, "channel": "Channel::Instagram"}
        event = parse_event(payload)
        assert event is not None
        assert event.channel is None

    def test_no_sender_is_none(self):
        payload = {k: v for k, v in CONVERSATION_RESOLVED.items() if k != "meta"}
        event = parse_event(payload)
        assert event.sender is None

    def test_conversation_created_contact_is_meta_sender(self):
        event = parse_event(CONVERSATION_CREATED_LIVE_CHAT)
        assert event.contact.email == "jamie@example.com"

    def test_agent_reply_is_never_the_contact(self):
        payload = {
            **MESSAGE_CREATED_WHATSAPP,
            "message_type": "outgoing",
            "sender": {
                "id": 1,
                "name": "Agent",
                "email": "agent@crm.test",
                "type": "user",
            },
        }
        event = parse_event(payload)
        assert event.sender.sender_type == "user"
        assert event.contact is None

    def test_agent_reply_takes_contact_from_conversation_meta(self):
        payload = {
            **MESSAGE_CREATED_WHATSAPP,
            "message_type": "outgoing",
            "sender": {
                "id": 1,
                "name": "Agent",
                "email": "agent@crm.test",
                "type": "user",
            },
            "conversation": {
                **MESSAGE_CREATED_WHATSAPP["conversation"],
                "meta": {
                    "sender": {
                        "id": 11,
                        "name": "Jamie",
                        "phone_number": "+56912345678",
                    }
                },
            },
        }
        event = parse_event(payload)
        assert event.sender.email == "agent@crm.test"
        assert event.contact.phone == "+56912345678"
        assert event.contact.sender_type == "contact"

    def test_timestamp_parsing_handles_z_suffix(self):
        event = parse_event(CONVERSATION_CREATED_LIVE_CHAT)
        assert event.occurred_at.year == 2026
        assert event.occurred_at.month == 10
        assert event.occurred_at.day == 14
