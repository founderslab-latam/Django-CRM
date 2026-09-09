// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
  namespace App {
    // interface Error {}
    interface Locals {
      user?: any; // You might want to replace 'any' with a more specific type for user
      org?: any; // You might want to replace 'any' with a more specific type for org
      org_name?: string;
      // Per-tenant subdomain routing: the org this request's host belongs to,
      // or null on the bare domain / an unknown subdomain. Resolved in
      // hooks.server.js via GET /api/org/by-host/.
      host_org?: {
        id: string;
        name: string;
        subdomain: string;
        logo_url: string | null;
        brand_color: string;
      } | null;
      // i18n pilot: resolved in hooks.server.js from the `locale` cookie,
      // always one of the supported locales in $lib/i18n (never absent by
      // the time a route's load() runs).
      locale?: string;
      org_settings?: {
        default_currency?: string;
        currency_symbol?: string;
        default_country?: string | null;
      };
      profile?: {
        role?: string;
        is_organization_admin?: boolean;
      };
    }
    // interface PageData {}
    // interface PageState {}
    // interface Platform {}
  }
}

export {};
