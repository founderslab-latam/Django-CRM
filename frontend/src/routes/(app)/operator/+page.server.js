import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { listOrgs, orgLifecycle, updateOrg, verifyOrgDomain } from '$lib/server/v2/operator.js';
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

  // Set, change or clear (blank) an org's customer-owned domain. The backend
  // drops the verification on any change, so a new domain is never routed
  // before `verifyDomain` has seen it point here.
  setDomain: async (event) => {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    const domain = form.get('custom_domain')?.toString().trim() ?? '';
    if (!id) return fail(400, { error: get(_)('operator.list.error_bad_request') });
    try {
      await updateOrg(event, id, { custom_domain: domain });
    } catch (/** @type {any} */ err) {
      return fail(400, { error: readableError(err, get(_)('operator.list.error_fallback')) });
    }
    return { ok: true };
  },

  verifyDomain: async (event) => {
    const form = await event.request.formData();
    const id = form.get('id')?.toString() ?? '';
    if (!id) return fail(400, { error: get(_)('operator.list.error_bad_request') });
    try {
      const res = await verifyOrgDomain(event, id);
      return { domainCheck: { id, verified: res.verified === true, detail: res.detail ?? '' } };
    } catch (/** @type {any} */ err) {
      return fail(400, { error: readableError(err, get(_)('operator.list.error_fallback')) });
    }
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
