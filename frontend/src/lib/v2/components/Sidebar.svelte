<script>
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { page } from '$app/state';
  import {
    Sun,
    Columns3,
    Target,
    Building2,
    Users,
    CircleCheck,
    LifeBuoy,
    BookOpen,
    Receipt,
    Trophy,
    Clock,
    UserCog,
    CircleUser,
    CircleHelp,
    FileText,
    Bell,
    SlidersHorizontal,
    Search,
    Smartphone,
    ShieldCheck,
    LogOut
  } from '@lucide/svelte';
  import { t } from '$lib/terminology.js';
  import { _ } from '$lib/i18n/index.js';

  /**
   * One flat tree, grouped by what the person is doing rather than by which
   * Django app owns the model. Every label matches the route it lands on and
   * the page title it lands on; "Pipeline" goes to /v2/pipeline, which is
   * titled "Pipeline".
   *
   * v1 had /leads listed twice, as "Pipeline" and as "Leads", and a "Deals"
   * entry pointing at /opportunities while /deals 404'd.
   *
   * `role` is server-derived from the JWT (see the app layout loader). It only
   * decides which destinations to *show*. Every hidden one is still enforced
   * by the backend, so this is UX, not access control. An item marked `admin`
   * is one where a member gets nothing but a "for administrators" gate, so
   * showing it would only teach them to bounce off it.
   *
   * `termKey` marks the handful of entity destinations a vertical pack may
   * relabel (see `$lib/terminology.js`). The string in `label` below is only
   * ever the fallback an org with no pack, or no override for that key,
   * still renders; the derived `groups` below is what actually resolves it
   * against `terminology`. No other label branches on the org at all.
   *
   * @type {{
   *   counts?: Record<string, number>,
   *   org?: { name: string, logo_url?: string | null },
   *   role?: string,
   *   isSuperuser?: boolean,
   *   terminology?: Record<string, string> | null,
   *   onsearch?: () => void
   * }}
   */
  let {
    counts = {},
    org = { name: 'BottleCRM' },
    role = 'USER',
    isSuperuser = false,
    terminology = undefined,
    onsearch = () => {}
  } = $props();

  /**
   * One shape for every nav destination, so mapping over the (structurally
   * varied) `GROUPS` items below doesn't collapse into a narrower union that
   * drops fields particular items don't set (`exact`, `count`, `termKey`,
   * `admin`).
   *
   * @typedef {{
   *   href: string,
   *   labelKey: string,
   *   icon: import('svelte').Component,
   *   exact?: boolean,
   *   count?: string,
   *   termKey?: string,
   *   admin?: boolean
   * }} NavItem
   */

  /** @type {{ labelKey: string, items: NavItem[] }[]} */
  const GROUPS = [
    {
      labelKey: 'common.sidebar.nav.group.sell',
      items: [
        { href: '/', labelKey: 'common.sidebar.nav.today', icon: Sun, exact: true },
        {
          href: '/pipeline',
          labelKey: 'common.sidebar.nav.pipeline',
          icon: Columns3,
          count: 'pipeline',
          termKey: 'opportunity.plural'
        },
        {
          href: '/leads',
          labelKey: 'common.sidebar.nav.leads',
          icon: Target,
          count: 'leads',
          termKey: 'lead.plural'
        },
        {
          href: '/accounts',
          labelKey: 'common.sidebar.nav.accounts',
          icon: Building2,
          termKey: 'account.plural'
        },
        {
          href: '/contacts',
          labelKey: 'common.sidebar.nav.contacts',
          icon: Users,
          termKey: 'contact.plural'
        },
        { href: '/goals', labelKey: 'common.sidebar.nav.goals', icon: Trophy }
      ]
    },
    {
      labelKey: 'common.sidebar.nav.group.serve',
      items: [
        { href: '/tasks', labelKey: 'common.sidebar.nav.tasks', icon: CircleCheck, count: 'tasks' },
        // Approvals and Analytics live under Tickets as section tabs. They are
        // not separate destinations, so they do not get separate nav entries,
        // one level of navigation, and the tab strip carries the rest.
        {
          href: '/tickets',
          labelKey: 'common.sidebar.nav.tickets',
          icon: LifeBuoy,
          count: 'tickets'
        },
        { href: '/solutions', labelKey: 'common.sidebar.nav.knowledge_base', icon: BookOpen },
        { href: '/documents', labelKey: 'common.sidebar.nav.documents', icon: FileText }
      ]
    },
    {
      labelKey: 'common.sidebar.nav.group.bill',
      items: [
        {
          href: '/invoices',
          labelKey: 'common.sidebar.nav.invoices',
          icon: Receipt,
          count: 'invoices',
          termKey: 'invoice.plural'
        },
        { href: '/timesheet', labelKey: 'common.sidebar.nav.timesheet', icon: Clock }
      ]
    },
    {
      // Administration, kept apart from the work. Someone who never touches
      // these should not read past them four times a day.
      //
      // Team is admin-only. A member reaches it only to be told so. Settings
      // is not: the hub is readable by any member (it just omits admin-only
      // counts), so it stays for everyone.
      labelKey: 'common.sidebar.nav.group.run',
      items: [
        { href: '/team', labelKey: 'common.sidebar.nav.team', icon: UserCog, admin: true },
        { href: '/settings', labelKey: 'common.sidebar.nav.settings', icon: SlidersHorizontal }
      ]
    }
  ];

  // Drop admin-only items for members, resolve any relabelled entity through
  // the terminology map (falling back to the translated label, never the
  // untranslated key), then drop any group left with nothing.
  let groups = $derived(
    GROUPS.map((group) => ({
      ...group,
      label: $_(group.labelKey),
      items: group.items
        .filter((item) => role === 'ADMIN' || !item.admin)
        .map((item) => {
          const fallback = $_(item.labelKey);
          return {
            ...item,
            label: item.termKey ? t(terminology, item.termKey, fallback) : fallback
          };
        })
    })).filter((group) => group.items.length > 0)
  );

  const isActive = (href, exact) =>
    exact ? page.url.pathname === href : page.url.pathname.startsWith(href);
