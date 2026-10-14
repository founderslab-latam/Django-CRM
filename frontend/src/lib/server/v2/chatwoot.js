/**
 * The org's Chatwoot account: the wiring behind `/settings/chatwoot`.
 *
 * Server-only, singleton (one row per org, same shape as
 * `$lib/server/v2/inbound-email.js`'s mailboxes but with no list -- there is
 * exactly one or none). `GET /conversations/account/` is admin-only on the
 * backend already; this layer never receives `api_access_token`'s value at
 * all, only `has_api_access_token`, for the same reason inbound-email never
 * receives `webhook_secret`: a credential that never has to render on the
 * page should never travel to the browser, admin or not.
 */
import { apiRequest } from '$lib/api-helpers.js';
import { viewerRole } from './organization.js';

/**
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @returns {Promise<{ account: any, can_edit: boolean }>}
 */
export async function getChatwootAccount({ cookies }) {
  // The backend 403s GET for a non-admin (ChatwootAccountView is admin-only
  // on every verb, unlike /cases/mailboxes/, which any member can read).
  // Checked here, before the request, so a non-admin visiting this page
  // gets a clean "admins only" state instead of an unhandled 403 bubbling
  // out of `load()`.
  if (viewerRole(cookies) !== 'ADMIN') {
    return { account: null, can_edit: false };
  }
  const { account } = await apiRequest('/conversations/account/', {}, { cookies });
  return {
    account: account
      ? {
          base_url: account.base_url,
          account_id: account.account_id,
          has_api_access_token: account.has_api_access_token === true,
          webhook_url: account.webhook_url,
          seat_limit: account.seat_limit,
          is_active: account.is_active
        }
      : null,
    // Display hint only: PUT/DELETE both re-check admin server-side and 403
    // regardless of what this says.
    can_edit: viewerRole(cookies) === 'ADMIN'
  };
}

const SAVE_FIELDS = ['base_url', 'account_id', 'api_access_token', 'seat_limit', 'is_active'];

/** @param {{ [key: string]: any }} values */
function buildBody(values) {
  /** @type {Record<string, any>} */
  const body = {};
  for (const field of SAVE_FIELDS) {
    if (values[field] === undefined) continue;
    body[field] = values[field];
  }
  if (body.account_id !== undefined) body.account_id = Number(body.account_id) || 0;
  if (body.seat_limit !== undefined) body.seat_limit = Number(body.seat_limit) || 1;
  if (body.is_active !== undefined) body.is_active = Boolean(body.is_active);
  if (body.base_url !== undefined) body.base_url = String(body.base_url).trim();
  // A blank token field means "leave it alone" (see the serializer's
  // `update()`), so an unset/blank value is sent through rather than
  // dropped, letting the backend apply that same rule.
  if (body.api_access_token !== undefined) {
    body.api_access_token = String(body.api_access_token).trim();
  }
  return body;
}

/**
 * Create or update the org's single ChatwootAccount. The backend upserts:
 * full validation the first time (base_url/account_id are required), partial
 * on every save after that.
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 */
export async function saveChatwootAccount({ cookies }, values) {
  const body = buildBody(values);
  return await apiRequest('/conversations/account/', { method: 'PUT', body }, { cookies });
}

/**
 * Disconnect the integration entirely. Hard delete, and it cascades to every
 * mirrored conversation/message for this org (see `ChatwootAccountView.delete`).
 *
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 */
export async function disconnectChatwootAccount({ cookies }) {
  return await apiRequest('/conversations/account/', { method: 'DELETE' }, { cookies });
}
