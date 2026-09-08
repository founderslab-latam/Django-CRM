"""Per-tenant branding and language for outbound email.

Two things every automatic email should carry and, until now, none did:

* the **sending org's mark** -- its logo, or failing that its name -- instead
  of a hard-coded "BottleCRM" wordmark, so a resold/white-labelled tenant's
  mail looks like theirs; and
* the **recipient's language**, so ``{% trans %}`` in the templates actually
  resolves to Spanish for a Spanish user. A Celery worker has no request and
  no ``LocaleMiddleware``, so the language has to be activated by hand.

Usage in a task::

    from common.email_branding import localized_email, brand_context

    with localized_email(recipient=profile.user, org=invoice.org):
        subject = _("Invoice %(number)s assigned to you") % {"number": n}
        html = render_to_string(tpl, {**ctx, **brand_context(invoice.org)})
        EmailMessage(subject, html, to=[addr]).send()

``localized_email`` activates the language for the whole block (subject
included); ``brand_context`` adds ``email_logo_url`` / ``email_brand_name``
for the root template's ``{% block brandmark %}``.
"""

from __future__ import annotations

from contextlib import contextmanager

from django.conf import settings
from django.utils import translation

from common.i18n import resolve_language


def logo_url_for_email(org):
    """Absolute, credential-free URL of ``org``'s logo, or ``None``.

    An email client fetches images anonymously and cannot follow a relative
    path, so ``org.logo.url`` (``/media/org_logos/x.png`` under the default
    filesystem storage) is unusable as-is. ``settings.PUBLIC_MEDIA_URL`` names
    the public host that serves that subtree; prepend it. A storage backend
    that already returns an absolute URL (e.g. S3) is passed straight through.
    Returns ``None`` when there is no logo or no public host configured -- the
    template then falls back to the name.
    """
    if org is None:
        return None
    logo = getattr(org, "logo", None)
    if not logo:
        return None
    try:
        url = logo.url
    except ValueError:
        return None
    if url.startswith(("http://", "https://", "//")):
        return url
    base = getattr(settings, "PUBLIC_MEDIA_URL", "")
    if not base:
        return None
    return f"{base}{url}"


def brand_context(org):
    """Template vars for ``{% block brandmark %}`` in the root email template.

    ``email_logo_url`` may be ``None``; the template shows the name then, and
    ``email_brand_name`` is ``None`` too for a message with no org (magic-link,
    welcome), which the template renders as the product default.
    """
    return {
        "email_logo_url": logo_url_for_email(org),
        "email_brand_name": getattr(org, "name", None) if org else None,
    }


@contextmanager
def localized_email(*, recipient=None, org=None, accept_language=None):
    """Activate the resolved language for the duration of the block.

    ``recipient`` is the ``User`` the mail is addressed to (its ``language``
    wins); ``org`` supplies the fallback and is also the right sole argument
    for customer-facing mail whose recipient has no account. Yields the
    language code in case the caller wants to log it.
    """
    language = resolve_language(
        user=recipient, org=org, accept_language=accept_language
    )
    with translation.override(language):
        yield language
