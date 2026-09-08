import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { createOrg } from '$lib/server/v2/operator.js';
import { readableError } from '$lib/server/v2/form-errors.js';
import { CURRENCY_CODES } from '$lib/constants/filters.js';

/** @type {import('./$types').PageServerLoad} */
export function load() {
  return {
    currencies: CURRENCY_CODES.filter((/** @type {any} */ c) => c.value)
  };
}

/** @type {import('./$types').Actions} */
export const actions = {
  create: async (event) => {
    const form = await event.request.formData();
    /** @type {Record<string, string>} */
    const body = {};
    for (const field of [
      'name',
      'default_currency',
      'default_country',
      'subdomain',
      'admin_email'
    ]) {
      const v = form.get(field)?.toString().trim() ?? '';
      if (v) body[field] = v;
    }
    if (!body.name) {
      return fail(400, { values: body, error: get(_)('operator.new.error_name_required') });
    }

    /** @type {any} */
    let result;
    try {
      result = await createOrg(event, body);
    } catch (/** @type {any} */ err) {
      return fail(400, {
        values: body,
        error: readableError(err, get(_)('operator.new.error_fallback'))
      });
    }
    throw redirect(303, `/operator?created=${result?.organization?.id ?? ''}`);
  }
};
