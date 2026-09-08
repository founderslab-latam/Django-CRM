"""
Operator console: /api/operator/orgs/ — superuser-only tenant administration.

Run with: pytest common/tests/test_operator_console.py -v
"""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from common.models import MagicLinkToken, Org, Profile, User
from common.serializer import OrgAwareRefreshToken

LIST_URL = "/api/operator/orgs/"


@pytest.fixture
def superuser(db):
    u = User.objects.create_user(email="op@test.com", password="x")
    u.is_superuser = True
    u.is_staff = True
    u.save(update_fields=["is_superuser", "is_staff"])
    return u


@pytest.fixture
def operator_client(superuser):
    client = APIClient()
    token = OrgAwareRefreshToken.for_user_and_org(superuser, None)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
class TestOperatorAuth:
    def test_anonymous_is_403(self):
        assert APIClient().get(LIST_URL).status_code in (401, 403)

    def test_org_admin_non_superuser_is_403(self, admin_client, org_a):
        assert admin_client.get(LIST_URL).status_code == 403

    def test_superuser_is_allowed(self, operator_client):
        assert operator_client.get(LIST_URL).status_code == 200

    @override_settings(OPERATOR_API_KEY="s3cr3t-op-key")
    def test_api_key_header_is_allowed(self):
        r = APIClient().get(LIST_URL, HTTP_X_OPERATOR_KEY="s3cr3t-op-key")
        assert r.status_code == 200

    @override_settings(OPERATOR_API_KEY="s3cr3t-op-key")
    def test_wrong_api_key_is_403(self):
        r = APIClient().get(LIST_URL, HTTP_X_OPERATOR_KEY="nope")
        assert r.status_code in (401, 403)

    def test_api_key_ignored_when_setting_empty(self):
        # OPERATOR_API_KEY defaults to "" -> the header path is off.
        r = APIClient().get(LIST_URL, HTTP_X_OPERATOR_KEY="anything")
        assert r.status_code in (401, 403)


@pytest.mark.django_db
class TestOperatorOrgCrud:
    def test_list_spans_every_org(self, operator_client, org_a, org_b):
        names = {o["name"] for o in operator_client.get(LIST_URL).json()["organizations"]}
        assert {org_a.name, org_b.name} <= names

    def test_list_status_filter(self, operator_client, org_a, org_b):
        org_b.status = "SUSPENDED"
        org_b.save()
        r = operator_client.get(LIST_URL + "?status=suspended").json()["organizations"]
        assert [o["name"] for o in r] == [org_b.name]

    def test_create_minimal(self, operator_client):
        r = operator_client.post(LIST_URL, {"name": "Nimbus SA"}, format="json")
        assert r.status_code == 201
        org = r.json()["organization"]
        assert org["status"] == "ACTIVE"
        assert org["routing_key"]
        assert org["cname_target"].startswith(org["routing_key"] + ".")
        assert Org.objects.filter(name="Nimbus SA").exists()

    def test_create_with_subdomain(self, operator_client):
        r = operator_client.post(
            LIST_URL,
            {"name": "Acme", "subdomain": "ACME", "default_currency": "CLP"},
            format="json",
        )
        assert r.status_code == 201
        assert Org.objects.get(name="Acme").subdomain == "acme"

    def test_create_rejects_duplicate_subdomain(self, operator_client):
        operator_client.post(LIST_URL, {"name": "A", "subdomain": "dup"}, format="json")
        r = operator_client.post(
            LIST_URL, {"name": "B", "subdomain": "dup"}, format="json"
        )
        assert r.status_code == 400
        assert "subdomain" in r.json()

    def test_create_rejects_reserved_subdomain(self, operator_client):
        r = operator_client.post(
            LIST_URL, {"name": "A", "subdomain": "admin"}, format="json"
        )
        assert r.status_code == 400

    def test_create_with_admin_email_invites(self, operator_client):
        r = operator_client.post(
            LIST_URL,
            {"name": "Invited SA", "admin_email": "boss@invited.example"},
            format="json",
        )
        assert r.status_code == 201
        assert r.json()["admin_invited"] is True
        org = Org.objects.get(name="Invited SA")
        prof = Profile.objects.get(org=org, user__email="boss@invited.example")
        assert prof.role == "ADMIN"
        assert MagicLinkToken.objects.filter(
            email="boss@invited.example", is_used=False
        ).exists()

    def test_patch_updates_editable_fields(self, operator_client, org_a):
        r = operator_client.patch(
            f"{LIST_URL}{org_a.id}/",
            {"name": "Renamed", "default_country": "CL"},
            format="json",
        )
        assert r.status_code == 200
        org_a.refresh_from_db()
        assert org_a.name == "Renamed"
        assert org_a.default_country == "CL"

    def test_patch_cannot_change_status(self, operator_client, org_a):
        operator_client.patch(
            f"{LIST_URL}{org_a.id}/", {"status": "SUSPENDED"}, format="json"
        )
        org_a.refresh_from_db()
        assert org_a.status == "ACTIVE"


