import { fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { _ } from '$lib/i18n/index.js';
import {
  getNotifications,
  markNotificationRead,
  markAllNotificationsRead
} from '$lib/server/v2/notifications.js';

/** @type {import('./$types').PageServerLoad} */
export async function load({ cookies }) {
  return await getNotifications({ cookies });
}

/** @type {import('./$types').Actions} */
export const actions = {
  /**
   * Mark one notification read. The page updates optimistically and calls this
   * to persist; `markNotificationRead` hits the recipient-scoped endpoint, so a
   * forged id for someone else's notification is a 404 there, not a write.
   */
  read: async ({ cookies, request }) => {
    const form = await request.formData();
    const id = form.get('id')?.toString() ?? '';
    if (!id) return fail(400, { error: get(_)('notifications.list.error_missing_id') });

    try {
      await markNotificationRead({ cookies }, id);
    } catch (/** @type {any} */ err) {
      return fail(err?.status === 404 ? 404 : 500, {
        error: get(_)('notifications.list.error_mark_read')
      });
    }
    return { ok: true };
  },

  /** Mark every unread notification read. */
  readAll: async ({ cookies }) => {
    try {
      await markAllNotificationsRead({ cookies });
    } catch {
      return fail(500, { error: get(_)('notifications.list.error_mark_all_read') });
    }
    return { ok: true };
  }
};
