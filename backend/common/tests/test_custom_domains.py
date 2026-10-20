"""Customer-owned domains (`crm.cliente.cl` CNAMEd to the tenant's routing_key
host): validation, the DNS check, routing, Traefik routes, links, CORS, the
operator API and where sign-in links point.

DNS is never really queried: `socket.getaddrinfo` is replaced by a table.
"""

import socket
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.test import APIClient

from common.cors import allow_custom_domain_origin
from common.custom_domains import (
    check_custom_domain,
    validate_custom_domain,
    verified_org_for_domain,
)
from common.links import frontend_base_url
from common.models import Org, Profile, User
from common.serializer import OrgAwareRefreshToken
from common.tasks import _sign_in_org, send_magic_link_email
from common.tenant_hosts import resolve_org_for_host
from common.tenant_routes import render_tenant_routes

BASE = "crm.founderslab.cloud"
PLATFORM_IP = "203.0.113.10"


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.TENANT_BASE_DOMAIN = BASE
    settings.FRONTEND_URL = "https://crm.founderslab.cloud"
    settings.ALLOWED_HOSTS = [
        "testserver",
        "api-crm.founderslab.cloud",
        ".crm.founderslab.cloud",
    ]


def fake_dns(table):
    def resolve(host, *_args, **_kwargs):
        if host not in table:
            raise socket.gaierror("Name or service not known")
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in table[host]
        ]

    return resolve


@pytest.fixture
def org(db):
    return Org.objects.create(name="Cliente", subdomain="cliente")


@pytest.fixture
def verified(org):
    org.custom_domain = "crm.cliente.cl"
    org.custom_domain_verified_at = timezone.now()
    org.save()
    return org


@pytest.fixture
def operator_client(db):
    user = User.objects.create_user(email="op@test.com", password="x")
    user.is_superuser = True
    user.save(update_fields=["is_superuser"])
    client = APIClient()
    token = OrgAwareRefreshToken.for_user_and_org(user, None)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


class TestValidation:
    @pytest.mark.parametrize("value", ["crm.cliente.cl", "app.empresa.com", ""])
    def test_accepts(self, value):
        validate_custom_domain(value)

    @pytest.mark.parametrize(
        "value",
        [
            "localhost",  # one label
            "crm..cliente.cl",
            "-crm.cliente.cl",
            "crm.cliente.123",
            "https://crm.cliente.cl",
            "acme.crm.founderslab.cloud",  # a platform subdomain
            "crm.founderslab.cloud",  # the platform itself
            "api-crm.founderslab.cloud",  # the API host
        ],
    )
    def test_refuses(self, value):
        with pytest.raises(ValidationError):
            validate_custom_domain(value)


@pytest.mark.django_db
class TestDnsCheck:
    def test_passes_when_it_resolves_to_the_platform(self, org):
        org.custom_domain = "crm.cliente.cl"
        dns = {
            f"{org.routing_key}.{BASE}": [PLATFORM_IP],
            "crm.cliente.cl": [PLATFORM_IP],
        }
        with patch("socket.getaddrinfo", fake_dns(dns)):
            ok, detail = check_custom_domain(org)
        assert ok, detail

    def test_fails_when_it_points_elsewhere(self, org):
        org.custom_domain = "crm.cliente.cl"
        dns = {
            f"{org.routing_key}.{BASE}": [PLATFORM_IP],
            "crm.cliente.cl": ["198.51.100.7"],
        }
        with patch("socket.getaddrinfo", fake_dns(dns)):
            ok, detail = check_custom_domain(org)
        assert not ok
        assert f"CNAME to {org.routing_key}.{BASE}" in detail

    def test_fails_clearly_when_not_created_yet(self, org):
        org.custom_domain = "crm.cliente.cl"
        dns = {f"{org.routing_key}.{BASE}": [PLATFORM_IP]}
        with patch("socket.getaddrinfo", fake_dns(dns)):
            ok, detail = check_custom_domain(org)
        assert not ok
        assert "does not resolve yet" in detail

    def test_blames_the_platform_when_its_wildcard_is_missing(self, org):
        org.custom_domain = "crm.cliente.cl"
        with patch("socket.getaddrinfo", fake_dns({"crm.cliente.cl": [PLATFORM_IP]})):
            ok, detail = check_custom_domain(org)
        assert not ok
        assert "wildcard" in detail


@pytest.mark.django_db
class TestRouting:
    def test_verified_domain_resolves_case_and_port_insensitively(self, verified):
        assert resolve_org_for_host("CRM.Cliente.cl:443") == verified

    def test_unverified_domain_does_not_resolve(self, org):
        org.custom_domain = "crm.cliente.cl"
        org.save()
        assert resolve_org_for_host("crm.cliente.cl") is None

    def test_suspended_org_stops_resolving(self, verified):
        verified.status = "SUSPENDED"
        verified.save()
        assert verified_org_for_domain("crm.cliente.cl") is None

    def test_subdomains_still_resolve(self, verified):
        assert resolve_org_for_host(f"cliente.{BASE}") == verified

    def test_traefik_gets_a_router_only_once_verified(self, org):
        org.custom_domain = "crm.cliente.cl"
        org.save()
        assert "crm.cliente.cl" not in render_tenant_routes()
        org.custom_domain_verified_at = timezone.now()
        org.save()
        assert 'rule: "Host(`crm.cliente.cl`)"' in render_tenant_routes()

    def test_links_prefer_the_verified_domain(self, org):
        org.custom_domain = "crm.cliente.cl"
        assert frontend_base_url(org) == f"https://cliente.{BASE}"
        org.custom_domain_verified_at = timezone.now()
        assert frontend_base_url(org) == "https://crm.cliente.cl"


