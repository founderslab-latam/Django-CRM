import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import {
  getOrgSettings,
  updateOrgSettings,
  EDITABLE_FIELDS,
  BOOLEAN_FIELDS,
  listTimezones
} from '$lib/server/v2/organization.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/**
 * Editing organization settings.
 *
 * Admin-only. The load returns `forbidden` for a non-admin (the read page only
 * links here for admins, but a direct visit must not render the form either),
 * and the save action is gated a second time by the backend, `PATCH
 * /api/org/settings/` 403s a non-admin regardless of what reaches it.
 *
 * @type {import('./$types').PageServerLoad}
 */
export async function load({ cookies }) {
  const { org, can_edit } = await getOrgSettings({ cookies });
  if (!can_edit) return { forbidden: true };
  // Fetched rather than built from `Intl`, so the option list uses the same
  // zone vocabulary the org's stored value came from. See `listTimezones`.
  const timezones = await listTimezones(cookies).catch(() => [{ name: 'UTC', label: 'UTC' }]);
  return { forbidden: false, org, timezones };
}

/** @type {import('./$types').Actions} */
export const actions = {
  save: async ({ cookies, request }) => {
    const form = await request.formData();

    /** @type {Record<string, unknown>} */
    const body = {};

    // Text and select fields: only what the form actually submitted, trimmed.
    // An absent field is left alone (PATCH is partial), never blanked.
    for (const field of EDITABLE_FIELDS) {
      if (form.has(field)) body[field] = form.get(field)?.toString().trim() ?? '';
    }

    // The two switches always submit an explicit 'true'/'false', so "off" is a
    // real value rather than the "absent → leave alone" convention above.
    for (const flag of BOOLEAN_FIELDS) {
      if (form.has(flag)) body[flag] = form.get(flag) === 'true';
    }

    // A picked logo file turns the request into multipart. An untouched file
    // input still submits a zero-byte entry, so the `size > 0` check is what
    // separates "chose a new logo" from "left it alone".
    const logo = form.get('logo');
    const hasLogo = logo && typeof logo !== 'string' && 'size' in logo && logo.size > 0;

    /** @type {Record<string, unknown> | FormData} */
    let payload = body;
    if (hasLogo) {
      payload = new FormData();
      for (const [k, v] of Object.entries(body)) {
        payload.append(k, typeof v === 'boolean' ? String(v) : /** @type {string} */ (v));
      }
      payload.append('logo', /** @type {Blob} */ (logo), /** @type {File} */ (logo).name);
    }

    try {
      await updateOrgSettings({ cookies }, payload);
    } catch (/** @type {any} */ err) {
      if (err?.status === 403) {
        return fail(403, {
          values: body,
          error: get(_)('settings.organization.edit.error_forbidden')
        });
      }
      return fail(400, {
        values: body,
        error: readableError(err, get(_)('settings.organization.edit.error_fallback'))
      });
    }

    redirect(303, '/settings/organization');
  }
};