@pytest.mark.django_db
class TestOperatorOrgLifecycle:
    def _url(self, org, action):
        return f"{LIST_URL}{org.id}/{action}/"

    def test_suspend(self, operator_client, org_a):
        r = operator_client.post(
            self._url(org_a, "suspend"), {"reason": "non-payment"}, format="json"
        )
        assert r.status_code == 200
        org_a.refresh_from_db()
        assert org_a.status == "SUSPENDED"
        assert org_a.status_reason == "non-payment"
        assert org_a.is_active is False

    def test_delete_is_soft(self, operator_client, org_a):
        r = operator_client.post(self._url(org_a, "delete"), {}, format="json")
        assert r.status_code == 200
        org_a.refresh_from_db()
        assert org_a.status == "DELETED"
        assert org_a.deleted_at is not None
        assert Org.objects.filter(id=org_a.id).exists()  # row retained

    def test_reactivate_clears_reason(self, operator_client, org_a):
        org_a.status = "SUSPENDED"
        org_a.status_reason = "x"
        org_a.save()
        operator_client.post(self._url(org_a, "reactivate"), {}, format="json")
        org_a.refresh_from_db()
        assert org_a.status == "ACTIVE"
        assert org_a.status_reason == ""

    def test_restore_clears_deleted_at(self, operator_client, org_a):
        org_a.status = "DELETED"
        org_a.save()
        operator_client.post(self._url(org_a, "restore"), {}, format="json")
        org_a.refresh_from_db()
        assert org_a.status == "ACTIVE"
        assert org_a.deleted_at is None


@pytest.mark.django_db
class TestOperatorImpersonation:
    SWITCH = "/api/auth/switch-org/"

    def test_superuser_switches_into_a_non_member_org(self, operator_client, org_a):
        r = operator_client.post(self.SWITCH, {"org_id": str(org_a.id)}, format="json")
        assert r.status_code == 200, r.content
        prof = Profile.objects.get(
            user__email="op@test.com", org=org_a, is_operator_access=True
        )
        assert prof.role == "ADMIN"
        # the returned token actually works for that org
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access_token']}")
        assert c.get("/api/leads/").status_code == 200

    def test_non_superuser_still_403(self, user_client, org_b, org_b_client):
        # user_client (regular_user) is a member of org_a only; not a superuser.
        r = user_client.post(self.SWITCH, {"org_id": str(org_b.id)}, format="json")
        assert r.status_code == 403

    def test_superuser_can_enter_a_suspended_org(self, operator_client, org_a):
        org_a.status = "SUSPENDED"
        org_a.save()
        r = operator_client.post(self.SWITCH, {"org_id": str(org_a.id)}, format="json")
        assert r.status_code == 200
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access_token']}")
        assert c.get("/api/accounts/").status_code == 200  # not 403

    def test_switch_to_missing_org_is_404(self, operator_client):
        r = operator_client.post(
            self.SWITCH,
            {"org_id": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        assert r.status_code == 404

    def test_repeat_switch_reuses_the_profile(self, operator_client, org_a):
        for _ in range(3):
            operator_client.post(self.SWITCH, {"org_id": str(org_a.id)}, format="json")
        assert (
            Profile.objects.filter(
                user__email="op@test.com", org=org_a, is_operator_access=True
            ).count()
            == 1
        )

    def test_operator_profile_hidden_from_member_surfaces(
        self, operator_client, org_b, user_client, user_profile
    ):
        # user_client is a real member of org_b.
        operator_client.post(self.SWITCH, {"org_id": str(org_b.id)}, format="json")
        emails = {
            p["user_details"]["email"]
            for p in user_client.get("/api/users/").json().get("active_users", [])
            if p.get("user_details")
        }
        assert "op@test.com" not in emails
        teams_users = user_client.get("/api/users/get-teams-and-users/").json()
        pemails = {
            p.get("user_details", {}).get("email") for p in teams_users.get("profiles", [])
        }
        assert "op@test.com" not in pemails
