import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { listOrgTokens, createToken, revokeToken } from '$lib/server/v2/tokens.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { expiryFromChoice, scopesFromChoice } from '$lib/v2/token-rules.js';

/**
 * API tokens (admin oversight).
 *
 * Server load, so the JWT cookie stays server-side and the raw token value.
 * Returned once on create, is handled here, never fetched from the browser.
 * The list is admin-only; a non-admin gets `forbidden` back, not a broken page.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies }) {
  return await listOrgTokens({ cookies });
}

/** @type {import('./$types').Actions} */
export const actions = {
  /**
   * Create a token for the signed-in admin. The server owns the owner (from the
   * JWT) and returns the raw value once. The page shows it a single time and
   * it is unrecoverable after. We never log it.
   */
  create: async ({ cookies, request }) => {
    const form = await request.formData();
    const name = form.get('name')?.toString().trim();
    const expires_at = expiryFromChoice(form.get('expiry')?.toString());
    const scopes = scopesFromChoice(form.get('access')?.toString());
    if (!name)
      return fail(400, { create: { error: get(_)('settings.api_tokens.err_name_required') } });

    try {
      const res = await createToken({ cookies }, { name, expires_at, scopes });
      // Shown once. `token` is the raw value; the list will only ever have the
      // prefix after this response is gone.
      return {
        created: {
          name: res.name ?? name,
          token_prefix: res.token_prefix,
          token: res.token,
          expires_at: res.expires_at ?? null
        }
      };
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 403 ? 403 : 400, {
        create: {
          error:
            err?.status === 403
              ? get(_)('settings.api_tokens.err_create_forbidden')
              : readableError(err, get(_)('settings.api_tokens.err_create_fallback'))
        }
      });
    }
  },

  /** Revoke one token by id. Admin + org-scoped server-side. */
  revoke: async ({ cookies, request }) => {
    const form = await request.formData();
    const id = form.get('id')?.toString();
    if (!id) return fail(400, { error: get(_)('settings.api_tokens.err_which_token') });
    try {
      await revokeToken({ cookies }, id);
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 403 ? 403 : 400, {
        error:
          err?.status === 403
            ? get(_)('settings.api_tokens.err_revoke_forbidden')
            : readableError(err, get(_)('settings.api_tokens.err_revoke_fallback'))
      });
    }
    return { revoked: id };
  },

  /**
   * Revoke every live token on a deactivated owner in one go. The id list is
   * re-derived from the server, not read from the form. The page cannot ask us
   * to revoke an arbitrary set, only the orphaned rows the API itself reports.
   */
  revokeOrphaned: async ({ cookies }) => {
    let ids;
    try {
      ({ orphaned_ids: ids } = await listOrgTokens({ cookies }));
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 403 ? 403 : 400, {
        error:
          err?.status === 403
            ? get(_)('settings.api_tokens.err_revoke_forbidden')
            : readableError(err, get(_)('settings.api_tokens.err_load_fallback'))
      });
    }
    if (!ids?.length) return { revokedOrphaned: 0 };

    let done = 0;
    for (const id of ids) {
      try {
        await revokeToken({ cookies }, id);
        done += 1;
      } catch {
        // Best effort: one failure should not strand the rest. The reload
        // reflects whatever actually got revoked.
      }
    }
    return { revokedOrphaned: done };
  }
};
