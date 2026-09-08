import { redirect } from '@sveltejs/kit';

/**
 * Leave an impersonation session. Dropping the `org` cookie is enough: on the
 * next request hooks.server.js finds no org context (the org-scoped
 * impersonation token in `jwt_access` is simply ignored), so the "operating
 * as" banner clears. `/operator` is an AUTH_ONLY route, so it stays reachable
 * with just the user-level JWT.
 *
 * @type {import('./$types').RequestHandler}
 */
export function POST({ cookies }) {
  cookies.delete('org', { path: '/' });
  throw redirect(303, '/operator');
}
