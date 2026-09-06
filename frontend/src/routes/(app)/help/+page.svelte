<script>
  /**
   * Help.
   *
   * ── TWO TIERS, ONE PAGE ──────────────────────────────────────────────────
   * "Start here" is always shown, because somebody who opens Help is stuck and
   * the fastest fix is usually a page they already have. Below it the page
   * splits on `data.available`, which the load sets from whether the enterprise
   * support queue answered:
   *
   *   available   their tickets with the BottleCRM team, and a way to open one
   *   otherwise   how to reach a person, and what to tell them
   *
   * The second tier is not a degraded state, it is the whole of what a
   * community deployment can offer, and it is the page this route served
   * before the queue existed. Rendering an error there would take away help
   * from the one person guaranteed to need it.
   *
   * ── WHAT THIS PAGE IS NOT ────────────────────────────────────────────────
   * v1's support page was 647 lines of mission statement and pricing rationale
   * shown to people who have ALREADY BOUGHT and are, by the fact of being here,
   * stuck. Sales copy belongs on the marketing site, a different repo.
   *
   * Nothing identifying is rendered: no org id, no token, no email, no user id.
   * A help page that prints an identifier is a help page that puts it in
   * screenshots.
   */
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import { relativeTime } from '$lib/v2/format.js';
  import { _ } from '$lib/i18n/index.js';
  import { BookOpen, LifeBuoy, Plus, Bug, Mail, ArrowUpRight, ClipboardList } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  const STATUS_TONE = {
    open: 'rust',
    in_progress: 'clay',
    waiting_on_customer: 'sky',
    resolved: 'moss',
    closed: 'slate'
  };

  const SELF_SERVE = [
    { href: '/solutions', icon: BookOpen, key: 'kb' },
    { href: '/tickets', icon: LifeBuoy, key: 'tickets' },
    { href: '/settings', icon: ClipboardList, key: 'settings' }
  ];

  /**
   * These hrefs leave the app, so they are rendered as-is.
   *
   * Not through `resolve()`: it throws on anything that is not an internal
   * pathname or route id, which is a 500 for the whole page. `asInternalPath`
   * does not save you, it is a typecheck shim that returns its argument as
   * `any`, so an external URL passed through it compiles clean and fails at
   * render. Every other external link in this codebase is written straight
   * onto the anchor for the same reason.
   */
  const CONTACT = [
    {
      href: 'https://github.com/django-crm/Django-CRM/issues',
      icon: Bug,
      key: 'bug',
      newTab: true
    },
    {
      href: 'mailto:support@bottlecrm.io',
      icon: Mail,
      key: 'email',
      newTab: false
    }
  ];

  /**
   * The four facts a first reply always asks for. Browser and window come from
   * the client; the other two are things only the person writing can supply,
   * and they are phrased as prompts rather than pre-filled.
   */
  let browser = $state('—');
  let windowSize = $state('—');
  $effect(() => {
    if (data.available) return;
    const ua = navigator.userAgent;
    const m = ua.match(/(Firefox|Edg|Chrome|Safari)\/([\d.]+)/);
    browser = m
      ? `${m[1] === 'Edg' ? 'Edge' : m[1]} ${m[2].split('.')[0]}`
      : $_('help.home.unknown_browser');
    windowSize = `${window.innerWidth}×${window.innerHeight}`;
  });
</script>

