/**
 * Root layout load, above both the `(app)` and `(no-layout)` route groups.
 *
 * Its only job for the i18n pilot is handing the client the locale
 * `hooks.server.js` already resolved and rendered with, so the client-side
 * svelte-i18n store can be pointed at the same locale on hydration (see
 * `+layout.svelte` and `$lib/i18n`). Nothing else lives here - each group's
 * own layout still owns its own data.
 *
 * @type {import('./$types').LayoutServerLoad}
 */
export function load({ locals }) {
  return { locale: locals.locale };
}
