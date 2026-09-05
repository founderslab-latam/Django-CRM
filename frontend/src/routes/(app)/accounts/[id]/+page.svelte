<script>
  import { resolve } from '$app/paths';
  /**
   * The account is a workspace, not a form.
   *
   * v1 rendered an account as ~28 stacked label/value rows, so answering
   * "what is going on with Northwind?" meant visiting four other pages. Here
   * the deals, people, tickets and invoices are on the page, and the next
   * action names the problem that spans them.
   *
   * All four panels come from the single detail response, the API already
   * returned them, so this costs no extra round trips.
   */
  import { _ } from '$lib/i18n/index.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import { money, shortDate, longDate } from '$lib/v2/format.js';
  import {
    STAGE_LABEL,
    PRIORITY_TONE,
    INVOICE_STATUS_TONE,
    invoiceStatusLabel
  } from '$lib/v2/enums.js';
  import { ChevronRight, Mail, Phone } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let { account, deals, contacts, tickets, invoices, owners } = $derived(data);

  let openDeals = $derived(deals.filter((/** @type {any} */ d) => !d.stage.startsWith('CLOSED_')));
  let stalled = $derived(openDeals.filter((/** @type {any} */ d) => d.aging_status === 'red'));
  // `past_due` is decided by the same rule as the header figure. See
  // `isPastDue` in the data layer. The invoice's own `is_overdue` flag counts
  // drafts, and a rail that disagrees with its header discredits both.
  let pastDue = $derived(invoices.filter((/** @type {any} */ i) => i.past_due));

  /** One sentence that connects problems across objects. Every clause is a
      fact on this page: a stalled deal, or an invoice past its due date. */
  let headline = $derived(
    stalled.length && pastDue.length
      ? $_('accounts.detail.headline_both', {
          values: { dealName: stalled[0].name, invoiceNumber: pastDue[0].invoice_number }
        })
      : stalled.length
        ? $_('accounts.detail.headline_stalled', {
            values: { dealName: stalled[0].name, days: stalled[0].days_in_current_stage }
          })
        : pastDue.length
          ? $_('accounts.detail.headline_pastdue', {
              values: {
                invoiceNumber: pastDue[0].invoice_number,
                amount: money(pastDue[0].amount_due, pastDue[0].currency)
              }
            })
          : null
  );
</script>

