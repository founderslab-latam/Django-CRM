import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { EDITABLE_FIELDS, getAccountForEdit, updateAccount } from '$lib/server/v2/accounts.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { _ } from '$lib/i18n/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, params }) {
  return await getAccountForEdit({ cookies }, params.id);
}

/** @type {import('./$types').Actions} */
export const actions = {
  save: async ({ cookies, params, request }) => {
    const form = await request.formData();

    /** @type {Record<string, string>} */
    const values = {};
    for (const field of EDITABLE_FIELDS) {
      // Only fields the form actually submitted. A control that is absent or
      // disabled sends nothing, and "nothing" is how PATCH is told to leave a
      // field alone. See `updateAccount`.
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }

    /*
     * The owner is only sent when somebody actually changed it.
     *
     * `assigned_to` is many-to-many and this form offers a single select, so
     * sending it unconditionally rewrites the whole list from one value, an
     * account with two people on it silently loses one every time anybody
     * edits the phone number. The hidden `assigned_to_original` is what makes
     * "nobody touched this" distinguishable from "somebody chose this".
     */
    const owner = form.get('assigned_to')?.toString().trim() ?? '';
    const ownerWas = form.get('assigned_to_original')?.toString().trim() ?? '';
    if (owner !== ownerWas) values.assigned_to = owner;

    try {
      await updateAccount({ cookies }, params.id, values);
    } catch (/** @type {any} */ err) {
      // The request's locale was already resolved into the shared, per-process
      // `locale` store by `setupI18n()` in `hooks.server.js` before this
      // action ran (same request, awaited before `resolve()`), so reading it
      // here gets this request's language. See the SSR caveat documented on
      // that store: not request-isolated, accepted for this pilot's scope.
      return fail(400, {
        values,
        error: readableError(err, get(_)('accounts.edit.error_fallback'))
      });
    }

    redirect(303, `/accounts/${params.id}`);
  }
};
