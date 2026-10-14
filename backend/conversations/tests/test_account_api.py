"""GET/PUT/DELETE /api/conversations/account/: the org-settings singleton,
admin-only on every verb."""

import pytest

from conversations.models import ChatwootAccount

URL = "/api/conversations/account/"


@pytest.mark.django_db
class TestGet:
    def test_requires_auth(self, unauthenticated_client):
        assert unauthenticated_client.get(URL).status_code in (401, 403)

    def test_member_forbidden(self, user_client):
        assert user_client.get(URL).status_code == 403

    def test_admin_with_no_account_yet(self, admin_client):
        resp = admin_client.get(URL)
        assert resp.status_code == 200
        assert resp.json() == {"account": None}

    def test_admin_with_an_account(self, admin_client, chatwoot_account):
        resp = admin_client.get(URL)
        assert resp.status_code == 200
        body = resp.json()["account"]
        assert body["base_url"] == "https://chat.example.com"
        assert body["account_id"] == 7
        assert body["seat_limit"] == 3
        assert "api_access_token" not in body  # write-only, never echoed
        assert body["has_api_access_token"] is False
        assert body["webhook_url"].endswith(
            f"/api/public/conversations/chatwoot/{chatwoot_account.webhook_token}/"
        )

    def test_does_not_leak_another_org_s_account(
        self, admin_client, chatwoot_account_b
    ):
        resp = admin_client.get(URL)
        assert resp.json() == {"account": None}


@pytest.mark.django_db
class TestPut:
    def test_member_forbidden(self, user_client):
        assert (
            user_client.put(
                URL,
                {"base_url": "https://chat.example.com", "account_id": 1},
                format="json",
            ).status_code
            == 403
        )

    def test_creates_when_none_exists(self, admin_client, org_a):
        resp = admin_client.put(
            URL,
            {
                "base_url": "https://chat.example.com",
                "account_id": 7,
                "api_access_token": "secret-token",
                "seat_limit": 5,
            },
            format="json",
        )
        assert resp.status_code == 200
        account = ChatwootAccount.objects.get(org=org_a)
        assert account.account_id == 7
        assert account.api_access_token == "secret-token"
        assert account.seat_limit == 5
        assert resp.json()["account"]["has_api_access_token"] is True

    def test_create_requires_base_url_and_account_id(self, admin_client):
        resp = admin_client.put(URL, {"seat_limit": 2}, format="json")
        assert resp.status_code == 400

    def test_updates_existing_without_requiring_every_field(
        self, admin_client, chatwoot_account
    ):
        resp = admin_client.put(URL, {"seat_limit": 10}, format="json")
        assert resp.status_code == 200
        chatwoot_account.refresh_from_db()
        assert chatwoot_account.seat_limit == 10
        assert chatwoot_account.base_url == "https://chat.example.com"  # untouched

    def test_blank_token_on_update_does_not_clear_an_existing_one(
        self, admin_client, chatwoot_account
    ):
        chatwoot_account.api_access_token = "already-set"
        chatwoot_account.save()

        resp = admin_client.put(URL, {"api_access_token": ""}, format="json")
        assert resp.status_code == 200
        chatwoot_account.refresh_from_db()
        assert chatwoot_account.api_access_token == "already-set"

    def test_rewriting_the_token_does_overwrite(self, admin_client, chatwoot_account):
        admin_client.put(URL, {"api_access_token": "new-token"}, format="json")
        chatwoot_account.refresh_from_db()
        assert chatwoot_account.api_access_token == "new-token"

    def test_cannot_create_a_second_account_for_the_same_org(
        self, admin_client, chatwoot_account
    ):
        """PUT always targets the singleton; there is no way to end up with
        two rows for one org through this endpoint."""
        admin_client.put(
            URL,
            {"base_url": "https://chat2.example.com", "account_id": 99},
            format="json",
        )
        assert ChatwootAccount.objects.filter(org=chatwoot_account.org).count() == 1


@pytest.mark.django_db
class TestDelete:
    def test_member_forbidden(self, user_client):
        assert user_client.delete(URL).status_code == 403

    def test_admin_with_no_account_is_404(self, admin_client):
        assert admin_client.delete(URL).status_code == 404

    def test_admin_disconnects(self, admin_client, chatwoot_account, org_a):
        resp = admin_client.delete(URL)
        assert resp.status_code == 200
        assert ChatwootAccount.objects.filter(org=org_a).count() == 0

    def test_cascades_to_mirrored_conversations(self, admin_client, chatwoot_account):
        from conversations.chatwoot_events import parse_event
        from conversations.models import ChatwootConversation
        from conversations.pipeline import ingest

        payload = {
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
        ingest(parse_event(payload), chatwoot_account)
        assert ChatwootConversation.objects.count() == 1

        admin_client.delete(URL)
        assert ChatwootConversation.objects.count() == 0
