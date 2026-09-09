/**
 * Shown when a signed-in user lands on a tenant subdomain whose org they are
 * not a member of. `hooks.server.js` redirects here rather than switching the
 * session silently. The page offers the way back to the main app, where the
 * user can pick one of the orgs they do belong to.
 */

/** @type {import('./$types').PageServerLoad} */
export async function load({ locals, url }) {
  const hostOrg = locals.host_org ?? null;
  // The bare base domain is this host with its first label removed.
  const mainAppHost = url.host.split('.').slice(1).join('.') || url.host;

  return {
    orgName: hostOrg?.name ?? '',
    mainAppUrl: `${url.protocol}//${mainAppHost}`,
    signedInAs: locals.user?.email ?? ''
  };
}