<PageHeader title={account.name} record>
  {#snippet crumb()}
    <a href={resolve('/accounts')}>{$_('accounts.detail.breadcrumb_accounts')}</a>
    <ChevronRight size={12} />
    <span>{account.industry || $_('accounts.detail.no_industry_fallback')}</span>
  {/snippet}
  {#snippet sub()}
    {[
      account.industry,
      account.number_of_employees
        ? $_('accounts.detail.staff_count', { values: { count: account.number_of_employees } })
        : null,
      /* Derived: the close date of the first deal won here. There is no
         contract model, so this is what "customer since" can honestly mean. */
      account.first_won_on
        ? `${$_('accounts.detail.customer_since_prefix')} ${longDate(account.first_won_on)}`
        : $_('accounts.detail.no_deals_won_yet_sub'),
      owners.length ? $_('accounts.detail.owned_by_prefix', { values: { name: owners[0] } }) : null
    ]
      .filter(Boolean)
      .join(' · ')}
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn" href={resolve(`/accounts/${account.id}/edit`)}
      >{$_('accounts.detail.edit_button')}</a
    >
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-bottom:32px">
    <div class="v2-stats" style="margin-bottom:16px">
      <StatCard
        label={$_('accounts.detail.stat_revenue_won')}
        value={account.won_amount ? money(account.won_amount, data.org.currency) : '—'}
        tone={account.won_amount ? 'moss' : 'slate'}
        detail={account.won_count
          ? $_('accounts.detail.deals_won_detail', { values: { count: account.won_count } })
          : $_('accounts.detail.nothing_won_yet')}
      />
      <StatCard
        label={$_('accounts.detail.stat_open_pipeline')}
        value={account.open_pipeline ? money(account.open_pipeline, data.org.currency) : '—'}
        detail={account.open_deal_count
          ? $_('accounts.detail.open_deals_detail', { values: { count: account.open_deal_count } })
          : $_('accounts.detail.no_open_deals')}
      />
      <StatCard
        label={$_('accounts.detail.stat_past_due')}
        value={account.overdue_amount ? money(account.overdue_amount, data.org.currency) : '—'}
        tone={account.overdue_amount ? 'rust' : 'slate'}
        detail={pastDue.length
          ? pastDue.map((/** @type {any} */ i) => i.invoice_number).join(', ')
          : $_('accounts.detail.nothing_past_due')}
      />
      <StatCard
        label={$_('accounts.detail.stat_open_tickets')}
        value={String(account.open_tickets ?? 0)}
        tone={tickets.some((/** @type {any} */ t) => t.priority === 'Urgent') ? 'rust' : 'slate'}
        detail={tickets.length
          ? `${tickets[0].name} · ${tickets[0].priority}`
          : $_('accounts.detail.none_open')}
      />
    </div>

    {#if headline}
      <div style="margin-bottom:16px">
        <!--
          The invoice half of this had an `href` it should not have had: it
          pointed at `/invoices/<uuid>` while invoices is still fixtures
          keyed by slugs, so the one button on the page labelled "the thing
          that needs you" answered 404. Found by following the page's own
          outbound links rather than by reading it.

          Without an `href` the action stays a button that does nothing, which
          is the same wrong answer more quietly, so when the target is not
          wired the action is dropped entirely and the sentence stands on its
          own. It comes back when invoices is.
        -->
        <NextAction
          label={$_('accounts.detail.next_action_label')}
          text={headline}
          action={stalled.length ? $_('accounts.detail.open_deal_action') : null}
          href={stalled.length ? `/pipeline/${stalled[0].id}` : null}
          tone="rust"
        />
      </div>
    {/if}

    <!-- align-items:start so each card is its own height. Stretched to match
         its neighbour, a one-row panel ends in a tall blank area that reads as
         content that failed to load. -->
    <div
      style="display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start"
      class="v2-account-grid"
    >
      <!-- Deals -->
      <section class="v2-card" style="overflow:hidden">
        <div class="v2-card-head">
          <span class="v2-label">{$_('accounts.detail.section_deals')}</span>
          <a href={resolve('/pipeline')}>{$_('accounts.detail.view_all')}</a>
        </div>
        {#each deals as d (d.id)}
          <a
            href={resolve(`/pipeline/${d.id}`)}
            style="display:flex;gap:12px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--v2-line-soft);color:inherit;text-decoration:none"
          >
            <div style="flex:1;min-width:0">
              <div style="font-weight:550;font-size:13px">{d.name}</div>
              <!-- `closed_on` is labelled "Expected Close Date" on the model
                   and means two different things depending on the stage. Bare,
                   it reads as though an open deal already closed. -->
              <div class="v2-sub" style="font-size:11.5px">
                {STAGE_LABEL[d.stage]}{d.closed_on
                  ? d.stage.startsWith('CLOSED_')
                    ? ` · ${$_('accounts.detail.deal_closed_prefix')} ${shortDate(d.closed_on)}`
                    : ` · ${$_('accounts.detail.deal_due_prefix')} ${shortDate(d.closed_on)}`
                  : ''}
              </div>
            </div>
            {#if d.aging_status === 'red' && !d.stage.startsWith('CLOSED_')}
              <Pill tone="rust">{d.days_in_current_stage}d</Pill>
            {/if}
            <span class="v2-num" style="font-weight:600;font-size:13px"
              >{money(d.amount, d.currency)}</span
            >
          </a>
        {:else}
          <p class="v2-sub" style="padding:14px 15px;font-size:12.5px">
            {$_('accounts.detail.no_deals_yet')}
          </p>
        {/each}
      </section>

      <!-- People -->
      <section class="v2-card" style="overflow:hidden">
        <div class="v2-card-head">
          <span class="v2-label">{$_('accounts.detail.section_people')}</span>
          <a href={resolve('/contacts')}>{$_('accounts.detail.view_all')}</a>
        </div>
        {#each contacts as c (c.id)}
          <div
            style="display:flex;gap:11px;align-items:center;padding:10px 15px;border-bottom:1px solid var(--v2-line-soft)"
          >
            <Avatar name="{c.first_name} {c.last_name}" size={29} />
            <!-- A link now. This was deliberately dead text while
                 `/contacts/<uuid>` answered 404, which is the reason
                 contacts was the module to wire next. -->
            <a
              href={resolve(`/contacts/${c.id}`)}
              style="flex:1;min-width:0;color:inherit;text-decoration:none"
            >
              <div style="font-weight:550;font-size:13px">{c.first_name} {c.last_name}</div>
              <!-- title and department. The mock showed a "relationship"
                   (Champion / Blocker); Contact has no such field. -->
              <div class="v2-sub" style="font-size:11.5px">
                {[c.title, c.department].filter(Boolean).join(' · ') ||
                  $_('accounts.detail.no_title_recorded')}
              </div>
            </a>
            {#if c.email}
              <a
                class="v2-btn v2-btn-sm"
                href="mailto:{c.email}"
                aria-label={$_('accounts.detail.email_aria_label', {
                  values: { name: c.first_name }
                })}
              >
                <Mail size={13} />
              </a>
            {/if}
            {#if c.phone && !c.do_not_call}
              <a
                class="v2-btn v2-btn-sm"
                href="tel:{c.phone}"
                aria-label={$_('accounts.detail.call_aria_label', {
                  values: { name: c.first_name }
                })}
              >
                <Phone size={13} />
              </a>
            {/if}
          </div>
        {:else}
          <p class="v2-sub" style="padding:14px 15px;font-size:12.5px">
            {$_('accounts.detail.people_empty_prefix')}
            <a href={resolve(`/contacts/new?account=${account.id}`)}
              >{$_('accounts.detail.people_empty_link')}</a
            >
            {$_('accounts.detail.people_empty_suffix')}
          </p>
        {/each}
      </section>

      <!-- Tickets -->
      <section class="v2-card" style="overflow:hidden">
        <div class="v2-card-head">
          <span class="v2-label">{$_('accounts.detail.section_tickets')}</span>
          <a href={resolve('/tickets')}>{$_('accounts.detail.view_all')}</a>
        </div>
        {#each tickets as t (t.id)}
          <!-- A link again: tickets is wired, so a real id sent to
               `/tickets/<uuid>` opens the ticket. -->
          <a
            href={resolve(`/tickets/${t.id}`)}
            style="display:flex;gap:12px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--v2-line-soft);color:inherit;text-decoration:none"
          >
            <span style="flex:1;font-size:13px;min-width:0">{t.name}</span>
            <span class="v2-sub" style="font-size:11.5px">{t.status}</span>
            <Pill tone={PRIORITY_TONE[t.priority]}>{t.priority}</Pill>
          </a>
        {:else}
          <p class="v2-sub" style="padding:14px 15px;font-size:12.5px">
            {$_('accounts.detail.tickets_empty_prefix')}
            <a href={resolve(`/tickets/new?account=${account.id}`)}
              >{$_('accounts.detail.tickets_empty_link')}</a
            >
            {$_('accounts.detail.tickets_empty_suffix')}
          </p>
        {/each}
      </section>

      <!-- Invoices -->
      <section class="v2-card" style="overflow:hidden">
        <div class="v2-card-head">
          <span class="v2-label">{$_('accounts.detail.section_invoices')}</span>
          <a href={resolve('/invoices')}>{$_('accounts.detail.view_all')}</a>
        </div>
        {#each invoices as inv (inv.id)}
          <!-- A link now: invoices is wired, so a real id sent to
               `/invoices/<uuid>` opens the invoice. -->
          <a
            href={resolve(`/invoices/${inv.id}`)}
            style="display:flex;gap:12px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--v2-line-soft);color:inherit;text-decoration:none"
          >
            <span class="v2-num" style="font-size:12.5px">{inv.invoice_number}</span>
            <Pill tone={inv.past_due ? 'rust' : INVOICE_STATUS_TONE[inv.status]}>
              {inv.past_due
                ? $_('accounts.detail.invoice_past_due_label')
                : invoiceStatusLabel(inv.status)}
            </Pill>
            <span class="v2-num" style="margin-left:auto;font-weight:600;font-size:13px">
              {money(inv.past_due ? inv.amount_due : inv.total_amount, inv.currency)}
            </span>
          </a>
        {:else}
          <p class="v2-sub" style="padding:14px 15px;font-size:12.5px">
            {$_('accounts.detail.nothing_billed_yet')}
          </p>
        {/each}
      </section>
    </div>
  </div>
</div>

<style>
  @media (max-width: 1080px) {
    .v2-account-grid {
      grid-template-columns: 1fr !important;
    }
  }
</style>
