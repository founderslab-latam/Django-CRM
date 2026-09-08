/**
 * Server-side calls to the superuser operator console API (`/api/operator/`).
 * Every function takes the SvelteKit `event` (for its cookies) and talks to
 * Django, which enforces `IsOperator`. Nothing here is a security boundary --
 * the route's `+layout.server.js` gates the UI, the backend gates the data.
 */
import { apiRequest } from '$lib/api-helpers.js';

/** @param {import('@sveltejs/kit').RequestEvent} event */
export async function listOrgs(event, { status = '', search = '' } = {}) {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  if (search) params.set('search', search);
  const qs = params.toString();
  const res = await apiRequest(`/operator/orgs/${qs ? `?${qs}` : ''}`, {}, event);
  return res.organizations ?? [];
}

/** @param {import('@sveltejs/kit').RequestEvent} event */
export async function getOrg(event, id) {
  const res = await apiRequest(`/operator/orgs/${id}/`, {}, event);
  return res.organization;
}

/** @param {import('@sveltejs/kit').RequestEvent} event */
export async function createOrg(event, body) {
  const res = await apiRequest('/operator/orgs/', { method: 'POST', body }, event);
  return res; // { organization, admin_invited }
}

/** @param {import('@sveltejs/kit').RequestEvent} event */
export async function updateOrg(event, id, body) {
  const res = await apiRequest(`/operator/orgs/${id}/`, { method: 'PATCH', body }, event);
  return res.organization;
}

/**
 * One of: 'suspend' | 'delete' | 'reactivate' | 'restore'.
 * @param {import('@sveltejs/kit').RequestEvent} event
 */
export async function orgLifecycle(event, id, action, reason = '') {
  const res = await apiRequest(
    `/operator/orgs/${id}/${action}/`,
    { method: 'POST', body: reason ? { reason } : {} },
    event
  );
  return res.organization;
}
