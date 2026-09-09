/**
 * Which tenant, if any, the current request's host belongs to.
 *
 * Per-tenant subdomain routing: the app is reachable at
 * `<subdomain>.<base>` and `<routing_key>.<base>` as well as the bare base
 * domain. `hooks.server.js` calls this once per request to decide whether it
 * is on a tenant subdomain and, if so, to brand pre-auth pages and to pin the
 * session to that org.
 *
 * The backend answers `GET /api/org/by-host/` anonymously; a 404 means "not a
 * tenant host" and is cached the same as a hit, so the bare domain and unknown
 * subdomains cost one lookup, not one per request.
 */
import { env } from '$env/dynamic/public';

/** @typedef {{ id: string, name: string, subdomain: string, logo_url: string|null, brand_color: string }} HostOrg */

const TTL_MS = 60_000;
/** @type {Map<string, { value: HostOrg | null, at: number }>} */
const cache = new Map();

/**
 * @param {string} host - the browser-facing host, e.g. `acme.crm.example.com`
 * @param {typeof fetch} [fetchImpl]
 * @returns {Promise<HostOrg | null>}
 */
export async function resolveHostOrg(host, fetchImpl = fetch) {
  if (!host) return null;
  const key = host.toLowerCase();
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.value;

  /** @type {HostOrg | null} */
  let value = null;
  try {
    const url = `${env.PUBLIC_DJANGO_API_URL}/api/org/by-host/?host=${encodeURIComponent(host)}`;
    const res = await fetchImpl(url, { headers: { accept: 'application/json' } });
    if (res.ok) {
      const data = await res.json();
      value = data?.org ?? null;
    }
    // A non-OK response (typically 404 "not a tenant host") caches as null.
  } catch {
    // Network/API trouble: treat as "not a tenant host" for this request and
    // let the short TTL retry. The bare-domain experience is the safe default.
    value = null;
  }

  cache.set(key, { value, at: Date.now() });
  return value;
}

/** Test seam. */
export function _clearHostOrgCache() {
  cache.clear();
}
