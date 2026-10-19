import { json } from '@sveltejs/kit';
import { testMailboxConnection, readServerFields } from '$lib/server/v2/inbound-email.js';

/**
 * The form's "Test connection" button. A JSON endpoint rather than a form
 * action: `SettingsFormPanel` closes on any successful action, and testing
 * must leave the form open with the result beside the fields.
 *
 * @type {import('./$types').RequestHandler}
 */
export async function POST(event) {
  const form = await event.request.formData();
  const values = {
    ...readServerFields(form),
    mailbox_id: form.get('id')?.toString() ?? ''
  };
  try {
    return json(await testMailboxConnection(event, values));
  } catch (/** @type {any} */ err) {
    return json({ error: true }, { status: err?.status === 403 ? 403 : 400 });
  }
}