@pytest.mark.django_db
class TestCors:
    def _request(self, origin):
        return RequestFactory().get("/api/leads/", HTTP_ORIGIN=origin)

    def test_allows_the_verified_domain_over_https(self, verified):
        assert allow_custom_domain_origin(None, self._request("https://crm.cliente.cl"))

    @pytest.mark.parametrize(
        "origin",
        [
            "http://crm.cliente.cl",
            "https://crm.cliente.cl:8443",
            "https://evil.example",
            "",
        ],
    )
    def test_refuses_anything_else(self, verified, origin):
        assert not allow_custom_domain_origin(None, self._request(origin))

    def test_refuses_an_unverified_domain(self, org):
        org.custom_domain = "crm.cliente.cl"
        org.save()
        assert not allow_custom_domain_origin(
            None, self._request("https://crm.cliente.cl")
        )


@pytest.mark.django_db
class TestOperatorApi:
    def _url(self, org, suffix=""):
        return f"/api/operator/orgs/{org.id}/{suffix}"

    def test_sets_a_domain_normalized(self, operator_client, org):
        r = operator_client.patch(
            self._url(org), {"custom_domain": "CRM.Cliente.cl."}, format="json"
        )
        assert r.status_code == 200, r.json()
        assert r.json()["organization"]["custom_domain"] == "crm.cliente.cl"
        assert r.json()["organization"]["custom_domain_verified_at"] is None

    def test_refuses_a_platform_address(self, operator_client, org):
        r = operator_client.patch(
            self._url(org), {"custom_domain": f"x.{BASE}"}, format="json"
        )
        assert r.status_code == 400

    def test_refuses_a_domain_another_org_has(self, operator_client, verified):
        other = Org.objects.create(name="Otro")
        r = operator_client.patch(
            self._url(other), {"custom_domain": "crm.cliente.cl"}, format="json"
        )
        assert r.status_code == 400

    def test_changing_the_domain_drops_its_verification(
        self, operator_client, verified
    ):
        r = operator_client.patch(
            self._url(verified), {"custom_domain": "app.cliente.cl"}, format="json"
        )
        assert r.status_code == 200
        verified.refresh_from_db()
        assert verified.custom_domain_verified_at is None

    def test_verify_marks_it_verified_when_dns_is_right(self, operator_client, org):
        org.custom_domain = "crm.cliente.cl"
        org.save()
        dns = {
            f"{org.routing_key}.{BASE}": [PLATFORM_IP],
            "crm.cliente.cl": [PLATFORM_IP],
        }
        with patch("socket.getaddrinfo", fake_dns(dns)):
            r = operator_client.post(self._url(org, "verify-domain/"))
        assert r.status_code == 200
        assert r.json()["verified"] is True
        org.refresh_from_db()
        assert org.custom_domain_verified_at is not None

    def test_a_failed_recheck_keeps_a_working_domain_routed(
        self, operator_client, verified
    ):
        with patch("socket.getaddrinfo", fake_dns({})):
            r = operator_client.post(self._url(verified, "verify-domain/"))
        assert r.json()["verified"] is False
        verified.refresh_from_db()
        assert verified.custom_domain_verified_at is not None

    def test_members_cannot_use_it(self, admin_client, verified):
        r = admin_client.post(self._url(verified, "verify-domain/"))
        assert r.status_code == 403


@pytest.mark.django_db
class TestSignInLinks:
    def _member(self, email, *orgs):
        user = User.objects.create_user(email=email, password="x")
        for o in orgs:
            Profile.objects.create(user=user, org=o, role="USER", is_active=True)
        return user

    def test_single_org_member_signs_in_on_the_tenants_address(self, verified):
        user = self._member("ana@cliente.cl", verified)
        assert _sign_in_org(user, verified.id) == verified

    def test_member_of_several_orgs_signs_in_on_the_main_app(self, verified):
        other = Org.objects.create(name="Otro")
        user = self._member("ana@cliente.cl", verified, other)
        assert _sign_in_org(user, verified.id) is None

    def test_superuser_always_signs_in_on_the_main_app(self, verified):
        user = self._member("op@founderslab.cl", verified)
        user.is_superuser = True
        user.save()
        assert _sign_in_org(user, verified.id) is None

    def test_someone_from_another_org_gets_the_main_app(self, verified):
        other = Org.objects.create(name="Otro")
        user = self._member("ana@otro.cl", other)
        assert _sign_in_org(user, verified.id) is None

    def test_the_email_link_points_at_the_customer_domain(self, verified, mailoutbox):
        from common.models import MagicLinkToken

        self._member("ana@cliente.cl", verified)
        token = MagicLinkToken.objects.create(
            email="ana@cliente.cl",
            token="t" * 64,
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        send_magic_link_email(str(token.id), host_org_id=str(verified.id))
        assert f"https://crm.cliente.cl/login/verify?token={'t' * 64}" in (
            mailoutbox[0].body
        )

    def test_the_request_resolves_the_host_it_came_from(
        self, verified, unauthenticated_client
    ):
        with patch("common.tasks.send_magic_link_email") as task:
            unauthenticated_client.post(
                "/api/auth/magic-link/request/",
                {"email": "ana@cliente.cl", "host": "crm.cliente.cl"},
                format="json",
            )
        assert task.delay.call_args.kwargs["host_org_id"] == str(verified.id)

    def test_an_unknown_host_is_ignored_not_trusted(self, unauthenticated_client, db):
        with patch("common.tasks.send_magic_link_email") as task:
            unauthenticated_client.post(
                "/api/auth/magic-link/request/",
                {"email": "ana@cliente.cl", "host": "evil.example"},
                format="json",
            )
        assert task.delay.call_args.kwargs["host_org_id"] is None
