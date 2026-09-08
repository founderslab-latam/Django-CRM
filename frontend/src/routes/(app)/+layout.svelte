<script>
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { _ } from '$lib/i18n/index.js';
  import '../../app.css';
  import '$lib/v2/styles/v2.css';
  import { page } from '$app/state';
  import { afterNavigate } from '$app/navigation';
  import Sidebar from '$lib/v2/components/Sidebar.svelte';
  import CommandPalette from '$lib/v2/components/CommandPalette.svelte';
  import { Search, Sun, Columns3, LifeBuoy, Receipt, Plus, Menu } from '@lucide/svelte';

  /** @type {{ data: { counts: Record<string, number>, org: { name: string, terminology?: Record<string, string> | null, logo_url?: string | null }, role: string, is_superuser?: boolean, impersonated?: boolean }, children: import('svelte').Snippet }} */
  let { data, children } = $props();

  let paletteOpen = $state(false);

  // The sidebar is hidden below 768px, and the tab bar only carries four of the
  // ~16 destinations. This drawer is how a phone reaches the rest of the nav and
  // the footer: profile, notifications, help, sign out. It reuses the same
  // <Sidebar>, so the two can never drift apart. Closes itself on navigation.
  let menuOpen = $state(false);
  afterNavigate(() => (menuOpen = false));

  /** Focus the panel on open so Escape reaches it and keyboard users land inside. */
  function autofocus(/** @type {HTMLElement} */ node) {
    node.focus();
  }

  /**
   * The five things worth a thumb on a phone. Fewer than the sidebar on
   * purpose. A tab bar that scrolls is a menu wearing a tab bar's clothes.
   */
  const TABS = [
    { href: '/', label: 'Today', icon: Sun, exact: true },
    { href: '/pipeline', label: 'Pipeline', icon: Columns3 },
    { href: '/tickets', label: 'Tickets', icon: LifeBuoy },
    { href: '/invoices', label: 'Invoices', icon: Receipt }
  ];

  const isActive = (href, exact) =>
    exact ? page.url.pathname === href : page.url.pathname.startsWith(href);

  function onkeydown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      paletteOpen = !paletteOpen;
    } else if (e.key === 'Escape' && menuOpen) {
      menuOpen = false;
    }
  }
</script>

<svelte:head>
  <title>BottleCRM v2</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<svelte:window {onkeydown} />

<div class="v2-root v2-shell">
  <Sidebar
    counts={data.counts}
    org={data.org}
    role={data.role}
    isSuperuser={data.is_superuser}
    terminology={data.org.terminology}
    onsearch={() => (paletteOpen = true)}
  />
  <div class="v2-main">
    {#if data.impersonated}
      <div class="v2-impersonation-bar" role="status">
        <span>
          {$_('operator.banner.text', { values: { org: data.org.name } })}
        </span>
        <form method="POST" action="/operator/exit">
          <button type="submit">{$_('operator.banner.exit')}</button>
        </form>
      </div>
    {/if}
    <!-- Phone top bar. The sidebar is hidden below 768px; this replaces the
         org mark and the search affordance it carried. -->
    <div class="v2-mobile-top">
      <button
        class="v2-btn v2-btn-quiet"
        type="button"
        onclick={() => (menuOpen = true)}
        aria-label={$_('common.nav.aria_open_menu')}
        aria-expanded={menuOpen}
      >
        <Menu />
      </button>
      {#if data.org.logo_url}
        <img class="v2-mobile-logo" src={data.org.logo_url} alt={data.org.name} />
      {:else}
        <span class="v2-mark">{data.org.name.slice(0, 1)}</span>
        <h2>{data.org.name}</h2>
      {/if}
      <button
        class="v2-btn v2-btn-quiet"
        type="button"
        style="margin-left:auto"
        onclick={() => (paletteOpen = true)}
        aria-label={$_('common.nav.aria_search')}
      >
        <Search />
      </button>
    </div>

    {@render children()}

    <nav class="v2-tabbar" aria-label={$_('common.nav.aria_sections')}>
      {#each TABS as tab (tab.href)}
        <a
          href={resolve(asInternalPath(tab.href))}
          aria-current={isActive(tab.href, tab.exact) ? 'page' : undefined}
        >
          <tab.icon />
          {tab.label}
        </a>
      {/each}
    </nav>
  </div>

  <!-- Both live inside .v2-root so they inherit the scoped tokens; both are
       position:fixed, so the shell's overflow:hidden does not clip them. -->
  <a class="v2-fab" href={resolve('/pipeline/new')} aria-label={$_('common.nav.aria_new_deal')}
    ><Plus size={21} /></a
  >

  <!-- Mobile navigation drawer. Only openable from the mobile top bar, so it
       never surfaces on desktop; a backdrop click, Escape, or navigating all
       close it. It renders the same <Sidebar> the desktop shows. -->
  {#if menuOpen}
    <div
      class="v2-drawer-scrim"
      role="presentation"
      onclick={(e) => {
        if (e.target === e.currentTarget) menuOpen = false;
      }}
    >
      <div
        class="v2-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={$_('common.nav.aria_navigation')}
        tabindex="-1"
        use:autofocus
        onkeydown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault();
            menuOpen = false;
          }
        }}
      >
        <Sidebar
          counts={data.counts}
          org={data.org}
          role={data.role}
          isSuperuser={data.is_superuser}
          terminology={data.org.terminology}
          onsearch={() => {
            menuOpen = false;
            paletteOpen = true;
          }}
        />
      </div>
    </div>
  {/if}

  <CommandPalette open={paletteOpen} onclose={() => (paletteOpen = false)} />
</div>

<style>
  .v2-impersonation-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 550;
    color: #fff;
    background: var(--v2-rust, #b4462e);
  }
  .v2-impersonation-bar form {
    margin: 0;
  }
  .v2-impersonation-bar button {
    border: 1px solid rgba(255, 255, 255, 0.5);
    background: transparent;
    color: #fff;
    font: inherit;
    padding: 3px 10px;
    border-radius: 5px;
    cursor: pointer;
  }
  .v2-impersonation-bar button:hover {
    background: rgba(255, 255, 255, 0.15);
  }
  .v2-mobile-logo {
    max-height: 30px;
    max-width: 190px;
    object-fit: contain;
    object-position: left center;
    display: block;
  }
</style>
