import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { EDITABLE_FIELDS, createDeal, getDealFormOptions } from '$lib/server/v2/deals.js';
import { _ } from '$lib/i18n/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load(event) {
  // The currency hint under the amount comes from the shell (`data.org.currency`
  // via `(app)/+layout.server.js`). It is the currency this deal will be created
  // in: the form has no currency field, so the serializer stamps the org default
  // (`OpportunityCreateSerializer.create`).
  return await getDealFormOptions(event);
}

/** @type {import('./$types').Actions} */
export const actions = {
  async create(event) {
    const form = await event.request.formData();

    /** @type {Record<string, any>} */
    const values = {};
    for (const field of [...EDITABLE_FIELDS, 'assigned_to']) {
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }
    const contacts = form.getAll('contacts').map((id) => id.toString());
    if (contacts.length) values.contacts = contacts;

    /** @type {any} */
    let created;
    try {
      created = await createDeal(event, values);
    } catch (/** @type {any} */ err) {
      // `values` goes back so a rejected form is not a blank form. Retyping
      // eight fields because the ninth collided is how people learn to
      // distrust a create page.
      //
      // See the equivalent comment in `[id]/edit/+page.server.js`: the
      // request's locale is already resolved on the shared `locale` store by
      // `hooks.server.js` before this action runs.
      return fail(400, {
        values,
        error: String(err?.message ?? get(_)('opportunity.new.error_fallback'))
      });
    }

    // Straight to the deal, not back to the list: the next thing anyone does
    // after creating one is look at it.
    redirect(303, created?.id ? `/pipeline/${created.id}` : '/pipeline');
  }
};
