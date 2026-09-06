import { fail, redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import { createSupportTicket, SUPPORT_CATEGORIES } from '$lib/server/v2/support.js';
import { readableError } from '$lib/server/v2/form-errors.js';

export function load() {
  return { categories: SUPPORT_CATEGORIES };
}

/** @type {import('./$types').Actions} */
export const actions = {
  default: async ({ cookies, request }) => {
    const form = await request.formData();
    const subject = form.get('subject')?.toString().trim() ?? '';
    const category = form.get('category')?.toString() ?? '';
    const body = form.get('body')?.toString().trim() ?? '';
    const picked = form.get('attachment');
    const attachment =
      picked && typeof picked === 'object' && 'size' in picked && picked.size > 0 ? picked : null;

    if (!subject || !body || !SUPPORT_CATEGORIES.some((item) => item.value === category)) {
      return fail(400, {
        subject,
        category,
        body,
        error: get(_)('help.new.error_incomplete')
      });
    }

    let ticket;
    try {
      ticket = await createSupportTicket({ cookies }, { subject, category, body, attachment });
    } catch (/** @type {any} */ error) {
      // The queue is an enterprise feature, so a 404 here is the deployment
      // saying it has none, not a bad request. The list page hides the button
      // that leads here in that case, but the URL is still typeable.
      return fail(400, {
        subject,
        category,
        body,
        error:
          error?.status === 404
            ? get(_)('help.new.error_no_queue')
            : readableError(error, get(_)('help.new.error_fallback'))
      });
    }
    redirect(303, `/help/${ticket.id}`);
  }
};
