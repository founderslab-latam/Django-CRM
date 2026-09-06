<script>
  import { SvelteURLSearchParams } from 'svelte/reactivity';
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  import { page } from '$app/state';
  import { _ } from '$lib/i18n/index.js';
  import { opportunityStageKey } from '$lib/opportunity/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import FilterBar from '$lib/v2/components/FilterBar.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import StageMeter from '$lib/v2/components/StageMeter.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { money, count, shortDate } from '$lib/v2/format.js';
  import { AGING_TONE } from '$lib/v2/enums.js';
  import { agingKey } from '$lib/common/enums-labels.js';
  import { activeChips, activePresetKey, withoutParam } from '$lib/v2/filters.js';
  import { Columns3, List, Plus, TriangleAlert } from '@lucide/svelte';
  import { flip } from 'svelte/animate';
  import { dndzone } from 'svelte-dnd-action';
  import { invalidateAll } from '$app/navigation';
  import { deserialize } from '$app/forms';

  /** @type {{ data: any }} */
  let { data } = $props();

  const FLIP_MS = 160;

  let deals = $derived(data.deals);
  let totals = $derived(data.totals);
  let view = $derived(data.view);

  /* Lanes are built server-side from `/opportunities/kanban/`, which returns
     every stage with its true count. They used to be grouped on the client
     from whatever the list happened to return: correct only until the first
     page boundary, and wrong in the way that looks right: all the columns
     render, each is just short. */
  let lanes = $derived(data.lanes);

  /* `dndzone` reorders the array it is handed, so the board renders from a
     local copy. Rebuilt whenever the server sends new lanes, which is what
     makes a rejected move snap back: the action calls `invalidateAll()` and
     this effect overwrites the optimistic arrangement with the stored one. */
  let boardLanes = $state(/** @type {any[]} */ ([]));
  $effect(() => {
    boardLanes = lanes.map((/** @type {any} */ lane) => ({ ...lane, rows: [...lane.rows] }));
  });

  let moveError = $state('');

  /* The header has to describe the cards under it after an optimistic move,
     not the count the server sent before it. A capped lane keeps the server's
     total, since its own rows are not the whole story either way. */
  function laneCount(/** @type {any} */ lane) {
    return lane.truncated ? lane.count : lane.rows.length;
  }
  function laneSum(/** @type {any} */ lane) {
    return lane.rows.reduce(
      (/** @type {number} */ total, /** @type {any} */ r) => total + r.amount,
      0
    );
  }

  function onConsider(/** @type {any} */ lane, /** @type {any} */ e) {
    lane.rows = e.detail.items;
  }

  async function onFinalize(/** @type {any} */ lane, /** @type {any} */ e) {
    lane.rows = e.detail.items;
    const movedId = e.detail.info?.id;
    const index = e.detail.items.findIndex((/** @type {any} */ r) => r.id === movedId);
    // Finalize fires on both lanes of a cross-lane move. Only the lane now
    // holding the card knows where it landed, so only that one persists.
    if (index === -1) return;
    await persistMove(
      movedId,
      lane.stage,
      e.detail.items[index - 1]?.id,
      e.detail.items[index + 1]?.id
    );
  }

  /**
   * Both neighbours are sent when they exist. The server resolves them inside
   * the destination column and ignores any it cannot find there, so a board
   * another user has rearranged since this one loaded degrades to an append
   * rather than to a position computed from a card that has moved on.
   */
  async function persistMove(
    /** @type {string} */ id,
    /** @type {string} */ columnId,
    /** @type {string | undefined} */ aboveId,
    /** @type {string | undefined} */ belowId
  ) {
    const body = new FormData();
    body.set('id', id);
    body.set('column_id', columnId);
    if (aboveId) body.set('above_id', aboveId);
    if (belowId) body.set('below_id', belowId);
    try {
      const res = await fetch('?/move', { method: 'POST', body });
      const result = deserialize(await res.text());
      if (result.type === 'success') {
        moveError = '';
        return;
      }
      moveError =
        (result.type === 'failure' && /** @type {any} */ (result.data)?.error) ||
        $_('opportunity.list.move_error_fallback_failure');
    } catch {
      moveError = $_('opportunity.list.move_error_fallback_catch');
    }
    await invalidateAll();
  }

  /**
   * Whether the current view is actually narrowed, as opposed to merely
   * carrying a query string. `page.url.search` alone is the wrong test: on
   * this page `?view=board` is a layout toggle, not a filter, so a bare
   * "Board" click from the unfiltered list would otherwise claim these
   * numbers are filtered when nothing was. `'all'` is pipeline's own
   * empty-params preset (see `$lib/v2/filters.js`), its declared default, so
   * being on any other preset counts as filtered even when that preset
   * (`open`, `stalled`) sets no field a chip would represent.
   */
  let isFiltered = $derived(
    activeChips('pipeline', page.url, { people: data.people, tags: data.tags }).length > 0 ||
      activePresetKey('pipeline', page.url, data.meId) !== 'all'
  );

  /**
   * The List<->Board toggle used to be two static hrefs, `/pipeline` and
   * `/pipeline?view=board`, so switching layout silently dropped every active
   * filter. Board to List keeps every param and drops only `view`: the list
   * can run everything the board could and more. List to Board keeps
   * `view=board` plus only the params the board can actually honour
   * (`data.boardFields`, always returned by `load` regardless of the current
   * view, see the note in `+page.server.js`); the rest are deliberately
   * dropped, and it is visible rather than silent, since the chips for them
   * disappear along with the params.
   */
  let listHref = $derived(withoutParam(page.url, 'view'));
  let boardHref = $derived.by(() => {
    const next = new SvelteURLSearchParams();
    next.set('view', 'board');
    // `search` mirrors what `+page.server.js` forwards to the board itself
    // (`kanban_views.py:123` reads it); it is not one of `boardFields`
    // because it is not a descriptor field, just like on the list view.
    for (const key of [...(data.boardFields ?? []), 'search']) {
      const value = page.url.searchParams.get(key);
      if (value) next.set(key, value);
    }
    return `/pipeline?${next}`;
  });
