/**
 * i18n bootstrap (svelte-i18n) for the i18n pilot.
 *
 * See ~/harness-engineering/bottle-crm-i18n/PLAN.md for the full scope. This
 * module only wires the mechanism: locale registration, fallback, and a
 * single `setupI18n()` entry point used from both `hooks.server.js` (per
 * request, before anything renders) and the root `+layout.svelte` (to keep
 * the client store in sync with what SSR already resolved). It does not
 * contain any translated content.
 *
 * ── Key naming convention (fixed here, every screen after this pilot
 *    inherits it verbatim) ──────────────────────────────────────────────
 *
 *   <namespace>.<screen>.<element>
 *
 * - `namespace` groups by concern: `common` (cross-screen chrome: sidebar,
 *   topbar, buttons shared everywhere), `auth`, `dashboard`, and one per
 *   business module as the pilot expands (`accounts`, `contacts`, ...).
 * - `screen` is the component or route the string lives in (`login`,
 *   `sidebar`, `welcome`, ...).
 * - `element` is the specific piece of copy (`heading`, `submit_button`,
 *   `greeting`, ...). It may itself contain dots to group repeated elements
 *   (e.g. `common.sidebar.nav.leads`, `common.sidebar.nav.accounts`) - the
 *   convention is a minimum of three segments, not exactly three.
 *
 * Examples: `auth.login.heading`, `common.sidebar.nav.leads`,
 * `dashboard.welcome.greeting`.
 *
 * Interpolate with svelte-i18n's own syntax, not string concatenation:
 * `$_('dashboard.welcome.greeting', { values: { name } })`.
 *
 * Catalogs live in `src/lib/i18n/messages/<locale>.json` (there was no
 * existing `messages/`/`static/` i18n convention in this app - see PLAN.md's
 * "Hallazgos de partida"). PLAN.md's own suggestion was a top-level
 * `frontend/messages/`; that path 404s under the SvelteKit/Vite dev server
 * ("outside of Vite serving allow list" - Vite's dev middleware only serves
 * files reachable from `src/`), which turns every SSR page into a 500. Kept
 * inside `src/` instead, right next to the code that reads it. Do not add a
 * second catalog location.
 */
import { init, register, locale, waitLocale, isLoading, _ } from 'svelte-i18n';

/** Locales this pilot supports. Keep in sync with `frontend/messages/*.json`. */
export const SUPPORTED_LOCALES = ['en', 'es'];

/** Used when no cookie is set, or the cookie holds something we don't recognize. */
export const DEFAULT_LOCALE = 'en';

/** The single cookie this pilot reads/writes. No URL prefix (per PLAN.md). */
export const LOCALE_COOKIE_NAME = 'locale';

register('en', () => import('./messages/en.json'));
register('es', () => import('./messages/es.json'));

let initialized = false;

/**
 * `value` if it's one of `SUPPORTED_LOCALES`, `DEFAULT_LOCALE` otherwise
 * (covers an absent cookie, a stale value from a locale we drop, or a
 * tampered one).
 *
 * @param {string | null | undefined} value
 * @returns {string}
 */
export function resolveLocale(value) {
  return value && SUPPORTED_LOCALES.includes(value) ? value : DEFAULT_LOCALE;
}

/**
 * Register the catalogs (once per module instance) and point the `locale`
 * store at `requestedLocale`, waiting for that catalog to be loaded.
 *
 * Called from `hooks.server.js` on every request, before `resolve(event)`,
 * so the SSR HTML is rendered in the right language from the very first
 * response - no flash from one locale to another. Called again from the
 * root `+layout.svelte` on the client so hydration's store matches what SSR
 * already used.
 *
 * NOTE (SSR caveat, not a bug to silently fix here): svelte-i18n's `locale`
 * store is module-level, shared by every request the Node server handles.
 * Setting it per-request is the standard svelte-i18n/SvelteKit recipe for a
 * cookie-driven, no-URL-prefix locale, but it is not request-isolated -
 * two requests for different locales interleaving mid-await on the same
 * server process could in principle race. Out of scope to fix for this
 * pilot (single dev instance); flagged for whoever takes this past a
 * single-process deployment.
 *
 * @param {string} [requestedLocale]
 * @returns {Promise<void>}
 */
export function setupI18n(requestedLocale = DEFAULT_LOCALE) {
  const resolved = resolveLocale(requestedLocale);

  if (!initialized) {
    init({
      fallbackLocale: DEFAULT_LOCALE,
      initialLocale: resolved
    });
    initialized = true;
  } else {
    locale.set(resolved);
  }

  return waitLocale();
}

export { locale, waitLocale, isLoading, _ };