</script>

<nav class="v2-nav" aria-label={$_('common.sidebar.nav.landmark')}>
  <div class="v2-org">
    {#if org.logo_url}
      <img class="v2-org-logo" src={org.logo_url} alt={org.name} />
    {:else}
      <span class="v2-mark">{org.name.slice(0, 1)}</span>
      <b>{org.name}</b>
    {/if}
  </div>

  <!--
    No entry appears here without a route behind it. v1's "Deals" pointed at
    /opportunities while /deals 404'd; an Inbox link with nothing behind it
    would be the same mistake.
  -->
  {#each groups as group (group.label)}
    <div class="v2-nav-group v2-label">{group.label}</div>
    {#each group.items as item (item.href)}
      <a
        class="v2-link"
        href={resolve(asInternalPath(item.href))}
        aria-current={isActive(item.href, item.exact) ? 'page' : undefined}
      >
        <item.icon />
        {item.label}
        {#if item.count && counts[item.count]}
          <span class="v2-count">{counts[item.count]}</span>
        {/if}
      </a>
    {/each}
  {/each}

  <div class="v2-nav-foot">
    <button class="v2-link v2-nav-search" type="button" onclick={onsearch}>
      <Search />
      {$_('common.sidebar.nav.search')}
      <span class="v2-count">⌘K</span>
    </button>
    <!-- Personal, not work: your own feed sits with your own profile rather
         than in Serve, where it would read as a queue the team shares. -->
    <a
      class="v2-link"
      href={resolve('/notifications')}
      aria-current={isActive('/notifications', false) ? 'page' : undefined}
    >
      <Bell />
      {$_('common.sidebar.nav.notifications')}
      {#if counts.notifications}
        <span class="v2-count">{counts.notifications}</span>
      {/if}
    </a>
    <a class="v2-link" href={resolve('/profile')}>
      <CircleUser />
      {$_('common.sidebar.nav.profile')}
    </a>
    {#if isSuperuser}
      <a
        class="v2-link"
        href={resolve('/operator')}
        aria-current={isActive('/operator', false) ? 'page' : undefined}
      >
        <ShieldCheck />
        {$_('common.sidebar.nav.operator')}
      </a>
    {/if}
    <a class="v2-link" href={resolve('/help')}>
      <CircleHelp />
      {$_('common.sidebar.nav.help')}
    </a>
    <!-- The phone app for people on the hosted service. No pulsing dot. A
         download link is not something that needs you right now, and v2 keeps
         attention for the things that do. -->
    <a
      class="v2-link"
      href="https://play.google.com/store/apps/details?id=io.bottlecrm&hl=en"
      target="_blank"
      rel="noopener noreferrer"
    >
      <Smartphone />
      {$_('common.sidebar.nav.download_app')}
    </a>
    <!-- Leaving the app. Last in the list, and a plain link. /logout is a
         server load that clears the auth cookies and redirects to /login, so a
         GET navigation is all it takes and no data-fetching component follows. -->
    <a class="v2-link" href={resolve('/logout')} data-sveltekit-reload>
      <LogOut />
      {$_('common.sidebar.nav.sign_out')}
    </a>
  </div>
</nav>

<style>
  /* A logo stands in for the wordmark, so give it the whole rail. The rail's
     inner width is ~184px (222 nav − 22 nav padding − 16 .v2-org padding);
     drop the side padding when a logo is present so it can span the full
     width, centre it, and allow real height so a horizontal wordmark stays
     legible. */
  .v2-org:has(.v2-org-logo) {
    justify-content: center;
    padding-left: 2px;
    padding-right: 2px;
  }
  .v2-org-logo {
    width: 100%;
    max-width: 100%;
    max-height: 44px;
    object-fit: contain;
    object-position: center;
    display: block;
  }

  /* Search opens an overlay rather than navigating, so it is a button. It
     borrows .v2-link for everything else. A control that sits in a list of
     links should not look like the odd one out. */
  .v2-nav-search {
    width: 100%;
    background: none;
    border: 0;
    font-family: inherit;
    font-size: inherit;
    text-align: left;
    cursor: pointer;
  }
</style>
