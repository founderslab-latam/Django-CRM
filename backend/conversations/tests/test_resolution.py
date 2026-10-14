import pytest

from common.testing import rls_org
from contacts.models import Contact
from conversations.resolution import resolve_prospect
from leads.models import Lead


@pytest.mark.django_db
class TestResolveProspect:
    def test_matches_an_existing_contact_by_email(self, org_a):
        existing = Contact.objects.create(
            org=org_a, first_name="Jamie", last_name="Doe", email="jamie@example.com"
        )
        result = resolve_prospect(org_a, email="jamie@example.com", channel="live_chat")
        assert result.contact == existing
        assert result.lead is None
        assert result.created is False

    def test_matches_an_existing_contact_by_phone(self, org_a):
        existing = Contact.objects.create(
            org=org_a, first_name="Robin", last_name="Lee", phone="+56912345678"
        )
        result = resolve_prospect(org_a, phone="+56912345678", channel="whatsapp")
        assert result.contact == existing
        assert result.created is False

    def test_matches_an_existing_unconverted_lead_instead_of_duplicating(self, org_a):
        existing_lead = Lead.objects.create(
            org=org_a,
            title="Inbound inquiry",
            email="prospect@example.com",
            status="assigned",
        )
        result = resolve_prospect(
            org_a, email="prospect@example.com", channel="live_chat"
        )
        assert result.contact is None
        assert result.lead == existing_lead
        assert result.created is False
        assert Lead.objects.filter(org=org_a).count() == 1

    def test_creates_both_when_nobody_matches(self, org_a):
        result = resolve_prospect(
            org_a, email="new@example.com", name="Taylor Swift", channel="whatsapp"
        )
        assert result.created is True
        assert result.contact is not None
        assert result.lead is not None
        assert result.contact.first_name == "Taylor"
        assert result.contact.last_name == "Swift"
        assert result.contact.email == "new@example.com"
        assert result.lead.source == "whatsapp"
        assert result.lead.status == "assigned"
        assert list(result.lead.assigned_to.all()) == []  # unassigned
        assert result.contact in result.lead.contacts.all()

    def test_anonymous_sender_with_no_identity_resolves_to_nothing(self, org_a):
        result = resolve_prospect(org_a, channel="live_chat")
        assert result.contact is None
        assert result.lead is None
        assert result.created is False
        assert Contact.objects.filter(org=org_a).count() == 0
        assert Lead.objects.filter(org=org_a).count() == 0

    def test_no_name_falls_back_to_unknown(self, org_a):
        result = resolve_prospect(org_a, phone="+56900000000", channel="whatsapp")
        assert result.contact.first_name == "Unknown"
        assert result.contact.last_name == ""

    def test_does_not_leak_across_orgs(self, org_a, org_b):
        with rls_org(org_b):
            Contact.objects.create(
                org=org_b,
                first_name="Other",
                last_name="Org",
                email="shared@example.com",
            )
        result = resolve_prospect(
            org_a, email="shared@example.com", channel="live_chat"
        )
        assert result.created is True
        assert result.contact.org_id == org_a.id
