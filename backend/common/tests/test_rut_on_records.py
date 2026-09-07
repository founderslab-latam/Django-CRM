"""
The Chilean RUT is validated on an ACCOUNT's tax id (and the org's, elsewhere)
when country is CL -- an account is the party on an invoice. Lead and Contact
carry a `tax_id` column too, but it is a free-form optional note there, not
RUT-validated.

Run with: pytest common/tests/test_rut_on_records.py -v
"""

import pytest

from accounts.models import Account
from contacts.models import Contact
from leads.models import Lead

VALID_RUT_BARE = "123456785"
VALID_RUT_CANONICAL = "12.345.678-5"
BAD_RUT = "12.345.678-9"


@pytest.mark.django_db
class TestLeadTaxId:
    """Lead.tax_id is free text -- never RUT-validated, never canonicalised."""

    URL = "/api/leads/"

    def _payload(self, **extra):
        return {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.rut@example.com",
            **extra,
        }

    def test_cl_lead_accepts_any_tax_id_verbatim(self, admin_client, org_a):
        response = admin_client.post(
            self.URL, self._payload(country="CL", tax_id=BAD_RUT)
        )
        assert response.status_code == 200
        assert Lead.objects.get(email="jane.rut@example.com").tax_id == BAD_RUT

    def test_editing_a_cl_lead_is_not_blocked_by_its_tax_id(
        self, admin_client, admin_user, org_a
    ):
        lead = Lead.objects.create(
            first_name="Al",
            last_name="Pha",
            email="al.rut@example.com",
            country="CL",
            tax_id=BAD_RUT,
            created_by=admin_user,
            org=org_a,
        )
        response = admin_client.patch(
            f"{self.URL}{lead.id}/", {"first_name": "Alan"}, format="json"
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestContactTaxId:
    """Contact.tax_id is free text -- never RUT-validated, never canonicalised."""

    URL = "/api/contacts/"

    def _payload(self, **extra):
        return {
            "first_name": "Charlie",
            "last_name": "Brown",
            "email": "charlie.rut@example.com",
            **extra,
        }

    def test_cl_contact_accepts_any_tax_id_verbatim(self, admin_client, org_a):
        response = admin_client.post(
            self.URL, self._payload(country="CL", tax_id=BAD_RUT), format="json"
        )
        assert response.status_code == 200
        assert Contact.objects.get(email="charlie.rut@example.com").tax_id == BAD_RUT

    def test_editing_a_cl_contact_is_not_blocked_by_its_tax_id(
        self, admin_client, admin_user, org_a
    ):
        contact = Contact.objects.create(
            first_name="Di",
            last_name="Ez",
            email="di.rut@example.com",
            country="CL",
            tax_id=BAD_RUT,
            created_by=admin_user,
            org=org_a,
        )
        response = admin_client.patch(
            f"{self.URL}{contact.id}/", {"first_name": "Diego"}, format="json"
        )
        assert response.status_code == 200


@pytest.mark.django_db
class TestAccountTaxId:
    URL = "/api/accounts/"

    def test_cl_account_rejects_invalid_rut(self, admin_client, org_a):
        response = admin_client.post(
            self.URL, {"name": "Bad RUT SA", "country": "CL", "tax_id": BAD_RUT}
        )
        assert response.status_code == 400
        assert not Account.objects.filter(name="Bad RUT SA").exists()

    def test_cl_account_stores_rut_canonically(self, admin_client, org_a):
        response = admin_client.post(
            self.URL,
            {"name": "Good RUT SA", "country": "CL", "tax_id": VALID_RUT_BARE},
        )
        assert response.status_code == 200
        assert Account.objects.get(name="Good RUT SA").tax_id == VALID_RUT_CANONICAL

    def test_non_cl_account_keeps_free_form_tax_id(self, admin_client, org_a):
        response = admin_client.post(
            self.URL,
            {"name": "US Corp", "country": "US", "tax_id": "not-a-rut"},
        )
        assert response.status_code == 200
        assert Account.objects.get(name="US Corp").tax_id == "not-a-rut"
