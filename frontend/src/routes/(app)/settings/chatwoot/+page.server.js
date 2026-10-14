import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import {
  getChatwootAccount,
  saveChatwootAccount,
  disconnectChatwootAccount
} from '$lib/server/v2/chatwoot.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  return await getChatwootAccount({ cookies });
}

/** @param {FormData} form */
function readValues(form) {
  return {
    base_url: form.get('base_url')?.toString().trim() ?? '',
    account_id: form.get('account_id')?.toString().trim() ?? '',
    api_access_token: form.get('api_access_token')?.toString().trim() ?? '',
    seat_limit: form.get('seat_limit')?.toString().trim() ?? '',
    is_active: form.get('is_active') === 'true'
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  // Admin-only server-side (`ChatwootAccountView.put` checks `is_org_admin`
  // first). `can_edit` only hides the form.
  async save(event) {
    const form = await event.request.formData();
    const values = readValues(form);
    try {
      await saveChatwootAccount(event, values);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, { save: { error: get(_)('settings.chatwoot.error_forbidden') } });
      }
      return fail(400, {
        save: { error: readableError(err, get(_)('settings.chatwoot.error_save_fallback')) }
      });
    }
    return { saved: true };
  },

  async remove(event) {
    try {
      await disconnectChatwootAccount(event);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, { remove: { error: get(_)('settings.chatwoot.error_forbidden') } });
      }
      return fail(400, {
        remove: { error: readableError(err, get(_)('settings.chatwoot.error_remove_fallback')) }
      });
    }
    return { removed: true };
  }
};
