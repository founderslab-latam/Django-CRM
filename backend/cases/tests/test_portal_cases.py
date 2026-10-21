"""What a portal customer may read and write, and everything they may not."""

import pytest
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from cases.models import Case
from common.models import Comment
from common.portal_auth import mint_portal_token
from contacts.models import Contact

LIST_URL = "/api/portal/cases/"


def _client(contact):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {mint_portal_token(contact)}")
    return client


@pytest.fixture
def pat(org_a):
    return Contact.objects.create(
        org=org_a, first_name="Pat", last_name="Smith", email="pat@example.com"
    )


@pytest.fixture
def jo(org_a):
    return Contact.objects.create(
        org=org_a, first_name="Jo", last_name="Blake", email="jo@example.com"
    )


@pytest.fixture
def pats_case(org_a, pat):
    case = Case.objects.create(
        org=org_a, name="Login broken", status="New", priority="High"
    )
    case.contacts.add(pat)
    return case


@pytest.fixture
def jos_case(org_a, jo):
    case = Case.objects.create(
        org=org_a, name="Invoice query", status="New", priority="Low"
    )
    case.contacts.add(jo)
    return case


@pytest.mark.django_db
class TestPortalCaseList:
    def test_lists_my_cases(self, pat, pats_case):
        response = _client(pat).get(LIST_URL)
        assert response.status_code == 200
        assert [c["id"] for c in response.json()["cases"]] == [str(pats_case.id)]

    def test_does_not_list_a_colleagues_case(self, pat, pats_case, jos_case):
        """Same org, different contact. The narrow rule, proven."""
        ids = [c["id"] for c in _client(pat).get(LIST_URL).json()["cases"]]
        assert str(pats_case.id) in ids
        assert str(jos_case.id) not in ids

    def test_does_not_list_another_orgs_case(self, pat, pats_case, org_b):
        other = Case.objects.create(
            org=org_b, name="Not yours", status="New", priority="Low"
        )
        ids = [c["id"] for c in _client(pat).get(LIST_URL).json()["cases"]]
        assert str(other.id) not in ids

    def test_status_filter(self, pat, pats_case, org_a):
        closed = Case.objects.create(
            org=org_a, name="Old thing", status="Closed", priority="Low"
        )
        closed.contacts.add(pat)
        response = _client(pat).get(LIST_URL + "?status=Closed")
        assert [c["id"] for c in response.json()["cases"]] == [str(closed.id)]

    def test_rejects_an_unknown_status(self, pat, pats_case):
        assert _client(pat).get(LIST_URL + "?status=Nonsense").status_code == 400

    def test_soft_deleted_cases_are_hidden(self, pat, pats_case):
        pats_case.is_active = False
        pats_case.save()
        assert _client(pat).get(LIST_URL).json()["cases"] == []

    def test_anonymous_is_refused(self, pats_case):
        assert APIClient().get(LIST_URL).status_code in (401, 403)


