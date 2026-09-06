import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { getSupportTicket, replyToSupportTicket } from '$lib/server/v2/support.js';
import { readableError } from '$lib/server/v2/form-errors.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies, params }) {
  return { ticket: await getSupportTicket({ cookies }, params.id) };
}

/** @type {import('./$types').Actions} */
export const actions = {
  reply: async ({ cookies, params, request }) => {
    const form = await request.formData();
    const body = form.get('body')?.toString().trim() ?? '';
    const picked = form.get('attachment');
    const attachment =
      picked && typeof picked === 'object' && 'size' in picked && picked.size > 0 ? picked : null;
    if (!body && !attachment) {
      return fail(400, { body, error: get(_)('help.detail.error_empty') });
    }
    try {
      await replyToSupportTicket({ cookies }, params.id, { body, attachment });
      return { sent: true };
    } catch (/** @type {any} */ error) {
      return fail(400, {
        body,
        error: readableError(error, get(_)('help.detail.error_fallback'))
      });
    }
  }
};
