<script>
  /**
   * Where the time went: totals by agent, ticket or account over a window.
   *
   * The timesheet answers "what did I do this week". This answers the two
   * questions asked of that data afterwards, which are somebody else's: how
   * much of the month went to this account, and what of it can be billed.
   *
   * The filter bar is a plain GET form, so the report is a URL. That is what
   * makes it shareable, reloadable, and what lets the CSV link be the same
   * query string pointed at the export proxy. No JavaScript is needed for any
   * of it.
   */
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import { money, count, shortDate, hoursMinutes as hm } from '$lib/v2/format.js';
  import { _ } from '$lib/i18n/index.js';
  import { Download } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let report = $derived(data.report);
  let filters = $derived(data.filters);

  const GROUP_VALUES = ['agent', 'ticket', 'account'];

  /** The catalog key for a group's noun, said once above the table not per row. */
  const groupNoun = (/** @type {string} */ value) => $_(`timesheet.report.group.${value}`);

  let billableShare = $derived(
    report.totals.total_minutes
      ? Math.round((report.totals.billable_minutes / report.totals.total_minutes) * 100)
      : 0
  );

  /**
   * The window and filters as a query string, for the CSV link.
   *
   * Built from what the API reported on, not from the form's current state:
   * the link has to export the table being looked at, and an unsubmitted
   * change to a date input has not reached the table yet.
   */
  let exportQuery = $derived.by(() => {
    const qs = new URLSearchParams({
      start: report.start,
      end: report.end,
      group_by: report.group_by
    });
    if (filters.billable === 'true' || filters.billable === 'false') {
      qs.set('billable', filters.billable);
    }
    return qs.toString();
  });

  /** Currency for the value column. One symbol cannot label a mixed sum. */
  let currency = $derived(
    report.currencies?.length === 1 ? report.currencies[0] : data.org.currency
  );
</script>

<PageHeader title={$_('timesheet.report.title')}>
  {#snippet crumb()}
    <a href={resolve('/timesheet')}>{$_('timesheet.report.crumb')}</a>
  {/snippet}
  {#snippet sub()}
    {shortDate(report.start)} - {shortDate(report.end)} · {$_('timesheet.report.sub_by', {
      values: { group: groupNoun(report.group_by).toLowerCase() }
    })}
  {/snippet}
  {#snippet actions()}
    <!-- An anchor, not a fetch: the browser's own download, and the proxy
         behind it adds the token the httpOnly cookie will not hand over. -->
    <a
      class="v2-btn export"
      href="/api/time-entries/report/export/?{exportQuery}"
      data-sveltekit-reload
    >
      <Download size={12} />{$_('timesheet.report.export_csv')}
    </a>
  {/snippet}
</PageHeader>

<div class="v2-pad" style="padding-top:16px;flex:none">
  <form method="GET" class="filters">
    <div class="v2-field">
      <label for="r-start">{$_('timesheet.report.field_from')}</label>
      <input id="r-start" class="v2-input" type="date" name="start" value={report.start} />
    </div>
    <div class="v2-field">
      <label for="r-end">{$_('timesheet.report.field_to')}</label>
      <input id="r-end" class="v2-input" type="date" name="end" value={report.end} />
    </div>
    <div class="v2-field">
      <label for="r-group">{$_('timesheet.report.field_group_by')}</label>
      <select id="r-group" class="v2-input" name="group_by" value={report.group_by}>
        {#each GROUP_VALUES as value (value)}
          <option {value}>{groupNoun(value)}</option>
        {/each}
      </select>
    </div>
    <div class="v2-field">
      <label for="r-billable">{$_('timesheet.report.field_show')}</label>
      <select id="r-billable" class="v2-input" name="billable" value={filters.billable ?? ''}>
        <option value="">{$_('timesheet.report.show_all')}</option>
        <option value="true">{$_('timesheet.report.show_billable')}</option>
        <option value="false">{$_('timesheet.report.show_nonbillable')}</option>
      </select>
    </div>
    <button class="v2-btn v2-btn-primary filters-go">{$_('timesheet.report.apply')}</button>
  </form>

  <div class="v2-stats" style="margin-top:14px">
    <StatCard
      label={$_('timesheet.report.stat_logged')}
      value={hm(report.totals.total_minutes)}
      tone="ink"
    />
    <StatCard
      label={$_('timesheet.report.stat_billable')}
      value={hm(report.totals.billable_minutes)}
      tone="moss"
      detail={$_('timesheet.report.stat_billable_detail', { values: { percent: billableShare } })}
    />
    <StatCard
      label={$_('timesheet.report.stat_value')}
      value={money(report.totals.billable_value, currency)}
      tone="slate"
      detail={report.currencies?.length > 1
        ? $_('timesheet.report.stat_value_mixed', {
            values: { list: report.currencies.join(', ') }
          })
        : $_('timesheet.report.stat_value_detail')}
    />
    <StatCard
      label={$_('timesheet.report.stat_entries')}
      value={count(report.totals.entry_count)}
      tone="slate"
    />
  </div>
</div>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-bottom:32px">
    {#if report.rows.length === 0}
      <p class="v2-sub" style="font-size:12.5px">
        {$_('timesheet.report.empty')}
      </p>
    {:else}
      <div class="v2-table-wrap">
        <table class="v2-table">
          <thead>
            <tr>
              <th>{groupNoun(report.group_by)}</th>
              <th class="v2-r">{$_('timesheet.report.col_entries')}</th>
              <th class="v2-r">{$_('timesheet.report.col_billable')}</th>
              <th class="v2-r">{$_('timesheet.report.col_value')}</th>
              <th class="v2-r">{$_('timesheet.report.col_logged')}</th>
            </tr>
          </thead>
          <tbody>
            {#each report.rows as row (row.key ?? row.name)}
              <tr>
                <td data-m="title">
                  {#if report.group_by === 'ticket' && row.key}
                    <a href={resolve(`/tickets/${row.key}`)} class="v2-table-primary">{row.name}</a>
                  {:else if report.group_by === 'account' && row.key}
                    <a href={resolve(`/accounts/${row.key}`)} class="v2-table-primary">{row.name}</a
                    >
                  {:else}
                    {row.name}
                  {/if}
                </td>
                <td class="v2-num v2-r" data-m="meta" data-l="entries">{count(row.entry_count)}</td>
                <td class="v2-num v2-r" data-m="meta" data-l="billable">
                  {hm(row.billable_minutes)}
                </td>
                <td class="v2-num v2-r" data-m="meta" data-l="worth">
                  {money(row.billable_value, currency)}
                </td>
                <td class="v2-num v2-r" data-m="tag">{hm(row.total_minutes)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

<style>
  .filters {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    flex-wrap: wrap;
  }
  .filters .v2-field {
    margin-bottom: 0;
    flex: 1 1 150px;
  }
  .filters-go {
    height: 36px;
  }

  @media (max-width: 768px) {
    /* Two fields a row on a phone: four full-width inputs stacked would put
       Apply below the fold on every load. The dates pair, the pickers pair. */
    .filters .v2-field {
      flex: 1 1 calc(50% - 5px);
    }
    .filters-go {
      flex: 1 0 100%;
      min-height: 44px;
    }
    /* Thumb-sized. The shared control is 40px, which is fine under a mouse
       and short of the 44px this app holds phone targets to. */
    .filters :global(.v2-input),
    .export {
      min-height: 44px;
    }
  }
</style>