@pytest.mark.django_db
class TestPortalCaseDetail:
    def test_reads_my_case(self, pat, pats_case):
        response = _client(pat).get(f"{LIST_URL}{pats_case.id}/")
        assert response.status_code == 200
        assert response.json()["case"]["name"] == "Login broken"

    def test_cannot_read_a_colleagues_case(self, pat, jos_case):
        assert _client(pat).get(f"{LIST_URL}{jos_case.id}/").status_code == 404

    def test_cannot_read_another_orgs_case(self, pat, org_b):
        other = Case.objects.create(
            org=org_b, name="Not yours", status="New", priority="Low"
        )
        assert _client(pat).get(f"{LIST_URL}{other.id}/").status_code == 404

    def test_internal_notes_never_appear(self, pat, pats_case, org_a, admin_profile):
        """The one leak that would matter most, and the reason is_internal exists."""
        ct = ContentType.objects.get_for_model(Case)
        Comment.objects.create(
            org=org_a,
            content_type=ct,
            object_id=pats_case.id,
            comment="Customer is being difficult, deprioritise.",
            commented_by=admin_profile,
            is_internal=True,
        )
        Comment.objects.create(
            org=org_a,
            content_type=ct,
            object_id=pats_case.id,
            comment="We are looking into it.",
            commented_by=admin_profile,
            is_internal=False,
        )
        rendered = str(_client(pat).get(f"{LIST_URL}{pats_case.id}/").json())
        assert "We are looking into it." in rendered
        assert "difficult" not in rendered

    def test_agent_authors_are_not_named(self, pat, pats_case, org_a, admin_profile):
        Comment.objects.create(
            org=org_a,
            content_type=ContentType.objects.get_for_model(Case),
            object_id=pats_case.id,
            comment="On it.",
            commented_by=admin_profile,
            is_internal=False,
        )
        body = _client(pat).get(f"{LIST_URL}{pats_case.id}/").json()
        assert body["comments"][0]["author"] == "Support"
        assert body["comments"][0]["is_mine"] is False
        assert body["comments"][0]["is_support"] is True

    def test_my_own_reply_is_not_marked_as_support(self, pat, pats_case, org_a):
        Comment.objects.create(
            org=org_a,
            content_type=ContentType.objects.get_for_model(Case),
            object_id=pats_case.id,
            comment="Still broken.",
            commented_by_contact=pat,
            is_internal=False,
        )
        body = _client(pat).get(f"{LIST_URL}{pats_case.id}/").json()
        assert body["comments"][0]["is_support"] is False

    def test_detail_carries_reference_and_org_name(self, pat, pats_case, org_a):
        body = _client(pat).get(f"{LIST_URL}{pats_case.id}/").json()
        expected = str(pats_case.id).replace("-", "")[:8].upper()
        assert body["case"]["reference"] == expected
        assert body["case"]["updated_at"]
        assert body["org_name"] == org_a.name
        # Still none of the agent-side fields.
        assert "assigned_to" not in body["case"]
        assert "teams" not in body["case"]

    def test_list_carries_the_reference_too(self, pat, pats_case):
        cases = _client(pat).get(LIST_URL).json()["cases"]
        assert cases[0]["reference"] == str(pats_case.id).replace("-", "")[:8].upper()

    def test_open_case_does_not_promise_a_reopen(self, pat, pats_case):
        body = _client(pat).get(f"{LIST_URL}{pats_case.id}/").json()
        assert body["reopens_on_reply"] is False

    def test_recently_closed_case_reopens_on_reply(self, pat, pats_case):
        from django.utils import timezone

        Case.objects.filter(pk=pats_case.pk).update(
            status="Closed", closed_on=timezone.localdate()
        )
        body = _client(pat).get(f"{LIST_URL}{pats_case.id}/").json()
        assert body["reopens_on_reply"] is True

    def test_case_closed_past_the_window_does_not_reopen(self, pat, pats_case):
        from datetime import timedelta

        from django.utils import timezone

        Case.objects.filter(pk=pats_case.pk).update(
            status="Closed", closed_on=timezone.localdate() - timedelta(days=30)
        )
        body = _client(pat).get(f"{LIST_URL}{pats_case.id}/").json()
        assert body["reopens_on_reply"] is False