</script>

<PageHeader title={$_('opportunity.list.title')}>
  {#snippet sub()}
    <!-- Totals come from the API aggregate, never from the rows on screen.
         Not "open deals": the default view is now the pipeline's own "All
         deals" preset (empty params), which includes closed stages, so a word
         that was only ever true under the old hardcoded ?open=true would lie
         here as soon as somebody switched presets. -->
    <span class="v2-num">{count(totals.count)}</span>
    {$_('opportunity.list.deals_suffix', { values: { count: totals.count } })} ·
    <span class="v2-num">{money(totals.amount_sum, data.org.currency)}</span> ·
    <span class="v2-num">{money(totals.weighted_sum, data.org.currency)}</span>
    {$_('opportunity.list.weighted_suffix')} ·
    <span class="v2-num" style="color:var(--v2-rust)">{totals.stalled_count}</span>
    {$_('opportunity.list.stalled_suffix', { values: { count: totals.stalled_count } })}
  {/snippet}
  {#snippet actions()}
    {#if view === 'board'}
      <a class="v2-btn v2-btn-quiet" href={resolve(asInternalPath(listHref))}
        ><List />{$_('opportunity.list.list_view_button')}</a
      >
      <span class="v2-btn" aria-current="true"
        ><Columns3 />{$_('opportunity.list.board_view_button')}</span
      >
    {:else}
      <span class="v2-btn" aria-current="true"
        ><List />{$_('opportunity.list.list_view_button')}</span
      >
      <a class="v2-btn v2-btn-quiet" href={resolve(asInternalPath(boardHref))}
        ><Columns3 />{$_('opportunity.list.board_view_button')}</a
      >
    {/if}
    <a class="v2-btn v2-btn-primary" href={resolve('/pipeline/new')}
      ><Plus />{$_('opportunity.list.new_deal_button')}</a
    >
  {/snippet}
</PageHeader>

{#if isFiltered}
  <p class="v2-sub" style="font-size:11.5px;margin:8px 0 0">
    {$_('opportunity.list.filtered_notice')}
  </p>
{/if}

<FilterBar
  page="pipeline"
  url={page.url}
  people={data.people}
  tags={data.tags}
  meId={data.meId}
  onlyFields={data.onlyFields}
  onlyPresets={data.onlyPresets}
  meta={view === 'board' ? $_('opportunity.list.board_meta') : $_('opportunity.list.list_meta')}
/>

{#if moveError}
  <!-- The card has already snapped back by the time this renders, so the
       message explains a reversal the user has just watched rather than
       warning about one to come. Same banner as the tasks board. -->
  <div class="v2-pad" style="padding-top:12px;flex:none">
    <div class="v2-move-error" role="status">
      <TriangleAlert size={13} style="flex:none" />
      <span>{moveError}</span>
    </div>
  </div>
{/if}

{#if view === 'board'}
  <div class="v2-board">
    {#each boardLanes as lane (lane.stage)}
      <section class="v2-lane">
        <div class="v2-lane-head">
          <span class="v2-label">{$_(opportunityStageKey(lane.stage))}</span>
          <span class="v2-num"
            >{count(laneCount(lane))} · {money(laneSum(lane), data.org.currency)}</span
          >
        </div>
        {#if lane.truncated}
          <!-- The API caps a column at 100 cards. Saying so beats a lane that
               silently stops. Outside the dndzone below, so it never becomes a
               drop target of its own. -->
          <p class="v2-sub" style="padding:0 2px 6px;font-size:11.5px">
            {$_('opportunity.list.board_truncated_prefix')}
            <span class="v2-num">{lane.rows.length}</span>. {$_(
              'opportunity.list.board_truncated_suffix'
            )}
          </p>
        {/if}
        <div
          class="v2-lane-body"
          use:dndzone={{ items: lane.rows, flipDurationMs: FLIP_MS }}
          onconsider={(e) => onConsider(lane, e)}
          onfinalize={(e) => onFinalize(lane, e)}
        >
          {#each lane.rows as d (d.id)}
            <!-- A div, not an anchor: dragging a link fights the browser's own
                 link-drag, so the card is the drag handle and the name inside
                 it is the way in. Matches the tasks board. -->
            <div class="v2-deal-card v2-card-drag" animate:flip={{ duration: FLIP_MS }}>
              <a
                href={resolve(`/pipeline/${d.id}`)}
                style="font-weight:600;letter-spacing:-0.012em;line-height:1.3;color:inherit;text-decoration:none"
                >{d.name}</a
              >
              <div class="v2-sub" style="margin-top:2px">{d.account.name}</div>
              <div style="margin-top:9px">
                <Pill tone={AGING_TONE[d.aging_status]} dot>
                  {$_(agingKey(d.aging_status)) +
                    (d.aging_status === 'green'
                      ? ''
                      : ` · ${d.days_in_current_stage}${$_('opportunity.list.days_short_suffix')}`)}
                </Pill>
              </div>
              <div class="v2-deal-card-foot">
                <Avatar name={d.assigned_to} size={21} />
                <span class="v2-num" style="font-weight:600">{money(d.amount, d.currency)}</span>
                <span class="v2-sub" style="margin-left:auto;font-size:11.5px"
                  >{shortDate(d.closed_on)}</span
                >
              </div>
            </div>
          {:else}
            <p class="v2-sub" style="padding:10px 2px;font-size:12px">
              {$_('opportunity.list.lane_empty')}
            </p>
          {/each}
        </div>
      </section>
    {/each}
  </div>
{:else if deals.length === 0}
  <div class="v2-scroll">
    <EmptyState title={$_('opportunity.list.empty_title')} body={$_('opportunity.list.empty_body')}>
      {#snippet icon()}<Columns3 size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/pipeline/new')}
          >{$_('opportunity.list.new_deal_button')}</a
        >
        <a class="v2-btn" href={resolve('/leads')}>{$_('opportunity.list.go_to_leads_button')}</a>
      {/snippet}
    </EmptyState>
  </div>
{:else}
  <div class="v2-scroll">
    <div class="v2-table-wrap">
      <table class="v2-table">
        <thead>
          <tr>
            <th>{$_('opportunity.list.col_deal')}</th>
            <th>{$_('opportunity.list.col_stage')}</th>
            <th>{$_('opportunity.list.col_health')}</th>
            <th class="v2-r">{$_('opportunity.list.col_value')}</th>
            <th>{$_('opportunity.list.col_closing')}</th>
            <th class="v2-r">{$_('opportunity.list.col_in_stage')}</th>
            <th>{$_('opportunity.list.col_owner')}</th>
          </tr>
        </thead>
        <tbody>
          {#each deals as d (d.id)}
            <tr>
              <td>
                <a class="v2-row-link" href={resolve(`/pipeline/${d.id}`)}>
                  <div class="v2-table-primary">{d.name}</div>
                  <div class="v2-table-secondary">{d.account.name}</div>
                </a>
              </td>
              <td><StageMeter stage={d.stage} /></td>
              <td data-m="tag">
                <Pill tone={AGING_TONE[d.aging_status]} dot>{$_(agingKey(d.aging_status))}</Pill>
              </td>
              <td class="v2-r v2-num" style="font-weight:600">{money(d.amount, d.currency)}</td>
              <td>{shortDate(d.closed_on)}</td>
              <!-- Hidden on a phone: the Health pill beside the title is computed
                   from this same number, so showing both spends a line to say
                   the same thing twice. -->
              <td
                class="v2-r v2-num"
                data-m="hide"
                style={d.aging_status === 'red'
                  ? 'color:var(--v2-rust);font-weight:600'
                  : 'color:var(--v2-slate)'}
              >
                {d.days_in_current_stage}{$_('opportunity.list.days_short_suffix')}
              </td>
              <td data-m="hide"><Avatar name={d.assigned_to} size={22} /></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="v2-sub v2-pad" style="font-size:12px;padding-bottom:24px">
      {$_('opportunity.list.showing_prefix')} <span class="v2-num">{deals.length}</span>
      {$_('opportunity.list.of_connector')}
      <span class="v2-num">{count(totals.count)}</span>
    </p>
  </div>
{/if}
