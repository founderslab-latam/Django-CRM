import pytest

from contacts.models import Contact
from conversations.chatwoot_events import parse_event
from conversations.models import ChatwootConversation, ChatwootMessage
from conversations.pipeline import ingest

CONVERSATION_CREATED = {
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
    "account": {"id": 7},
}

MESSAGE_CREATED = {
    "event": "message_created",
    "id": 501,
    "content": "Hola, necesito ayuda",
    "message_type": "incoming",
    "created_at": "2026-10-14T10:05:00.000Z",
    "conversation": {
        "id": 45,
        "inbox_id": 3,
        "status": "open",
        "channel": "Channel::WebWidget",
    },
    "sender": {
        "id": 10,
        "name": "Jamie",
        "email": "jamie@example.com",
        "phone_number": None,
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


@pytest.mark.django_db
class TestIngest:
    def test_conversation_created_resolves_and_creates_prospect(self, chatwoot_account):
        event = parse_event(CONVERSATION_CREATED)
        result = ingest(event, chatwoot_account)

        assert result.dropped is False
        assert result.created_conversation is True
        conv = result.conversation
        assert conv.chatwoot_conversation_id == 45
        assert conv.channel == "live_chat"
        assert conv.contact is not None
        assert conv.contact.email == "jamie@example.com"
        assert conv.lead is not None  # brand new prospect, both created

    def test_message_created_appends_to_the_conversation(self, chatwoot_account):
        ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)
        result = ingest(parse_event(MESSAGE_CREATED), chatwoot_account)

        assert result.dropped is False
        assert result.created_conversation is False  # already existed
        assert result.message is not None
        assert result.message.content == "Hola, necesito ayuda"
        assert (
            ChatwootMessage.objects.filter(conversation=result.conversation).count()
            == 1
        )

    def test_message_created_before_conversation_created_still_works(
        self, chatwoot_account
    ):
        """Webhook delivery order isn't guaranteed; the first event we see
        for an unknown conversation id must still resolve+create it."""
        result = ingest(parse_event(MESSAGE_CREATED), chatwoot_account)
        assert result.created_conversation is True
        assert result.conversation.contact.email == "jamie@example.com"

    def test_duplicate_message_is_idempotent(self, chatwoot_account):
        ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)
        ingest(parse_event(MESSAGE_CREATED), chatwoot_account)
        ingest(parse_event(MESSAGE_CREATED), chatwoot_account)  # webhook retry

        assert ChatwootMessage.objects.count() == 1

    def test_resolution_runs_once_not_per_message(self, chatwoot_account, org_a):
        """A second message from the same sender must not create a second
        Contact/Lead -- the conversation is already linked."""
        ingest(parse_event(MESSAGE_CREATED), chatwoot_account)
        second_message = {**MESSAGE_CREATED, "id": 502, "content": "Still there?"}
        ingest(parse_event(second_message), chatwoot_account)

        assert Contact.objects.filter(org=org_a).count() == 1
        assert ChatwootMessage.objects.count() == 2

    def test_agent_reply_seen_first_links_the_customer_not_the_agent(
        self, chatwoot_account, org_a
    ):
        """A conversation that existed in Chatwoot before the webhook was
        wired up: the first event the CRM sees may be an agent's reply."""
        agent_reply = {
            **MESSAGE_CREATED,
            "message_type": "outgoing",
            "sender": {
                "id": 1,
                "name": "Agent",
                "email": "agent@crm.test",
                "type": "user",
            },
            "conversation": {
                **MESSAGE_CREATED["conversation"],
                "meta": {"sender": CONVERSATION_CREATED["meta"]["sender"]},
            },
        }
        result = ingest(parse_event(agent_reply), chatwoot_account)

        assert result.conversation.contact.email == "jamie@example.com"
        assert result.message.sender_name == "Agent"
        assert not Contact.objects.filter(org=org_a, email="agent@crm.test").exists()

    def test_agent_reply_without_customer_info_links_nobody(
        self, chatwoot_account, org_a
    ):
        agent_reply = {
            **MESSAGE_CREATED,
            "message_type": "outgoing",
            "sender": {
                "id": 1,
                "name": "Agent",
                "email": "agent@crm.test",
                "type": "user",
            },
        }
        result = ingest(parse_event(agent_reply), chatwoot_account)

        assert result.conversation.contact is None
        assert result.conversation.lead is None
        assert not Contact.objects.filter(org=org_a).exists()

    def test_conversation_resolved_marks_resolved(self, chatwoot_account):
        ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)
        result = ingest(parse_event(CONVERSATION_RESOLVED), chatwoot_account)

        assert result.conversation.status == "resolved"
        assert result.conversation.resolved_at is not None

    def test_unmapped_channel_is_dropped_not_half_created(self, chatwoot_account):
        payload = {**CONVERSATION_CREATED, "channel": "Channel::Instagram"}
        result = ingest(parse_event(payload), chatwoot_account)

        assert result.dropped is True
        assert result.drop_reason == "unmapped_channel"
        assert ChatwootConversation.objects.count() == 0

    def test_second_org_s_chatwoot_account_gets_its_own_conversation_id_space(
        self, chatwoot_account, chatwoot_account_b, org_b
    ):
        """Chatwoot conversation ids are per Chatwoot account, not globally
        unique -- two orgs can legitimately see the same numeric id."""
        ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)
        result_b = ingest(parse_event(CONVERSATION_CREATED), chatwoot_account_b)

        assert result_b.created_conversation is True
        assert (
            ChatwootConversation.objects.filter(chatwoot_conversation_id=45).count()
            == 2
        )
        assert result_b.conversation.org_id == org_b.id