<PageHeader title={$_('help.home.title')} center width="920px">
  {#snippet sub()}
    {$_('help.home.sub')}
  {/snippet}
  {#snippet actions()}
    {#if data.available}
      <a class="v2-btn v2-btn-primary" href={resolve('/help/new')}
        ><Plus />{$_('help.home.new_ticket')}</a
      >
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div
    class="v2-pad"
    style="padding-top:18px;padding-bottom:32px;max-width:920px;margin-inline:auto"
  >
    <div class="v2-label" style="margin-bottom:10px">{$_('help.home.section_start')}</div>
    <div class="cards">
      {#each SELF_SERVE as card (card.href)}
        <a class="v2-card card" href={resolve(asInternalPath(card.href))}>
          <card.icon size={17} />
          <div>
            <b>{$_(`help.home.card_${card.key}_title`)}</b>
            <p>{$_(`help.home.card_${card.key}_body`)}</p>
          </div>
        </a>
      {/each}
    </div>

    {#if data.available}
      <div class="v2-label" style="margin:26px 0 10px">{$_('help.home.section_tickets')}</div>
      {#if data.tickets.length === 0}
        <EmptyState title={$_('help.home.empty_title')} body={$_('help.home.empty_body')}>
          {#snippet icon()}<LifeBuoy size={21} />{/snippet}
          {#snippet actions()}
            <a class="v2-btn v2-btn-primary" href={resolve('/help/new')}
              >{$_('help.home.empty_action')}</a
            >
          {/snippet}
        </EmptyState>
      {:else}
        <div class="v2-table-wrap">
          <table class="v2-table">
            <thead>
              <tr>
                <th>{$_('help.home.col_ticket')}</th>
                <th>{$_('help.home.col_category')}</th>
                <th>{$_('help.home.col_status')}</th>
                <th>{$_('help.home.col_messages')}</th>
                <th class="v2-r">{$_('help.home.col_updated')}</th>
              </tr>
            </thead>
            <tbody>
              {#each data.tickets as ticket (ticket.id)}
                <tr>
                  <td data-m="title">
                    <a class="v2-row-link" href={resolve(`/help/${ticket.id}`)}>
                      <span class="v2-table-primary">{ticket.subject}</span>
                      <span class="v2-sub" style="display:block;font-size:11px;margin-top:2px"
                        >{ticket.reference}</span
                      >
                    </a>
                  </td>
                  <td class="v2-muted">{ticket.categoryLabel}</td>
                  <td data-m="tag"
                    ><Pill tone={STATUS_TONE[ticket.status]}>{ticket.statusLabel}</Pill></td
                  >
                  <td class="v2-num v2-muted" data-m="hide">{ticket.messageCount}</td>
                  <td class="v2-r v2-muted" data-m="meta">{relativeTime(ticket.lastActivityAt)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    {:else}
      <div class="v2-label" style="margin:26px 0 10px">{$_('help.home.section_contact')}</div>
      <div class="cards">
        {#each CONTACT as card (card.href)}
          <a
            class="v2-card card"
            href={card.href}
            rel={card.newTab ? 'noreferrer noopener' : undefined}
            target={card.newTab ? '_blank' : undefined}
          >
            <card.icon size={17} />
            <div>
              <b>
                {$_(`help.home.card_${card.key}_title`)}{#if card.newTab}<ArrowUpRight
                    size={12}
                    class="ext"
                  />{/if}
              </b>
              <p>{$_(`help.home.card_${card.key}_body`)}</p>
            </div>
          </a>
        {/each}
      </div>

      <div class="v2-label" style="margin:26px 0 10px">{$_('help.home.section_include')}</div>
      <div class="v2-card" style="padding:16px 18px">
        <p class="lead">
          {$_('help.home.include_lead')}
        </p>
        <dl class="facts">
          <dt>{$_('help.home.fact_browser')}</dt>
          <dd class="v2-num">{browser}</dd>
          <dt>{$_('help.home.fact_window')}</dt>
          <dd class="v2-num">{windowSize}</dd>
          <dt>{$_('help.home.fact_expected')}</dt>
          <dd>{$_('help.home.fact_expected_body')}</dd>
          <dt>{$_('help.home.fact_happened')}</dt>
          <dd>
            {$_('help.home.fact_happened_body')}
          </dd>
        </dl>
        <p class="fine">
          {$_('help.home.fine_print')}
        </p>
      </div>
    {/if}
  </div>
</div>

<style>
  .cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
  }
  .card {
    display: flex;
    gap: 11px;
    align-items: flex-start;
    padding: 15px 16px;
    color: inherit;
    text-decoration: none;
    transition: border-color 0.12s;
  }
  .card:hover {
    border-color: var(--v2-slate);
  }
  .card :global(svg) {
    flex: none;
    margin-top: 1px;
    color: var(--v2-slate);
  }
  .card b {
    display: flex;
    align-items: center;
    gap: 3px;
    font-size: 13.5px;
    font-weight: 600;
  }
  .card :global(.ext) {
    opacity: 0.5;
  }
  .card p {
    margin: 4px 0 0;
    font-size: 12px;
    color: var(--v2-slate);
    line-height: 1.5;
  }

  .lead {
    margin: 0 0 12px;
    font-size: 12.5px;
    color: var(--v2-slate);
  }
  .facts {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 8px 18px;
    margin: 0;
    font-size: 12.5px;
    line-height: 1.5;
  }
  .facts dt {
    color: var(--v2-slate);
    white-space: nowrap;
  }
  .facts dd {
    margin: 0;
  }
  .fine {
    margin: 14px 0 0;
    padding-top: 12px;
    border-top: 1px solid var(--v2-line);
    font-size: 11.5px;
    color: var(--v2-slate);
    line-height: 1.55;
  }
  @media (max-width: 768px) {
    .facts {
      grid-template-columns: 1fr;
      gap: 2px 0;
    }
    .facts dd {
      margin-bottom: 8px;
    }
  }
</style>
