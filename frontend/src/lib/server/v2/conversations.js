/**
 * Chatwoot conversations (Live Chat + WhatsApp) linked to a Contact or a
 * Lead -- the panel on their detail page that lists them and links into
 * Chatwoot's own agent dashboard. Email stays out of this: it's on the
 * native pipeline and shown through the existing ticket/case views.
 *
 * Never lets a failure here break the page it's attached to: a brand-new
 * org with no Chatwoot wired up yet still has a Contact/Lead detail page
 * that renders, just with an empty conversation list.
 */
import { apiRequest } from '$lib/api-helpers.js';

/**
 * @param {{ cookies: import('@sveltejs/kit').Cookies }} event
 * @param {{ contact?: string, lead?: string }} who exactly one of the two
 * @returns {Promise<Array<{
 *   id: string, channel: string, channel_display: string,
 *   status: string, status_display: string, chatwoot_conversation_id: number,
 *   embed_url: string, created_at: string, resolved_at: string|null
 * }>>}
 */
export async function getChatwootConversations({ cookies }, who) {
  const params = new URLSearchParams(who);
  try {
    const res = await apiRequest(`/conversations/chatwoot/?${params}`, {}, { cookies });
    return Array.isArray(res) ? res : [];
  } catch {
    return [];
  }
}
