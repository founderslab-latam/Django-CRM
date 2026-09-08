/**
 * Set the viewer's UI language.
 *
 * The `locale` cookie is what `hooks.server.js` reads on every request, so
 * writing it here (server-side, non-httpOnly so the switcher can still read it
 * in the browser) is what actually changes the language. When the request is
 * authenticated we also persist it to the account via `PATCH /api/profile/`,
 * so the choice follows the user to their next device / session instead of
 * living only in this browser. That persistence is best-effort: a failure
 * still leaves the cookie set and the page usable.
 *
 * Top-level route on purpose — the language switcher renders on `/login`
 * (no auth, no org) as well as inside the app shell.
 */
import { json } from '@sveltejs/kit';
import { apiRequest } from '$lib/api-helpers.js';
import { SUPPORTED_LOCALES, LOCALE_COOKIE_NAME } from '$lib/i18n/index.js';

/** @type {import('./$types').RequestHandler} */
export async function POST({ request, cookies, locals }) {
  const body = await request.json().catch(() => ({}));
  const locale = body?.locale;
  if (!SUPPORTED_LOCALES.includes(locale)) {
    return json({ error: 'unsupported locale' }, { status: 400 });
  }

  cookies.set(LOCALE_COOKIE_NAME, locale, {
    path: '/',
    httpOnly: false,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60 * 24 * 365
  });

  if (locals.user) {
    try {
      await apiRequest('/profile/', { method: 'PATCH', body: { language: locale } }, { cookies });
    } catch {
      // Non-fatal: the cookie is set regardless; the stored preference just
      // won't follow the account elsewhere until the next successful save.
    }
  }

  return json({ locale });
}
