import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { EDITABLE_FIELDS, getDealForEdit, updateDeal } from '$lib/server/v2/deals.js';
import { _ } from '$lib/i18n/index.js';

/** @type {import('./$types').PageServerLoad} */
export async function load(event) {
  return await getDealForEdit(event, event.params.id);
}

/** @type {import('./$types').Actions} */
export const actions = {
  async save(event) {
    const form = await event.request.formData();

    /**
     * Only fields the form actually submitted. A disabled input sends nothing,
     * and PATCH reads absent as "leave this alone", which is exactly right
     * for the amount on a deal whose line items own it.
     * @type {Record<string, any>}
     */
    const values = {};
    for (const field of EDITABLE_FIELDS) {
      if (form.has(field)) values[field] = form.get(field)?.toString().trim() ?? '';
    }

    /*
     * The owner is only sent when somebody actually changed it.
     *
     * `assigned_to` is many-to-many and this form offers a single select, so
     * sending it unconditionally rewrites the whole list from one value,
     * a deal with two people on it silently loses one every time anybody
     * edits the description. Caught by saving a real two-assignee deal and
     * counting the assignees afterwards.
     *
     * Comparing against the value the form was rendered with keeps "nobody
     * touched this" distinguishable from "somebody chose this", which is the
     * distinction PATCH is built on.
     */
    const owner = form.get('assigned_to')?.toString().trim() ?? '';
    const ownerWas = form.get('assigned_to_original')?.toString().trim() ?? '';
    if (owner !== ownerWas) values.assigned_to = owner;

    // A multi-select submits nothing when fully deselected, which reads the
    // same as a field this form does not own. The hidden `contacts_present`
    // marker is what lets "remove the last contact" be expressible.
    if (form.has('contacts_present')) {
      values.contacts = form.getAll('contacts').map((id) => id.toString());
    }

    try {
      await updateDeal(event, event.params.id, values);
    } catch (/** @type {any} */ err) {
      // The API's field errors are the ones that count: this form's own
      // checks are a UX hint and the serializer is the rule.
      //
      // The request's locale was already resolved into the shared, per-process
      // `locale` store by `setupI18n()` in `hooks.server.js` before this
      // action ran (same request, awaited before `resolve()`), so reading it
      // here gets this request's language. See the SSR caveat documented on
      // that store: not request-isolated, accepted for this pilot's scope.
      return fail(400, {
        values,
        error: String(err?.message ?? get(_)('opportunity.edit.error_fallback'))
      });
    }

    return { saved: true };
  }
};
