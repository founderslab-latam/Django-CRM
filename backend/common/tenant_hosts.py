"""Resolve an incoming HTTP Host to an Org — per-tenant subdomain routing.

Every tenant is reachable at two hosts under ``settings.TENANT_BASE_DOMAIN``:

* ``<org.subdomain>.<base>``   — the branded subdomain the operator assigns.
* ``<org.routing_key>.<base>`` — a stable, unguessable label the customer
  points a CNAME at; it never changes even if the org renames its subdomain.

Both map to the same Org. Anything that is not a single label under the base
domain (the bare ``<base>``, the API host, an unknown label) resolves to
``None`` and the caller falls back to the credential-derived org, exactly as
before this feature existed.

The web app calls :func:`resolve_org_for_host` through ``/api/org/by-host/``;
the shared API host itself is never routed this way — it stays multi-tenant by
token.
"""

from __future__ import annotations

import re

from django.conf import settings

# A DNS label: what a single subdomain level may contain. Matches the shape
# `common.validators.validate_org_subdomain` enforces on `Org.subdomain`, and
# `secrets.token_hex(6)` (the routing_key) is a subset of it.
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def tenant_label(host: str) -> str | None:
    """The single sub-label of ``host`` beneath ``TENANT_BASE_DOMAIN``.

    ``"acme.crm.example.com"`` -> ``"acme"``. Returns ``None`` for the bare
    base domain, a deeper name (``"a.b.crm.example.com"``), a label that is not
    a valid DNS label, or a host outside the base domain. Port and trailing dot
    are ignored; matching is case-insensitive.
    """
    base = (
        (getattr(settings, "TENANT_BASE_DOMAIN", "") or "").strip().lower().strip(".")
    )
    if not base or not host:
        return None
    name = str(host).split(":", 1)[0].strip().lower().strip(".")
    suffix = "." + base
    if not name.endswith(suffix):
        return None
    label = name[: -len(suffix)]
    if not label or "." in label:
        return None
    return label if _LABEL_RE.fullmatch(label) else None


def resolve_org_for_host(host: str):
    """The active Org served at ``host``, or ``None``.

    Matches the sub-label against ``Org.subdomain`` (case-insensitively) and
    then ``Org.routing_key``. Only ``status="ACTIVE"`` orgs resolve — a
    suspended or deleted tenant's subdomain stops routing, which is the point
    of the operator console's state machine.
    """
    label = tenant_label(host)
    if label is None:
        return None

    from django.db.models import Q

    from common.models import Org

    return (
        Org.objects.filter(
            Q(subdomain__iexact=label) | Q(routing_key=label),
            status="ACTIVE",
        )
        .order_by("id")
        .first()
    )
