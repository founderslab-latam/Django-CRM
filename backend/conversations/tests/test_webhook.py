"""HTTP-level tests for the Chatwoot webhook: auth, reachability, isolation.

See conversations/tests/test_pipeline.py for ingestion behaviour and
test_chatwoot_events.py for payload parsing; this file is only about the
endpoint itself.
"""

import pytest

from conversations.models import ChatwootConversation

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


def _url(account):
    return f"/api/public/conversations/chatwoot/{account.webhook_token}/"


@pytest.mark.django_db
class TestChatwootWebhook:
    def test_wrong_token_is_404(self, unauthenticated_client):
        resp = unauthenticated_client.post(
            "/api/public/conversations/chatwoot/not-a-real-token/",
            CONVERSATION_CREATED,
            format="json",
        )
        assert resp.status_code == 404

    def test_inactive_account_is_404(self, unauthenticated_client, chatwoot_account):
        chatwoot_account.is_active = False
        chatwoot_account.save()
        resp = unauthenticated_client.post(
            _url(chatwoot_account), CONVERSATION_CREATED, format="json"
        )
        assert resp.status_code == 404

    def test_reachable_with_no_credential_at_all(
        self, unauthenticated_client, chatwoot_account
    ):
        """The point of the whole design: Chatwoot sends no Authorization
        header, ever. This must not 403 at the middleware before the view
        (the token in the URL) gets a chance to authenticate it."""
        resp = unauthenticated_client.post(
            _url(chatwoot_account), CONVERSATION_CREATED, format="json"
        )
        assert resp.status_code == 200
        assert resp.json()["conversation_created"] is True

    def test_creates_a_mirrored_conversation(
        self, unauthenticated_client, chatwoot_account, org_a
    ):
        unauthenticated_client.post(
            _url(chatwoot_account), CONVERSATION_CREATED, format="json"
        )
        conv = ChatwootConversation.objects.get(org=org_a)
        assert conv.chatwoot_conversation_id == 45
        assert conv.contact.email == "jamie@example.com"

    def test_unhandled_event_is_ignored_not_an_error(
        self, unauthenticated_client, chatwoot_account
    ):
        resp = unauthenticated_client.post(
            _url(chatwoot_account),
            {"event": "contact_created", "id": 1},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json() == {"ignored": True}

    def test_malformed_body_is_400(self, unauthenticated_client, chatwoot_account):
        resp = unauthenticated_client.post(
            _url(chatwoot_account), ["not", "a", "dict"], format="json"
        )
        assert resp.status_code == 400

    def test_one_org_s_webhook_cannot_write_into_another(
        self, unauthenticated_client, chatwoot_account, chatwoot_account_b, org_a, org_b
    ):
        unauthenticated_client.post(
            _url(chatwoot_account), CONVERSATION_CREATED, format="json"
        )
        unauthenticated_client.post(
            _url(chatwoot_account_b), CONVERSATION_CREATED, format="json"
        )

        assert ChatwootConversation.objects.filter(org=org_a).count() == 1
        assert ChatwootConversation.objects.filter(org=org_b).count() == 1
        assert (
            ChatwootConversation.objects.get(org=org_a).chatwoot_account_id
            == chatwoot_account.id
        )
