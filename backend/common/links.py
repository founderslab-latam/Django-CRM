"""Absolute links into the web app, for emails.

Every link that leaves this system in an email points at the SvelteKit frontend,
not at the API: ``/portal/invoice/<token>`` and ``/portal/estimate/<token>`` for
customers, ``/csat/<token>`` for a survey, ``/invoices/<id>`` for a colleague.
None of those paths exist on the Django host.

They were built four different wrong ways, each independently broken:

* ``f"{protocol}://{domain}/portal/invoice/{token}"`` where every caller passed
  ``domain=settings.DOMAIN_NAME``, which already carries a scheme. The emitted
  link was ``http://http://localhost:8000/portal/invoice/…``: two schemes, dead
  on arrival even when ``DOMAIN_NAME`` was set correctly for a real deployment.
* ``DOMAIN_NAME`` names the **backend**. Even with the double scheme removed,
  the link pointed at the API host, where ``/portal/...`` 404s.
* ``send_estimate_to_client`` is dispatched with no ``domain`` at all, so it
  fell back to the ``"localhost"`` default and emitted ``http://localhost/…``.
* ``backend/.env`` sets ``DOMAIN_NAME=""``, so the CSAT builder's
  ``f"{domain}/csat/{token}"`` produced the relative ``"/csat/<token>"``, which
  is not a link at all inside an email body.

``FRONTEND_URL`` already existed and already meant exactly this: it is what the
welcome email and the magic-link sign-in URL are built from. Routing the rest
through it makes one setting answer one question, and gives an operator a single
value to get right.
"""

from django.conf import settings


def frontend_base_url(org=None):
    """The web app base URL, tenant-aware.

    When ``org`` has a ``subdomain`` and ``TENANT_BASE_DOMAIN`` is configured,
    the tenant is served at its own host, so a link into the app should point
    there — ``https://<subdomain>.<base>`` — not at the shared ``FRONTEND_URL``.
    Falls back to ``FRONTEND_URL`` for an org with no subdomain, or none at all
    (welcome mail, the magic-link sign-in URL).
    """
    base_domain = (getattr(settings, "TENANT_BASE_DOMAIN", "") or "").strip().strip(".")
    subdomain = (getattr(org, "subdomain", "") or "").strip().lower()
    if org is not None and subdomain and base_domain:
        return f"https://{subdomain}.{base_domain}"
    return (getattr(settings, "FRONTEND_URL", "") or "").rstrip("/")


def frontend_url(path, org=None):
    """Return an absolute URL to ``path`` on the web app.

    ``path`` is a root-relative path such as ``/portal/invoice/<token>``. The
    leading slash is optional and the base's trailing slash is stripped, so an
    operator who sets ``FRONTEND_URL=https://app.example.com/`` gets the same
    result as one who omits it.

    Pass ``org`` for any link that belongs to a specific tenant (a portal link,
    a "view this record" link to a colleague): the URL is then built on that
    tenant's own subdomain when it has one. See :func:`frontend_base_url`.
    """
    base = frontend_base_url(org).rstrip("/")
    suffix = path if path.startswith("/") else f"/{path}"
    return f"{base}{suffix}"
