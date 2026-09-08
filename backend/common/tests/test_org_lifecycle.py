"""
Org lifecycle model layer: status <-> is_active sync, subdomain rules, the
stable routing key.

Run with: pytest common/tests/test_org_lifecycle.py -v
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from common.models import Org, generate_routing_key
from common.validators import validate_org_subdomain


@pytest.mark.django_db
class TestOrgStatusSync:
    def test_new_org_is_active(self):
        org = Org.objects.create(name="Acme")
        assert org.status == "ACTIVE"
        assert org.is_active is True

    def test_suspend_clears_is_active(self):
        org = Org.objects.create(name="Acme")
        org.status = "SUSPENDED"
        org.save()
        org.refresh_from_db()
        assert org.is_active is False

    def test_reactivate_restores_is_active(self):
        org = Org.objects.create(name="Acme", status="SUSPENDED")
        assert org.is_active is False
        org.status = "ACTIVE"
        org.save()
        assert org.is_active is True

    def test_deleted_status_is_inactive(self):
        org = Org.objects.create(name="Acme", status="DELETED")
        assert org.is_active is False


@pytest.mark.django_db
class TestOrgRoutingKey:
    def test_auto_assigned_and_unique(self):
        a = Org.objects.create(name="A")
        b = Org.objects.create(name="B")
        assert a.routing_key and b.routing_key
        assert a.routing_key != b.routing_key

    def test_generate_routing_key_is_a_dns_label(self):
        key = generate_routing_key()
        assert 1 <= len(key) <= 63
        assert key == key.lower()
        assert all(c.isalnum() for c in key)


@pytest.mark.django_db
class TestOrgSubdomain:
    @pytest.mark.parametrize("good", ["acme", "acme-corp", "a1", "x" * 63])
    def test_accepts_valid_labels(self, good):
        validate_org_subdomain(good)  # no raise

    def test_blank_is_allowed(self):
        validate_org_subdomain("")

    @pytest.mark.parametrize(
        "bad", ["-acme", "acme-", "AC ME", "acme_corp", "x" * 64, "acmé"]
    )
    def test_rejects_bad_shape(self, bad):
        with pytest.raises(ValidationError):
            validate_org_subdomain(bad)

    @pytest.mark.parametrize("reserved", ["www", "api", "admin", "operator", "crm"])
    def test_rejects_reserved(self, reserved):
        with pytest.raises(ValidationError):
            validate_org_subdomain(reserved)

    def test_subdomain_unique_case_insensitive(self):
        Org.objects.create(name="A", subdomain="acme")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Org.objects.create(name="B", subdomain="ACME")

    def test_multiple_orgs_may_have_no_subdomain(self):
        Org.objects.create(name="A", subdomain="")
        Org.objects.create(name="B", subdomain="")  # no unique clash on blank
