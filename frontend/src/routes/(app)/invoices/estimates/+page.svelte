<script>
  import { resolve } from '$app/paths';
  /**
   * Estimates, sorted so the one thing worth doing is at the top.
   *
   * Accepted-and-not-converted is money the customer has already agreed to and
   * nobody has billed. v1 gave it the same green "Accepted" pill as an
   * estimate that had become an invoice weeks ago, so the two were
   * indistinguishable and the gap only surfaced at month end. Status and
   * "has it been billed" are two separate facts and get two separate columns.
   */
  import { page } from '$app/state';
  import { _ } from '$lib/i18n/index.js';
  import { estimateStatusKey } from '$lib/invoices/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SectionTabs from '$lib/v2/components/SectionTabs.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import FilterBar from '$lib/v2/components/FilterBar.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { enhance } from '$app/forms';
  import { money, count, daysSince } from '$lib/v2/format.js';
  import { ESTIMATE_STATUS_TONE } from '$lib/v2/enums.js';
  import { Plus, FileText } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let totals = $derived(data.totals);

  /** Only an estimate that can still be accepted has a meaningful validity. */
  const LIVE = ['Sent', 'Viewed'];

  function validity(e) {
    if (!e.valid_until) return null;
    if (!LIVE.includes(e.status)) return null;
    const n = daysSince(e.valid_until);
    if (n > 0)
      return {
        text: $_('invoices.estimates.validity_expired', { values: { count: n } }),
        urgent: true
      };
    if (n === 0) return { text: $_('invoices.estimates.validity_today'), urgent: true };
    return {
      text: $_('invoices.estimates.validity_left', { values: { count: Math.abs(n) } }),
      urgent: Math.abs(n) <= 7
    };
  }

  const needsBilling = (e) => e.status === 'Accepted' && !e.converted_invoice;
</script>

<PageHeader title={$_('invoices.estimates.title')}>
  {#snippet sub()}
    <span class="v2-num">{count(totals.count)}</span>
    {$_('invoices.estimates.sub_estimates', { values: { count: totals.count } })} ·
    <span class="v2-num">{money(totals.awaiting_reply, data.org.currency)}</span>
    {$_('invoices.estimates.sub_awaiting')}
  {/snippet}
  {#snippet actions()}
    <!-- An estimate is raised from a deal, not typed from scratch here. The
         empty state has always said so. Send the button where estimates are
         born rather than to a form this page does not own. -->
    <a class="v2-btn v2-btn-primary" href={resolve('/pipeline')}
      ><Plus />{$_('invoices.estimates.new_button')}</a
    >
  {/snippet}
</PageHeader>

{#if page.url.search}
  <p class="v2-sub" style="font-size:11.5px;margin:8px 0 0">
    {$_('invoices.estimates.filtered_notice')}
  </p>
{/if}

<SectionTabs set="invoices" />

{#if form?.error}
  <div class="v2-pad" style="padding-top:12px;flex:none">
    <p class="est-error" role="alert">{form.error}</p>
  </div>
{/if}

<div class="v2-pad" style="padding-top:16px;flex:none">
  <div class="v2-stats">
    <StatCard
      label={$_('invoices.estimates.stat_accepted_label')}
      value={money(totals.accepted_unconverted, data.org.currency)}
      tone="clay"
      detail={$_('invoices.estimates.stat_accepted_detail')}
    />
    <StatCard
      label={$_('invoices.estimates.stat_awaiting_label')}
      value={money(totals.awaiting_reply, data.org.currency)}
      tone="ink"
    />
    <StatCard
      label={$_('invoices.estimates.stat_expiring_label')}
      value={count(totals.expiring_within_7d)}
      tone={totals.expiring_within_7d ? 'clay' : 'slate'}
    />
    <StatCard
      label={$_('invoices.estimates.stat_count_label')}
      value={count(totals.count)}
      tone="slate"
    />
  </div>
</div>

<FilterBar
  page="estimates"
  url={page.url}
  accounts={data.accounts}
  meta={$_('invoices.estimates.filter_meta')}
/>

<div class="v2-scroll">
  {#if data.estimates.length === 0}
    <EmptyState
      title={$_('invoices.estimates.empty_title')}
      body={$_('invoices.estimates.empty_body')}
    >
      {#snippet icon()}<FileText size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/pipeline')}
          >{$_('invoices.estimates.empty_button')}</a
        >
      {/snippet}
    </EmptyState>
  {:else}
    <div class="v2-table-wrap">
      <table class="v2-table">
        <thead>
          <tr>
            <th>{$_('invoices.estimates.col_estimate')}</th>
            <th>{$_('invoices.estimates.col_account')}</th>
            <th>{$_('invoices.estimates.col_status')}</th>
            <th>{$_('invoices.estimates.col_billed')}</th>
            <th class="v2-r">{$_('invoices.estimates.col_amount')}</th>
            <th class="v2-r">{$_('invoices.estimates.col_valid')}</th>
          </tr>
        </thead>
        <tbody>
          {#each data.estimates as e (e.id)}
            {@const v = validity(e)}
            <tr>
              <td>
                <span class="v2-table-primary">{e.title}</span>
                <span class="v2-table-secondary" style="display:block">
                  <span class="v2-num">{e.estimate_number}</span> · {e.contact}
                </span>
              </td>
              <td>
                <a href={resolve(`/accounts/${e.account.id}`)} style="color:inherit"
                  >{e.account.name}</a
                >
                {#if e.opportunity}
                  <span class="v2-table-secondary" style="display:block">{e.opportunity.name}</span>
                {/if}
              </td>
              <td
                ><Pill tone={ESTIMATE_STATUS_TONE[e.status]}>{$_(estimateStatusKey(e.status))}</Pill
                ></td
              >
              <td>
                {#if e.converted_invoice}
                  <a
                    href={resolve(`/invoices/${e.converted_invoice.id}`)}
                    class="v2-num"
                    style="color:inherit"
                  >
                    {e.converted_invoice.invoice_number}
                  </a>
                {:else if needsBilling(e)}
                  <!-- The one place ember belongs on this page: an accepted
                       estimate is the only row with an action nobody has taken.
                       Convert copies it to a Draft invoice and opens that. -->
                  <form method="POST" action="?/convert" use:enhance>
                    <input type="hidden" name="id" value={e.id} />
                    <button class="v2-btn v2-btn-sm v2-btn-primary" type="submit">
                      {$_('invoices.estimates.raise_invoice')}
                    </button>
                  </form>
                {:else}
                  <span class="v2-muted">—</span>
                {/if}
              </td>
              <td class="v2-r v2-num" style="font-weight:600"
                >{money(e.total_amount, e.currency)}</td
              >
              <td class="v2-r" style={v?.urgent ? 'color:var(--v2-rust);font-weight:600' : ''}>
                {#if v}
                  {v.text}
                {:else}
                  <span class="v2-muted">—</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="v2-sub v2-pad" style="font-size:12px;padding-bottom:24px">
      {$_('invoices.estimates.showing_prefix')}
      <span class="v2-num">{data.estimates.length}</span>
      {$_('invoices.estimates.of_connector')}
      <span class="v2-num">{count(totals.count)}</span>
    </p>
  {/if}
</div>

<style>
  .est-error {
    margin: 0;
    padding: 8px 12px;
    border: 1px solid color-mix(in srgb, var(--v2-rust) 40%, transparent);
    border-radius: 6px;
    background: color-mix(in srgb, var(--v2-rust) 8%, transparent);
    color: var(--v2-rust);
    font-size: 13px;
  }
</style>
