import { error } from '@sveltejs/kit';

/**
 * The operator console. Gated on the platform superuser flag from the JWT
 * (hooks.server.js -> locals.is_superuser). A 404, not a 403, so the route's
 * existence is not advertised to non-superusers. The Django /api/operator/
 * endpoints enforce the same check server-side regardless.
 *
 * @type {import('./$types').LayoutServerLoad}
 */
export function load({ locals }) {
  if (!(/** @type {any} */ (locals).is_superuser)) {
    throw error(404, 'Not found');
  }
  return {};
}
