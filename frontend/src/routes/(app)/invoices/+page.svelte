<script>
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { _ } from '$lib/i18n/index.js';
  import { invoiceStatusKey } from '$lib/invoices/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SectionTabs from '$lib/v2/components/SectionTabs.svelte';
  import FilterBar from '$lib/v2/components/FilterBar.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { money, count, shortDate, daysSince } from '$lib/v2/format.js';
  import { INVOICE_STATUS_TONE } from '$lib/v2/enums.js';
  import { enhance } from '$app/forms';
  import { Plus, Receipt } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let invoices = $derived(data.invoices);
  let totals = $derived(data.totals);

  /** Rows with a send in flight, so the button can show it is working. */
  let sending = $state(/** @type {Record<string, boolean>} */ ({}));

  /**
   * Days past due, or days remaining. A settled invoice has no age, once it
   * is Paid or Cancelled the due date stops meaning anything, and showing
   * "4d late" against a paid invoice is just wrong.
   */
  const SETTLED = ['Paid', 'Cancelled'];

  function ageLabel(inv) {
    if (SETTLED.includes(inv.status)) return '—';
    if (!inv.due_date) return '—';
    const n = daysSince(inv.due_date);
    if (n > 0) return $_('invoices.list.age_late', { values: { count: n } });
    if (n === 0) return $_('invoices.list.age_due_today');
    return $_('invoices.list.age_left', { values: { count: Math.abs(n) } });
  }

  const isLate = (inv) =>
    !SETTLED.includes(inv.status) && inv.due_date && daysSince(inv.due_date) > 0;
</script>

<PageHeader title={$_('invoices.list.title')}>
  {#snippet sub()}
    <!--
      These aggregates come from the API over the whole result set. v1 summed
      the loaded page, so a 50-row list showed pills adding up to 10.
    -->
    <span class="v2-num">{count(totals.count)}</span>
    {$_('invoices.list.sub_invoices', { values: { count: totals.count } })} ·
    <span class="v2-num">{money(totals.outstanding, data.org.currency)}</span>
    {$_('invoices.list.sub_outstanding')}
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn v2-btn-primary" href={resolve('/invoices/new')}
      ><Plus />{$_('invoices.list.new_button')}</a
    >
  {/snippet}
</PageHeader>

<!-- Estimates and Recurring were buttons in this header that went nowhere,
     while /invoices/estimates existed in v1 and was reachable only from a
     dropdown elsewhere. They are sibling pages; a tab strip says so. -->
<SectionTabs set="invoices" />

<div class="v2-pad" style="padding-top:16px;flex:none">
  <div class="v2-stats">
    <StatCard
      label={$_('invoices.list.stat_overdue_label')}
      value={money(totals.overdue, data.org.currency)}
      tone="rust"
      detail={$_('invoices.list.stat_overdue_detail')}
    />
    <StatCard
      label={$_('invoices.list.stat_due_month_label')}
      value={money(totals.due_this_month, data.org.currency)}
      tone="clay"
    />
    <StatCard
      label={$_('invoices.list.stat_paid_quarter_label')}
      value={money(totals.paid_this_quarter, data.org.currency)}
      tone="moss"
    />
    <StatCard
      label={$_('invoices.list.stat_draft_label')}
      value={money(totals.draft, data.org.currency)}
      tone="slate"
      detail={$_('invoices.list.stat_draft_detail')}
    />
  </div>
</div>

<!-- No "filtered list" line here, unlike the other v2 list pages: the pills
     above come from `totals`, which the API deliberately computes over the
     whole role-scoped queryset regardless of the active filter (see the note
     on `listInvoices` in `$lib/server/v2/invoices.js`). Saying "these numbers
     describe the filtered list" would be false for this page. -->
<FilterBar
  page="invoices"
  url={page.url}
  people={data.people}
  accounts={data.accounts}
  meId={data.meId}
  meta={$_('invoices.list.filter_meta')}
/>

{#if form?.error}
  <p class="v2-sub v2-pad" style="color:var(--v2-rust);font-size:12.5px;padding-top:10px">
    {form.error}
  </p>
{/if}

<div class="v2-scroll">
  {#if invoices.length === 0}
    <EmptyState title={$_('invoices.list.empty_title')} body={$_('invoices.list.empty_body')}>
      {#snippet icon()}<Receipt size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/invoices/new')}
          >{$_('invoices.list.new_button')}</a
        >
        <a class="v2-btn" href={resolve('/pipeline')}>{$_('invoices.list.empty_pipeline_button')}</a
        >
      {/snippet}
    </EmptyState>
  {:else}
    <div class="v2-table-wrap">
      <table class="v2-table">
        <thead>
          <tr>
            <th>{$_('invoices.list.col_invoice')}</th>
            <th>{$_('invoices.list.col_account')}</th>
            <th>{$_('invoices.list.col_status')}</th>
            <th class="v2-r">{$_('invoices.list.col_amount')}</th>
            <th>{$_('invoices.list.col_due')}</th>
            <th class="v2-r">{$_('invoices.list.col_age')}</th>
            <th style="width:130px"></th>
          </tr>
        </thead>
        <tbody>
          {#each invoices as inv (inv.id)}
            {@const late = isLate(inv)}
            <tr>
              <td>
                <a class="v2-row-link" href={resolve(`/invoices/${inv.id}`)}>
                  <span class="v2-table-primary v2-num" style="font-size:13px"
                    >{inv.invoice_number}</span
                  >
                </a>
              </td>
              <td>{inv.account.name}</td>
              <td>
                <Pill tone={INVOICE_STATUS_TONE[inv.status]}
                  >{$_(invoiceStatusKey(inv.status))}</Pill
                >
              </td>
              <td class="v2-r v2-num" style="font-weight:600"
                >{money(inv.total_amount, inv.currency)}</td
              >
              <td>{shortDate(inv.due_date)}</td>
              <td
                class="v2-r v2-num"
                class:v2-muted={!late}
                style={late ? 'color:var(--v2-rust);font-weight:600' : ''}
              >
                {ageLabel(inv)}
              </td>
              <td>
                {#if inv.status === 'Overdue' || inv.status === 'Draft'}
                  <form
                    method="POST"
                    action="?/send"
                    use:enhance={() => {
                      sending[inv.id] = true;
                      return async ({ update }) => {
                        await update();
                        sending[inv.id] = false;
                      };
                    }}
                  >
                    <input type="hidden" name="id" value={inv.id} />
                    <button class="v2-btn v2-btn-sm" disabled={sending[inv.id]}>
                      {#if sending[inv.id]}{$_(
                          'invoices.list.sending'
                        )}{:else if inv.status === 'Overdue'}{$_(
                          'invoices.list.send_reminder'
                        )}{:else}{$_('invoices.list.send')}{/if}
                    </button>
                  </form>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="v2-sub v2-pad" style="font-size:12px;padding-bottom:24px">
      {$_('invoices.list.showing_prefix')} <span class="v2-num">{invoices.length}</span>
      {$_('invoices.list.of_connector')}
      <span class="v2-num">{count(totals.count)}</span>
    </p>
  {/if}
</div>
