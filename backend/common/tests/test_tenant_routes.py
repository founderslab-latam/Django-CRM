"""Traefik dynamic-config generation for per-tenant subdomains."""

import pytest

from common.tenant_routes import render_tenant_routes, write_tenant_routes

BASE = "crm.founderslab.cloud"


@pytest.fixture(autouse=True)
def _cfg(settings):
    settings.TENANT_BASE_DOMAIN = BASE
    settings.TENANT_ROUTER_SERVICE = "crm-web@docker"
    settings.TENANT_ROUTER_ENTRYPOINTS = "websecure"
    settings.TENANT_ROUTER_CERTRESOLVER = "mytlschallenge"


@pytest.mark.django_db
class TestRenderTenantRoutes:
    def test_empty_when_no_subdomains(self, org_a):
        # org_a has a routing_key but no subdomain -> still a router for the key.
        out = render_tenant_routes()
        assert f"Host(`{org_a.routing_key}.{BASE}`)" in out
        assert "service: crm-web@docker" in out
        assert "certResolver: mytlschallenge" in out

    def test_subdomain_and_key_both_routed(self, org_a):
        org_a.subdomain = "acme"
        org_a.save()
        out = render_tenant_routes()
        assert f"Host(`acme.{BASE}`)" in out
        assert f"Host(`{org_a.routing_key}.{BASE}`)" in out

    def test_suspended_org_is_dropped(self, org_a):
        org_a.subdomain = "acme"
        org_a.status = "SUSPENDED"
        org_a.save()
        out = render_tenant_routes()
        assert f"acme.{BASE}" not in out
        assert org_a.routing_key not in out

    def test_no_base_domain_is_empty_routers(self, settings, org_a):
        settings.TENANT_BASE_DOMAIN = ""
        out = render_tenant_routes()
        assert "routers:" in out
        assert "Host(" not in out

    def test_valid_yaml_shape(self, org_a):
        org_a.subdomain = "acme"
        org_a.save()
        yaml = pytest.importorskip("yaml")
        parsed = yaml.safe_load(render_tenant_routes())
        routers = parsed["http"]["routers"]
        assert any(r["rule"] == f"Host(`acme.{BASE}`)" for r in routers.values())
        for r in routers.values():
            assert r["service"] == "crm-web@docker"
            assert r["entryPoints"] == ["websecure"]
            assert r["tls"]["certResolver"] == "mytlschallenge"


@pytest.mark.django_db
class TestWriteTenantRoutes:
    def test_noop_without_setting(self, settings, org_a):
        settings.TRAEFIK_DYNAMIC_FILE = ""
        assert write_tenant_routes() is None

    def test_writes_atomically_when_configured(self, settings, tmp_path, org_a):
        org_a.subdomain = "acme"
        org_a.save()
        target = tmp_path / "sub" / "tenant-routes.yml"
        settings.TRAEFIK_DYNAMIC_FILE = str(target)

        written = write_tenant_routes()
        assert written == str(target)
        assert target.exists()
        assert f"Host(`acme.{BASE}`)" in target.read_text()
        # No temp files left behind.
        assert not list((tmp_path / "sub").glob(".tenant-routes-*"))

    def test_org_save_triggers_write(self, settings, tmp_path):
        target = tmp_path / "routes.yml"
        settings.TRAEFIK_DYNAMIC_FILE = str(target)
        from common.models import Org

        Org.objects.create(name="Signal Co", subdomain="signalco")
        assert target.exists()
        assert f"Host(`signalco.{BASE}`)" in target.read_text()
