"""Customer-owned domains: a tenant served at ``crm.cliente.cl``.

The customer creates ``crm.cliente.cl CNAME <routing_key>.<TENANT_BASE_DOMAIN>``.
A CNAME only changes where the name resolves; the browser still sends
``Host: crm.cliente.cl``. So the domain has to be known here -- for host
routing (`common.tenant_hosts`), the Traefik router + certificate
(`common.tenant_routes`), CORS (`common.cors`) and links (`common.links`).

Nothing is routed until the operator verifies the domain
(`check_custom_domain`): a router for a name that doesn't point at us yet
would only make Traefik fail ACME challenges against Let's Encrypt's rate
limits.
"""

from __future__ import annotations

import re
import socket
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_host(value: str) -> str:
    """Lowercase, no port, no trailing dot."""
    return str(value or "").split(":", 1)[0].strip().lower().rstrip(".")


def _platform_hosts() -> set[str]:
    hosts = {
        normalize_host(urlsplit(getattr(settings, "FRONTEND_URL", "") or "").netloc)
    }
    hosts.update(
        normalize_host(h)
        for h in getattr(settings, "ALLOWED_HOSTS", [])
        if h and not h.startswith(".") and h != "*"
    )
    hosts.discard("")
    return hosts


def validate_custom_domain(value: str) -> None:
    """A full hostname the platform doesn't already own. Blank is allowed."""
    if not value:
        return
    host = normalize_host(value)
    labels = host.split(".")
    if (
        len(host) > 253
        or len(labels) < 2
        or not all(_LABEL_RE.fullmatch(label) for label in labels)
        or labels[-1].isdigit()
    ):
        raise ValidationError(_("Enter a domain name such as crm.example.com."))
    base = normalize_host(getattr(settings, "TENANT_BASE_DOMAIN", "") or "")
    if base and (host == base or host.endswith("." + base)):
        raise ValidationError(
            _("That is a platform address; set the subdomain field instead.")
        )
    if host in _platform_hosts():
        raise ValidationError(_("That address is used by the platform itself."))


def cname_target(org) -> str:
    base = normalize_host(getattr(settings, "TENANT_BASE_DOMAIN", "") or "")
    return f"{org.routing_key}.{base}"


def _addresses(host: str) -> set[str]:
    infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
    return {info[4][0] for info in infos}


def check_custom_domain(org) -> tuple[bool, str]:
    """Whether ``org.custom_domain`` resolves to this platform yet.

    Compares addresses rather than reading the CNAME record itself, so an A
    record pointing at the same IP passes too, and no DNS library is needed.
    Returns ``(ok, message)``; the message is meant for the operator.
    """
    domain = normalize_host(org.custom_domain)
    if not domain:
        return False, "No custom domain is set."
    target = cname_target(org)
    try:
        ours = _addresses(target)
    except OSError:
        return False, (
            f"{target} does not resolve: the wildcard DNS record "
            f"*.{target.split('.', 1)[1]} is missing on the platform side."
        )
    try:
        theirs = _addresses(domain)
    except OSError:
        return False, (
            f"{domain} does not resolve yet. The customer needs a CNAME record "
            f"pointing it to {target}; new records can take a while to propagate."
        )
    if ours & theirs:
        return True, f"{domain} points to this platform."
    return False, (
        f"{domain} resolves to {', '.join(sorted(theirs))}, not to this platform. "
        f"It should be a CNAME to {target}."
    )


def verified_org_for_domain(host: str):
    """The active org whose verified custom domain is ``host``, or None."""
    domain = normalize_host(host)
    if not domain:
        return None
    from common.models import Org

    return (
        Org.objects.filter(
            custom_domain=domain,
            custom_domain_verified_at__isnull=False,
            status="ACTIVE",
        )
        .order_by("id")
        .first()
    )
