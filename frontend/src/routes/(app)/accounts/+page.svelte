<script>
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { _ } from '$lib/i18n/index.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import FilterBar from '$lib/v2/components/FilterBar.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { money, count } from '$lib/v2/format.js';
  import { activeChips, activePresetKey } from '$lib/v2/filters.js';
  import { Plus, Building2 } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let accounts = $derived(data.accounts);
  let totals = $derived(data.totals);

  /**
   * Whether the view is actually narrowed, rather than merely carrying a query
   * string. `page.url.search` alone is the wrong test: it fires on any param,
   * including ones that are not filters at all. `'all'` is this page's
   * empty-params preset, its declared default, so any other preset counts as
   * filtered even when it sets no field a chip would show.
   */
  let isFiltered = $derived(
    activeChips('accounts', page.url, { people: data.people, tags: data.tags }).length > 0 ||
      activePresetKey('accounts', page.url, data.meId) !== 'all'
  );
</script>

<PageHeader title={$_('accounts.list.title')}>
  {#snippet sub()}
    <!-- The count is the size of the whole result set, not of this page. -->
    <span class="v2-num">{count(totals.count)}</span>
    {$_('accounts.list.count_suffix', { values: { count: totals.count } })}
    <!-- `customers` is counted from the rows actually loaded, because the
         accounts endpoint returns no aggregate for it (see the note in
         `lib/server/v2/accounts.js`). Printing it beside a whole-set count
         when only one page is loaded states a smaller number as though it
         covered everything, so it is shown only when this page IS the whole
         set. A figure that disappears beats a figure that is wrong. -->
    {#if (totals.shown ?? 0) >= (totals.count ?? 0)}
      · <span class="v2-num">{count(totals.customers)}</span>
      {$_('accounts.list.with_deal_won_suffix')}
    {/if}
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn v2-btn-primary" href={resolve('/accounts/new')}
      ><Plus />{$_('accounts.list.new_account_button')}</a
    >
  {/snippet}
</PageHeader>

{#if isFiltered}
  <p class="v2-sub" style="font-size:11.5px;margin:8px 0 0">
    {$_('accounts.list.filtered_notice')}
  </p>
{/if}

<FilterBar
  page="accounts"
  url={page.url}
  people={data.people}
  tags={data.tags}
  meId={data.meId}
  meta={$_('accounts.list.sorted_by_revenue')}
/>

<div class="v2-scroll">
  {#if accounts.length === 0}
    <EmptyState title={$_('accounts.list.empty_title')} body={$_('accounts.list.empty_body')}>
      {#snippet icon()}<Building2 size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/accounts/new')}
          >{$_('accounts.list.new_account_button')}</a
        >
        <a class="v2-btn" href={resolve('/leads')}>{$_('accounts.list.go_to_leads_button')}</a>
      {/snippet}
    </EmptyState>
  {:else}
    <div class="v2-table-wrap">
      <table class="v2-table">
        <thead>
          <tr>
            <th>{$_('accounts.list.col_account')}</th>
            <th>{$_('accounts.list.col_industry')}</th>
            <th class="v2-r">{$_('accounts.list.col_won')}</th>
            <th class="v2-r">{$_('accounts.list.col_open_pipeline')}</th>
            <th class="v2-r">{$_('accounts.list.col_past_due')}</th>
            <th>{$_('accounts.list.col_tickets')}</th>
          </tr>
        </thead>
        <tbody>
          {#each accounts as a (a.id)}
            <tr>
              <td>
                <a class="v2-row-link" href={resolve(`/accounts/${a.id}`)}>
                  <div class="v2-table-primary">{a.name}</div>
                  <div class="v2-table-secondary">
                    {[a.city, a.country_display].filter(Boolean).join(', ') ||
                      $_('accounts.list.no_address')}
                  </div>
                </a>
              </td>
              <td class="v2-muted" data-m="hide" style="font-size:12.5px">
                {a.industry || '—'}
              </td>
              <!-- All four figures are annotated in SQL by the API over the
                   whole related set, never derived from the rows on screen. -->
              <td class="v2-r v2-num" data-m="hide">
                {a.won_amount ? money(a.won_amount, data.org.currency) : '—'}
              </td>
              <!-- Labelled on a phone: without the header row, two money
                   columns side by side are two unattributed numbers. -->
              <td class="v2-r v2-num" data-l={$_('accounts.list.mobile_label_pipeline')}>
                {a.open_pipeline ? money(a.open_pipeline, data.org.currency) : '—'}
              </td>
              <td
                class="v2-r v2-num"
                data-l={$_('accounts.list.col_past_due')}
                style={a.overdue_amount ? 'color:var(--v2-rust);font-weight:600' : ''}
              >
                {a.overdue_amount ? money(a.overdue_amount, data.org.currency) : '—'}
              </td>
              <td>
                {#if a.open_tickets}
                  <Pill tone="slate"
                    >{$_('accounts.list.tickets_open_count', {
                      values: { count: a.open_tickets }
                    })}</Pill
                  >
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
      {#if totals.shown < totals.count}
        {$_('accounts.list.showing_partial_prefix')} <span class="v2-num">{totals.shown}</span>
        {$_('accounts.list.of_connector')}
        <span class="v2-num">{count(totals.count)}</span>
      {:else}
        {$_('accounts.list.showing_all_prefix')}
        <span class="v2-num">{count(totals.count)}</span>
      {/if}
      {#if totals.inactive}
        · <span class="v2-num">{totals.inactive}</span>
        {$_('accounts.list.inactive_not_shown', { values: { count: totals.inactive } })}
      {/if}
    </p>
  {/if}
</div>
