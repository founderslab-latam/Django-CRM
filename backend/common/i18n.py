"""Language resolution shared by the request path and the Celery/email path.

The UI already localises itself: the web and mobile clients send the user's
chosen locale as ``Accept-Language`` and ``django.middleware.locale.
LocaleMiddleware`` activates it. What this module adds is a single, stored
answer to "which language is this person / this org", so that:

* a Celery worker rendering an email -- which has no request and no middleware
  -- can still send it in the recipient's language, and
* a brand-new user, or a request with no explicit locale, inherits the org's
  language before falling back to English.

Resolution order (first hit wins):

    user's stored ``language``  ->  org's stored ``language``  ->
    the request's ``Accept-Language``  ->  ``"en"``

``User.language`` / ``Org.language`` are blank by default; a blank value is
"no preference" and is skipped, not treated as a choice.
"""

from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "es")
DEFAULT_LANGUAGE = "en"

# Offered in the UI (Profile + Org settings) and stored on the models.
LANGUAGE_CHOICES = (
    ("en", "English"),
    ("es", "Español"),
)


def normalize_language(value):
    """Map anything language-shaped onto a supported code, or ``None``.

    Accepts ``"es"``, ``"es-CL"``, ``"ES_cl"``, ``" es "`` -> ``"es"``.
    Returns ``None`` for blank, unknown, or unsupported values so callers can
    treat "no usable preference" uniformly.
    """
    if not value:
        return None
    base = str(value).strip().lower().replace("_", "-").split("-", 1)[0]
    return base if base in SUPPORTED_LANGUAGES else None


def parse_accept_language(header):
    """Language tags from an ``Accept-Language`` header, best first.

    A tiny, dependency-free q-value sort. ``"es-CL,es;q=0.9,en;q=0.8"`` ->
    ``["es-CL", "es", "en"]``. Malformed weights are treated as 1.0 rather
    than dropped.
    """
    if not header:
        return []
    weighted = []
    for index, chunk in enumerate(str(header).split(",")):
        chunk = chunk.strip()
        if not chunk:
            continue
        tag, _, params = chunk.partition(";")
        tag = tag.strip()
        if not tag or tag == "*":
            continue
        weight = 1.0
        if params:
            _, _, q = params.partition("q=")
            try:
                weight = float(q)
            except ValueError:
                weight = 1.0
        # index keeps the sort stable for equal weights (header order wins).
        weighted.append((-weight, index, tag))
    weighted.sort()
    return [tag for _, _, tag in weighted]


def resolve_language(*, user=None, org=None, accept_language=None):
    """The language to use, following the order documented at module level.

    Every argument is optional; pass whatever the call site has. ``user`` and
    ``org`` are duck-typed on a ``.language`` attribute, so an unsaved instance
    or a lightweight stand-in works.
    """
    for source in (user, org):
        if source is not None:
            picked = normalize_language(getattr(source, "language", ""))
            if picked:
                return picked
    for tag in parse_accept_language(accept_language):
        picked = normalize_language(tag)
        if picked:
            return picked
    return DEFAULT_LANGUAGE
