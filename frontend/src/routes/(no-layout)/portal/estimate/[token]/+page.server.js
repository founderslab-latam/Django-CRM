/**
 * Public Estimate Portal Page
 *
 * Public view for clients to see their estimate via token.
 * No authentication required.
 */

import { error, fail } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { env } from '$env/dynamic/public';
import { _ } from '$lib/i18n/index.js';

// The Django API, reached server-to-server. Absolute (not a relative `/api/...`
// that only resolves behind a production reverse proxy) so the anonymous portal
// works the same in dev and prod. The CSAT loader takes the same approach.
const API_BASE_URL = `${env.PUBLIC_DJANGO_API_URL}/api`;

/** @type {import('./$types').PageServerLoad} */
export async function load({ params, fetch }) {
  const { token } = params;

  if (!token) {
    throw error(400, get(_)('portal.estimate.error_token_required'));
  }

  try {
    // Fetch estimate from public API (no auth). The v2 portal renders the
    // Django shape directly (snake_case, template nested), so pass it through
    // rather than re-mapping to camelCase.
    const response = await fetch(`${API_BASE_URL}/public/estimate/${token}/`);

    if (!response.ok) {
      if (response.status === 404) {
        throw error(404, get(_)('portal.estimate.error_not_found'));
      }
      throw error(response.status, get(_)('portal.estimate.error_load'));
    }

    const estimate = await response.json();

    return { estimate, token };
  } catch (err) {
    if (err.status) throw err;
    console.error('Error loading public estimate:', err);
    throw error(500, get(_)('portal.estimate.error_load'));
  }
}

/** @type {import('./$types').Actions} */
export const actions = {
  accept: async ({ params, fetch, request, getClientAddress }) => {
    const { token } = params;

    // Accepting authorises the quote's price, so the server now requires the
    // acceptor to identify themselves. Collect their name and email, and pass
    // the real client IP/user-agent through so the acceptance record reflects
    // the customer, not this SvelteKit server.
    const formData = await request.formData();
    const name = (formData.get('name') || '').toString().trim();
    const email = (formData.get('email') || '').toString().trim();

    if (!name || !email) {
      return fail(400, {
        error: get(_)('portal.estimate.error_name_email_required'),
        values: { name, email }
      });
    }

    try {
      const response = await fetch(`${API_BASE_URL}/public/estimate/${token}/accept/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Forwarded-For': getClientAddress(),
          'User-Agent': request.headers.get('user-agent') || ''
        },
        body: JSON.stringify({ name, email })
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        return fail(response.status, {
          error: data.message || get(_)('portal.estimate.error_accept'),
          values: { name, email }
        });
      }

      return { success: true, action: 'accepted' };
    } catch (err) {
      console.error('Error accepting estimate:', err);
      return fail(500, { error: get(_)('portal.estimate.error_accept') });
    }
  },

  decline: async ({ params, fetch }) => {
    const { token } = params;

    try {
      const response = await fetch(`${API_BASE_URL}/public/estimate/${token}/decline/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const data = await response.json();
        return fail(response.status, {
          error: data.message || get(_)('portal.estimate.error_decline')
        });
      }

      return { success: true, action: 'declined' };
    } catch (err) {
      console.error('Error declining estimate:', err);
      return fail(500, { error: get(_)('portal.estimate.error_decline') });
    }
  }
};
