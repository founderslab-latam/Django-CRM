"""GET /api/conversations/chatwoot/?contact=|lead=: the authenticated panel
the Contact/Lead detail pages use to list and link into Chatwoot."""

import pytest

from conversations.chatwoot_events import parse_event
from conversations.pipeline import ingest

URL = "/api/conversations/chatwoot/"

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


@pytest.mark.django_db
class TestChatwootConversationListView:
    def test_requires_auth(self, unauthenticated_client):
        resp = unauthenticated_client.get(URL, {"contact": "whatever"})
        assert resp.status_code in (401, 403)

    def test_requires_exactly_one_filter(self, admin_client):
        assert admin_client.get(URL).status_code == 400
        assert admin_client.get(URL, {"contact": "a", "lead": "b"}).status_code == 400

    def test_lists_conversations_for_a_contact(self, admin_client, chatwoot_account):
        result = ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)
        contact = result.conversation.contact

        resp = admin_client.get(URL, {"contact": str(contact.id)})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["channel"] == "live_chat"
        assert body[0]["chatwoot_conversation_id"] == 45
        assert body[0]["embed_url"] == (
            "https://chat.example.com/app/accounts/7/conversations/45"
        )

    def test_lists_conversations_for_a_lead(self, admin_client, chatwoot_account):
        result = ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)
        lead = result.conversation.lead

        resp = admin_client.get(URL, {"lead": str(lead.id)})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_includes_the_transcript_in_order_without_empty_prompts(
        self, admin_client, chatwoot_account
    ):
        result = ingest(parse_event(CONVERSATION_CREATED), chatwoot_account)

        def message(msg_id, content, message_type, minute, sender):
            return {
                "event": "message_created",
                "id": msg_id,
                "content": content,
                "message_type": message_type,
                "created_at": f"2026-10-14T10:{minute:02d}:00.000Z",
                "conversation": {
                    "id": 45,
                    "inbox_id": 3,
                    "channel": "Channel::WebWidget",
                },
                "sender": sender,
                "account": {"id": 7},
            }

        jamie = CONVERSATION_CREATED["meta"]["sender"]
        agent = {"id": 1, "name": "Agent", "type": "user"}
        for payload in (
            message(503, "Te cotizo enseguida", "outgoing", 7, agent),
            message(501, "Hola, necesito ayuda", "incoming", 5, jamie),
            message(502, "", "template", 6, agent),
        ):
            ingest(parse_event(payload), chatwoot_account)

        resp = admin_client.get(URL, {"contact": str(result.conversation.contact.id)})
        transcript = resp.json()[0]["messages"]
        assert [m["content"] for m in transcript] == [
            "Hola, necesito ayuda",
            "Te cotizo enseguida",
        ]
        assert transcript[0]["message_type"] == "incoming"
        assert transcript[1]["sender_name"] == "Agent"

    def test_unknown_contact_is_an_empty_list_not_404(self, admin_client):
        import uuid

        resp = admin_client.get(URL, {"contact": str(uuid.uuid4())})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_another_org_s_contact_is_an_empty_list(
        self, admin_client, chatwoot_account_b, org_b
    ):
        """A contact id that is real, but belongs to org_b, must not leak
        org_b's conversation into org_a's response."""
        result = ingest(parse_event(CONVERSATION_CREATED), chatwoot_account_b)
        other_contact = result.conversation.contact
        assert other_contact.org_id == org_b.id

        resp = admin_client.get(URL, {"contact": str(other_contact.id)})
        assert resp.status_code == 200
        assert resp.json() == []
