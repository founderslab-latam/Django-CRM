# Internationalization

BottleCRM ships English and Spanish (`es`). The two runtimes localize
independently but off the same signal: the language the user picked.

- **Frontend** (SvelteKit): a `locale` cookie, read on every render.
- **Backend** (Django): the `Accept-Language` header the frontend sends on every
  API call, activated by `django.middleware.locale.LocaleMiddleware`.

There is no URL prefix (`/es/...`) and nothing about the locale is stored
server-side. A missing catalog or an empty translation falls back to the source
string, so a partially translated language is never broken, only partly English.

## Frontend

### The mechanism

`frontend/src/lib/i18n/index.js` sets up [`svelte-i18n`](https://github.com/kaisermann/svelte-i18n):
it registers the `en` and `es` catalogs, exposes `setupI18n(locale)` (called
from `hooks.server.js` before anything renders, and again from the root
`+layout.svelte` on the client), and re-exports the `locale` store and the `_`
translation function. `hooks.server.js` reads the `locale` cookie, resolves it
against `SUPPORTED_LOCALES`, stashes it on `event.locals.locale`, and fills the
`%lang%` placeholder in `app.html` so `<html lang>` is right from the first byte.

The switcher (`frontend/src/lib/v2/components/LanguageSwitcher.svelte`) writes
the cookie and reloads — it lives on the profile page (`Your profile →
Preferences`) and on the signed-out login screen.

### Catalogs and keys

`frontend/src/lib/i18n/messages/en.json` and `es.json`. Keys are
`namespace.screen.element`, e.g. `accounts.list.title`,
`common.sidebar.nav.leads`, `dashboard.today.goal_progress`. One namespace per
business module plus `common`, `auth`, `dashboard`. `en.json` holds the **exact
current English string** — translating a language must never change what an
English user sees. The two files must stay key-symmetric; `pnpm run check`
resolves every `$_()` call, and a quick script keeps the sets equal:

```python
import json
def paths(d, p=""):
    out = set()
    for k, v in d.items():
        q = f"{p}.{k}" if p else k
        out |= paths(v, q) if isinstance(v, dict) else {q}
    return out
en = paths(json.load(open("frontend/src/lib/i18n/messages/en.json")))
es = paths(json.load(open("frontend/src/lib/i18n/messages/es.json")))
assert en == es, sorted(en ^ es)
```

### Using it

- In a `.svelte` component: `import { _ } from '$lib/i18n/index.js'`, then
  `{$_('accounts.list.title')}`. Interpolate with
  `$_('key', { values: { name } })`. Pluralize with ICU:
  `"{count, plural, one {# thing} other {# things}}"` — and add the plural in
  Spanish even where English did not need one (`"# abierto"` / `"# abiertos"`).
- In a `+page.server.js` `load` or action: `import { get } from 'svelte/store'`
  and `import { _ } from '$lib/i18n/index.js'`, then
  `fail(400, { error: get(_)('accounts.edit.error_fallback') })`. Safe because
  `hooks.server.js` set the store for the request before the action runs.
- **Never** wrap: CSS class names, `data-*`/`aria-*` used as selectors,
  technical identifiers, values that come from an API response body.

### Shared code

Some text is not on any screen — it is in `$lib/v2/`.

- **`filters.js` / `tabs.js`**: a descriptor's `label` may be a plain string
  *or* a `() => string` function. Translated modules use the function form
  (`() => get($i18n)('leads.filters.field_owner')`); `FilterBar.svelte` and
  `SectionTabs.svelte` call it through a `labelText()` helper that accepts
  either. Convert one module's entry at a time; the rest keep working.
- **`enums.js`**: never edited for translation. Its label maps mirror the
  Django models 1:1. Instead, a per-module helper
  (`$lib/leads/status-source-labels.js`, `$lib/cases/labels.js`,
  `$lib/common/enums-labels.js`, …) maps the raw stored value to a catalog key
  (`leads.enums.source.campaign` → "Campaign" / "Campaña"), so the value written
  back to the API is untouched and only the shown label changes.
- **`format.js`**: `shortDate`, `longDate`, `relativeDays`, `relativeTime` and
  `count` read the active locale (via the `locale` store, at call time) and
  format through `Intl`. `money()` is deliberately still `en-US` — switching a
  currency's grouping and symbol placement is its own decision.

### Not translated on purpose

API-supplied data (activity feed labels, author names), `ROLE_LABEL` /
`AGING_LABEL` at their non-filter call sites on the untranslated `/team`-style
surfaces, the `PortalLineItems.svelte` table headers, and `money()` currency
format. These are tracked, not forgotten.

## Backend

### The mechanism

`settings.py` sets `LANGUAGE_CODE`, `LANGUAGES = [("en", …), ("es", …)]`,
`LOCALE_PATHS = [BASE_DIR / "locale"]`, and puts `LocaleMiddleware` right after
`SessionMiddleware`. `LocaleMiddleware` picks the language from
`Accept-Language`; the frontend sends it from the `locale` cookie in
`src/lib/api.js` (browser) and `src/lib/api-helpers.js` (server load functions).

### Marking strings

Model fields already use `gettext_lazy` — 580-odd `_()` calls across
`*/models.py`. For view and serializer messages:

```python
from django.utils.translation import gettext_lazy as _
...
return Response({"error": _("Organization context required")}, status=403)
raise serializers.ValidationError(_("Email already exists"))
```

- Import **unaliased** (`from django.utils.translation import gettext_lazy`) in a
  file that uses `_` as a throwaway (`for k, _ in ...`, `obj, _ = ...`) — the
  local `_` shadows the alias and calling it 500s.
- Replace f-strings with named `%`-formatting so the value stays out of the
  translatable text:
  `_("Cannot delete stage with %(count)s cases") % {"count": n}`.
- Leave alone: `logger.*`, internal exceptions that render as a 500 (a bare
  model-layer `ValidationError` guard, `Http404("...")` — DRF discards its
  message), technical identifiers, `str(exc)`.

### Building the catalogs

```bash
cd backend
python manage.py makemessages -l es --no-location --no-wrap
# edit backend/locale/es/LC_MESSAGES/django.po — fill each new msgstr,
# and on any entry makemessages marked "#, fuzzy" with a borrowed string,
# delete the "#, fuzzy" and "#|" lines and write the correct translation.
python manage.py compilemessages
```

`gettext` (the `msgfmt` CLI) is in the backend Docker image; the container
entrypoint runs `compilemessages` on start. `.po` files are committed; `.mo`
files are gitignored and built.

### Email templates

`backend/*/templates/**/*email*.html`. Each gets `{% load i18n %}` (right after
`{% extends %}` where present). Plain copy → `{% trans "..." %}`; copy with
variables or an `{% if %}` split → `{% blocktrans %}` (per branch — no block
tags inside `blocktrans`; simple variables only, use `{% blocktrans with
name=... %}`). URLs, inline styles and `{{ record.field }}` data stay as-is.

## Adding a language

1. Add it to `LANGUAGES` in `backend/crm/settings.py`.
2. `python manage.py makemessages -l <code>` and translate
   `backend/locale/<code>/LC_MESSAGES/django.po`.
3. Add `<code>` to `SUPPORTED_LOCALES` in `frontend/src/lib/i18n/index.js` and
   create `frontend/src/lib/i18n/messages/<code>.json` with every key `en.json`
   has.
4. Add its label to `common.language_switcher.*` in the catalogs.
