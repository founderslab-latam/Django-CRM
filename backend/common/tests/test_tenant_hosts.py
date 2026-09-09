"""Per-tenant subdomain routing: host -> Org resolution and /api/org/by-host/."""

import pytest

from common.links import frontend_base_url, frontend_url
from common.tenant_hosts import resolve_org_for_host, tenant_label

BASE = "crm.founderslab.cloud"


@pytest.fixture(autouse=True)
def _base_domain(settings):
    settings.TENANT_BASE_DOMAIN = BASE
    settings.FRONTEND_URL = "https://crm.founderslab.cloud"


class TestTenantLabel:
    @pytest.mark.parametrize(
        "host,expected",
        [
            (f"acme.{BASE}", "acme"),
            (f"acme.{BASE}:443", "acme"),
            (f"ACME.{BASE}", "acme"),
            (f"a1b2c3d4e5f6.{BASE}", "a1b2c3d4e5f6"),  # a routing_key
            (BASE, None),  # bare base domain
            (f"api-{BASE}", None),  # the API host is not a sub-label
            (f"deep.sub.{BASE}", None),  # only one level
            ("acme.example.com", None),  # different domain
            ("", None),
            (f"-bad.{BASE}", None),  # not a valid DNS label
        ],
    )
    def test_label(self, host, expected):
        assert tenant_label(host) == expected

    def test_no_base_domain_configured(self, settings):
        settings.TENANT_BASE_DOMAIN = ""
        assert tenant_label(f"acme.{BASE}") is None


@pytest.mark.django_db
class TestResolveOrgForHost:
    def test_matches_subdomain(self, org_a):
        org_a.subdomain = "acme"
        org_a.save()
        assert resolve_org_for_host(f"acme.{BASE}") == org_a
        assert resolve_org_for_host(f"ACME.{BASE}:443") == org_a

    def test_matches_routing_key(self, org_a):
        assert resolve_org_for_host(f"{org_a.routing_key}.{BASE}") == org_a

    def test_unknown_label_is_none(self, org_a):
        assert resolve_org_for_host(f"nope.{BASE}") is None

    def test_bare_base_is_none(self, org_a):
        org_a.subdomain = "acme"
        org_a.save()
        assert resolve_org_for_host(BASE) is None

    def test_suspended_org_does_not_route(self, org_a):
        org_a.subdomain = "acme"
        org_a.status = "SUSPENDED"
        org_a.save()
        assert resolve_org_for_host(f"acme.{BASE}") is None
        # ...and neither does its stable routing_key.
        assert resolve_org_for_host(f"{org_a.routing_key}.{BASE}") is None


@pytest.mark.django_db
class TestOrgByHostEndpoint:
    url = "/api/org/by-host/"

    def test_anonymous_can_resolve_a_tenant_host(self, unauthenticated_client, org_a):
        org_a.subdomain = "acme"
        org_a.brand_color = "#123abc"
        org_a.save()
        resp = unauthenticated_client.get(self.url, {"host": f"acme.{BASE}"})
        assert resp.status_code == 200
        assert resp.data["org"]["id"] == str(org_a.id)
        assert resp.data["org"]["subdomain"] == "acme"
        assert resp.data["org"]["brand_color"] == "#123abc"

    def test_unknown_host_404(self, unauthenticated_client, org_a):
        resp = unauthenticated_client.get(self.url, {"host": f"ghost.{BASE}"})
        assert resp.status_code == 404

    def test_bare_domain_404(self, unauthenticated_client, org_a):
        resp = unauthenticated_client.get(self.url, {"host": BASE})
        assert resp.status_code == 404


class TestFrontendUrlIsTenantAware:
    class _Org:
        def __init__(self, subdomain=""):
            self.subdomain = subdomain

    def test_no_org_uses_global_frontend_url(self):
        assert frontend_base_url() == f"https://{BASE}"
        assert frontend_url("/leads/1") == f"https://{BASE}/leads/1"

    def test_org_without_subdomain_uses_global(self):
        assert frontend_url("/leads/1", org=self._Org("")) == f"https://{BASE}/leads/1"

    def test_org_with_subdomain_gets_its_own_host(self):
        assert (
            frontend_url("/portal/invoice/tok", org=self._Org("acme"))
            == f"https://acme.{BASE}/portal/invoice/tok"
        )

    def test_no_base_domain_configured_falls_back(self, settings):
        settings.TENANT_BASE_DOMAIN = ""
        assert (
            frontend_url("/leads/1", org=self._Org("acme")) == f"https://{BASE}/leads/1"
        )
