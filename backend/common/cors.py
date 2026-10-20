"""CORS for customer-owned domains.

The tenant subdomains are admitted by a fixed regex in settings
(`CORS_ALLOWED_ORIGIN_REGEXES`); customer domains live in the database, so they
are admitted here, per request, through django-cors-headers'
`check_request_enabled` signal -- the same mechanism `webforms.cors` uses.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)


def allow_custom_domain_origin(sender, request, **kwargs):
    """True when the request's Origin is ``https://`` + a verified, active
    customer domain."""
    origin = request.META.get("HTTP_ORIGIN", "")
    if not origin:
        return False
    parts = urlsplit(origin)
    if parts.scheme != "https" or not parts.hostname or parts.port:
        return False

    from common.custom_domains import verified_org_for_domain

    try:
        return verified_org_for_domain(parts.hostname) is not None
    except Exception:
        # This decides whether to relax a cross-origin protection, so an error
        # must never read as permission.
        logger.warning("Custom-domain CORS lookup failed for %s", origin, exc_info=True)
        return False