@pytest.mark.django_db
class TestPortalWrites:
    def test_files_a_case_attached_to_me(self, pat, org_a):
        response = _client(pat).post(
            LIST_URL, {"name": "Printer on fire", "priority": "High"}, format="json"
        )
        assert response.status_code == 201
        case = Case.objects.get(name="Printer on fire")
        assert case.org == org_a
        assert list(case.contacts.all()) == [pat]
        assert case.status == "New"

    def test_cannot_choose_org_status_or_contacts(self, pat, org_a, org_b, jo):
        """Mass assignment. Every one of these is the server's to decide."""
        response = _client(pat).post(
            LIST_URL,
            {
                "name": "Sneaky",
                "priority": "Low",
                "org": str(org_b.id),
                "status": "Closed",
                "contacts": [str(jo.id)],
            },
            format="json",
        )
        assert response.status_code == 201
        case = Case.objects.get(name="Sneaky")
        assert case.org == org_a
        assert case.status == "New"
        assert list(case.contacts.all()) == [pat]

    def test_rejects_an_empty_name(self, pat):
        response = _client(pat).post(LIST_URL, {"name": "   "}, format="json")
        assert response.status_code == 400

    def test_replies_to_my_case(self, pat, pats_case):
        response = _client(pat).post(
            f"{LIST_URL}{pats_case.id}/comment/",
            {"comment": "Any news?"},
            format="json",
        )
        assert response.status_code == 201
        comment = Comment.objects.get(object_id=pats_case.id)
        assert comment.commented_by_contact == pat
        assert comment.commented_by is None
        assert comment.is_internal is False

    def test_reply_cannot_be_marked_internal(self, pat, pats_case):
        """A customer must not be able to write into the agents' private thread."""
        _client(pat).post(
            f"{LIST_URL}{pats_case.id}/comment/",
            {"comment": "Hidden?", "is_internal": True},
            format="json",
        )
        assert Comment.objects.get(object_id=pats_case.id).is_internal is False

    def test_my_own_reply_comes_back_as_mine(self, pat, pats_case):
        response = _client(pat).post(
            f"{LIST_URL}{pats_case.id}/comment/", {"comment": "Hello"}, format="json"
        )
        assert response.json()["comment"]["is_mine"] is True
        assert response.json()["comment"]["author"] == "Pat Smith"

    def test_cannot_reply_to_a_colleagues_case(self, pat, jos_case):
        response = _client(pat).post(
            f"{LIST_URL}{jos_case.id}/comment/", {"comment": "Nosy"}, format="json"
        )
        assert response.status_code == 404
        assert Comment.objects.count() == 0

    def test_rejects_an_empty_reply(self, pat, pats_case):
        response = _client(pat).post(
            f"{LIST_URL}{pats_case.id}/comment/", {"comment": "  "}, format="json"
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestTheAgentsSideOfTheConversation:
    """The other half of the thread, which the customer's half is useless without.

    A portal reply has no Profile, so the agent-facing serializer used to render
    it with a null author and the phone showed "Unknown". The contact who wrote
    it has to reach the agents' clients too.
    """

    def test_a_portal_reply_names_the_customer_who_wrote_it(
        self, org_a, pat, pats_case
    ):
        from common.serializer import CommentSerializer

        _client(pat).post(
            f"{LIST_URL}{pats_case.id}/comment/",
            {"comment": "Any news?"},
            format="json",
        )
        data = CommentSerializer(Comment.objects.get()).data
        assert data["commented_by"] is None
        assert data["commented_by_contact"]["name"] == "Pat Smith"
        assert data["commented_by_contact"]["email"] == "pat@example.com"

    def test_an_agent_reply_still_has_no_contact_author(self, org_a, admin_profile):
        """The two are mutually exclusive, so neither may shadow the other."""
        from common.serializer import CommentSerializer

        case = Case.objects.create(
            org=org_a, name="Agent side", status="New", priority="Low"
        )
        comment = Comment.objects.create(
            org=org_a,
            content_type=ContentType.objects.get_for_model(Case),
            object_id=case.id,
            comment="Looking into it.",
            commented_by=admin_profile,
        )
        data = CommentSerializer(comment).data
        assert data["commented_by_contact"] is None
        assert data["commented_by"] is not None

    def test_a_contact_author_cannot_be_set_from_a_request_body(
        self, org_a, pat, admin_profile
    ):
        """Read-only, so an agent cannot attribute their own words to a customer."""
        from common.serializer import CommentSerializer

        case = Case.objects.create(
            org=org_a, name="Attribution", status="New", priority="Low"
        )
        comment = Comment.objects.create(
            org=org_a,
            content_type=ContentType.objects.get_for_model(Case),
            object_id=case.id,
            comment="Mine.",
            commented_by=admin_profile,
        )
        serializer = CommentSerializer(
            comment,
            data={"comment": "Theirs.", "commented_by_contact": str(pat.id)},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        comment.refresh_from_db()
        assert comment.commented_by_contact_id is None


@pytest.mark.postgres_only
@pytest.mark.django_db
def test_portal_request_runs_under_a_real_rls_context(pat, pats_case):
    """The portal query runs with a real org context, not an empty one.

    This is the difference between the portal and the older public endpoints,
    which run anonymously with `app.current_org` empty and needed the
    PortalAccessToken workaround in backend/docs/PORTAL_RLS.md. A portal request
    resolves its org in middleware, so RLS applies normally.

    Worth pinning under Postgres specifically: dev often runs as a superuser,
    which bypasses RLS entirely and would make a broken context look fine.
    """
    from django.db import connection

    if connection.vendor != "postgresql":
        pytest.skip("RLS requires PostgreSQL")

    assert _client(pat).get(LIST_URL).status_code == 200
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.current_org', true)")
        assert cursor.fetchone()[0] not in (None, "")
