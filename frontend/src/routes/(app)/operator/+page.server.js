import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { listOrgs, orgLifecycle } from '$lib/server/v2/operator.js';
import { readableError } from '$lib/server/v2/form-errors.js';

const LIFECYCLE = ['suspend', 'delete', 'reactivate', 'restore'];

/** @type {import('./$types').PageServerLoad} */
export async function load(event) {
  const status = event.url.searchParams.get('status') ?? '';
  const search = event.url.searchParams.get('search') ?? '';
  const orgs = await listOrgs(event, { status, search }).catch(() => []);
  return { orgs, filter: { status, search } };
}

/** @type {import('./$types').Actions} */
export const actions = {
  // Change an org's lifecycle state.
  lifecycle: async (event) => {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    const action = form.get('action')?.toString() ?? '';
    const reason = form.get('reason')?.toString().trim() ?? '';
    if (!id || !LIFECYCLE.includes(action)) {
      return fail(400, { error: get(_)('operator.list.error_bad_request') });
    }
    try {
      await orgLifecycle(event, id, action, reason);
    } catch (/** @type {any} */ err) {
      return fail(400, { error: readableError(err, get(_)('operator.list.error_fallback')) });
    }
    return { ok: true };
  },

  // Enter a tenant as an ADMIN (impersonation). Setting the `org` cookie is
  // enough: hooks.server.js sees it differs from the token's org and calls
  // switch-org, which for a superuser non-member mints the operator profile.
  enter: async (event) => {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    if (!id) return fail(400, { error: get(_)('operator.list.error_bad_request') });
    event.cookies.set('org', id, {
      path: '/',
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 60 * 24
    });
    throw redirect(303, '/');
  }
};
