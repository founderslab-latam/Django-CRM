<script>
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import { invalidateAll } from '$app/navigation';
  import { SvelteSet } from 'svelte/reactivity';
  import { _ } from '$lib/i18n/index.js';
  import { casePriorityKey, caseStatusKey, caseTypeKey } from '$lib/cases/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SectionTabs from '$lib/v2/components/SectionTabs.svelte';
  import FilterBar from '$lib/v2/components/FilterBar.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import BulkActionBar from '$lib/v2/components/BulkActionBar.svelte';
  import { count, shortAge } from '$lib/v2/format.js';
  import { PRIORITY_TONE, CASE_STATUS_TONE } from '$lib/v2/enums.js';
  import { Plus, LifeBuoy } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let tickets = $derived(data.tickets);
  let totals = $derived(data.totals);

  // Bulk selection: loaded rows only, never the whole filtered set. SvelteSet
  // is reactive on mutation, so add/delete/clear below re-render without
  // reassigning the whole set.
  let selected = new SvelteSet();
  let banner = $state('');

  /** @param {string} id */
  function toggle(id) {
    if (selected.has(id)) selected.delete(id);
    else selected.add(id);
  }
  function toggleAll() {
    if (selected.size === tickets.length) {
      selected.clear();
    } else {
      selected.clear();
      for (const t of tickets) selected.add(t.id);
    }
  }
  /**
   * @param {'update'|'delete'} kind
   * @param {Record<string, number>} s
   */
  function summaryText(kind, s) {
    const parts = [
      kind === 'delete'
        ? $_('cases.list.bulk_deleted', { values: { count: s.deleted } })
        : $_('cases.list.bulk_updated', { values: { count: s.updated } })
    ];
    if (s.no_access)
      parts.push($_('cases.list.bulk_skipped_no_access', { values: { count: s.no_access } }));
    if (s.approval_required)
      parts.push($_('cases.list.bulk_need_approval', { values: { count: s.approval_required } }));
    if (s.closed_on_required)
      parts.push(
        $_('cases.list.bulk_missing_close_date', { values: { count: s.closed_on_required } })
      );
    if (s.invalid) parts.push($_('cases.list.bulk_invalid', { values: { count: s.invalid } }));
    return parts.join(' · ');
  }

  /**
   * How the first-reply clock stands.
   *
   * The deadline arrives from the server, where it is walked through the org's
   * business calendar and pushed forward by any time the ticket spent waiting
   * on the customer. Recomputing it here from `opened_at + hours`, which is
   * what the mock did, would put a second, quietly different answer on the
   * same screen.
   *
   * A progress bar only means something while there is still time on the
   * clock. Past the deadline a bar pinned at 100% says nothing about how bad
   * it is, so we stop drawing one and say how far over it went instead.
   *
   * @param {any} t
   */
  function responsePressure(t) {
    if (t.first_response_at) {
      const took =
        (new Date(t.first_response_at).getTime() - new Date(t.opened_at).getTime()) / 6e4;
      return {
        state: 'met',
        label: $_('cases.list.first_reply_met', { values: { duration: fmtMins(took) } }),
        tone: 'moss'
      };
    }
    if (!t.first_response_deadline) {
      return { state: 'none', label: $_('cases.list.first_reply_no_target'), tone: 'slate' };
    }
    const now = Date.now();
    const opened = new Date(t.opened_at).getTime();
    const due = new Date(t.first_response_deadline).getTime();
    if (now >= due) {
      return {
        state: 'breached',
        label: $_('cases.list.first_reply_over', {
          values: { duration: fmtMins((now - due) / 6e4) }
        }),
        tone: 'rust'
      };
    }
    const pct = Math.max(0, Math.min(100, Math.round(((now - opened) / (due - opened)) * 100)));
    return {
      state: 'running',
      pct,
      label: $_('cases.list.first_reply_left', {
        values: { duration: fmtMins((due - now) / 6e4) }
      }),
      tone: pct >= 75 ? 'rust' : pct >= 50 ? 'clay' : 'slate'
    };
  }

  /** @param {number} m */
  function fmtMins(m) {
    const n = Math.max(0, Math.round(m));
    if (n < 60) return `${n}m`;
    if (n < 1440) return `${Math.round(n / 60)}h`;
    return `${Math.round(n / 1440)}d`;
  }

  const TONE_VAR = {
    moss: 'var(--v2-moss)',
    rust: 'var(--v2-rust)',
    clay: 'var(--v2-clay)',
    slate: 'var(--v2-slate)'
  };
</script>

<PageHeader title={$_('cases.list.title')}>
  {#snippet sub()}
    <span class="v2-num">{count(totals.open)}</span>
    {$_('cases.list.sub_open', { values: { count: totals.open } })} ·
    <span class="v2-num" style="color:var(--v2-rust)">{totals.urgent}</span>
    {$_('cases.list.sub_urgent', { values: { count: totals.urgent } })} ·
    <!-- Not "breaching today". A breach depends on the org's business calendar
         and is a per-row calculation; nobody having replied yet is a fact the
         queue can establish, and it is the one that decides what to open. -->
    <span class="v2-num">{count(totals.awaiting_reply)}</span>
    {$_('cases.list.sub_no_reply')}
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn v2-btn-primary" href={resolve('/tickets/new')}
      ><Plus />{$_('cases.list.new_button')}</a
    >
  {/snippet}
</PageHeader>

{#if page.url.search}
  <p class="v2-sub" style="font-size:11.5px;margin:8px 0 0">
    {$_('cases.list.filtered_notice')}
  </p>
{/if}

<!-- Approvals and Analytics were buttons in this header that went nowhere.
     They are sibling pages, so they belong in a tab strip that also tells you
     which one you are on. -->
<SectionTabs set="tickets" />

{#if banner}
  <p class="v2-sub" style="font-size:12px;margin:8px 0 0">{banner}</p>
{/if}
{#if selected.size > 0}
  <BulkActionBar
    ids={[...selected]}
    people={data.people}
    tags={data.tags}
    onclear={() => selected.clear()}
    ondone={async () => {
      // The form action returned; show its summary, refresh, clear selection.
      const r = page.form;
      if (r?.ok) banner = summaryText(r.kind, r.summary);
      selected.clear();
      await invalidateAll();
    }}
  />
{/if}

<FilterBar
  page="tickets"
  url={page.url}
  people={data.people}
  tags={data.tags}
  meId={data.meId}
  meta={$_('cases.list.filter_meta')}
/>

<div class="v2-scroll">
  {#if tickets.length === 0}
    <!-- An empty queue is good news, so it does not read like a failure. -->
    <EmptyState
      title={data.showAll ? $_('cases.list.empty_all_title') : $_('cases.list.empty_open_title')}
      body={data.showAll ? $_('cases.list.empty_all_body') : $_('cases.list.empty_open_body')}
    >
      {#snippet icon()}<LifeBuoy size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/tickets/new')}
          >{$_('cases.list.new_button')}</a
        >
        {#if !data.showAll}
          <a class="v2-btn" href={resolve('/tickets?all=1')}
            >{$_('cases.list.show_closed_button')}</a
          >
        {/if}
        <a class="v2-btn" href={resolve('/solutions')}>{$_('cases.list.knowledge_base_button')}</a>
      {/snippet}
    </EmptyState>
  {:else}
    <div class="v2-table-wrap">
      <table class="v2-table">
        <thead>
          <tr>
            <th style="width:34px">
              <input
                type="checkbox"
                aria-label={$_('cases.list.select_all_aria')}
                checked={tickets.length > 0 && selected.size === tickets.length}
                onchange={toggleAll}
              />
            </th>
            <th>{$_('cases.list.col_subject')}</th>
            <th>{$_('cases.list.col_priority')}</th>
            <th>{$_('cases.list.col_status')}</th>
            <th>{$_('cases.list.col_type')}</th>
            <th>{$_('cases.list.col_account')}</th>
            <th>{$_('cases.list.col_assignee')}</th>
            <th class="v2-r">{$_('cases.list.col_age')}</th>
            <th style="width:130px">{$_('cases.list.col_first_reply')}</th>
          </tr>
        </thead>
        <tbody>
          {#each tickets as t (t.id)}
            {@const p = responsePressure(t)}
            <tr>
              <td data-m="lead">
                <input
                  type="checkbox"
                  aria-label={$_('cases.list.select_row_aria')}
                  checked={selected.has(t.id)}
                  onchange={() => toggle(t.id)}
                />
              </td>
              <td data-m="title">
                <a class="v2-row-link" href={resolve(`/tickets/${t.id}`)}>
                  <span class="v2-table-primary">{t.name}</span>
                </a>
              </td>
              <td
                ><Pill tone={PRIORITY_TONE[t.priority]}>{$_(casePriorityKey(t.priority))}</Pill></td
              >
              <td data-m="tag"
                ><Pill tone={CASE_STATUS_TONE[t.status]}>{$_(caseStatusKey(t.status))}</Pill></td
              >
              <!-- Nullable on the model and null on plenty of rows, so it says
                   so rather than printing an empty cell. -->
              <td class="v2-muted" data-m="hide" style="font-size:12.5px">
                {t.case_type ? $_(caseTypeKey(t.case_type)) : '—'}
              </td>
              <td class="v2-muted" style="font-size:12.5px">
                {#if t.account}
                  <a class="v2-row-link" href={resolve(`/accounts/${t.account.id}`)}
                    >{t.account.name}</a
                  >
                {:else}
                  {$_('cases.list.no_account')}
                {/if}
              </td>
              <td data-m="hide">
                {#if t.assignee}
                  <Avatar name={t.assignee} size={22} />
                {:else}
                  <span class="v2-muted" style="font-size:12.5px"
                    >{$_('cases.list.unassigned')}</span
                  >
                {/if}
              </td>
              <td class="v2-r v2-num v2-muted" data-m="meta">{shortAge(t.opened_at)}</td>
              <!-- Kept on a phone, unlike the other trailing columns: a running
                   first-reply clock is the one thing in this queue that decides
                   what to open next. It takes its own line so the meter has a
                   width to fill. -->
              <td data-m="bar">
                {#if p.state === 'running'}
                  <div style="display:flex;align-items:center;gap:8px">
                    <span
                      style="flex:1;height:4px;border-radius:3px;background:var(--v2-line);overflow:hidden;display:block"
                    >
                      <i
                        style="display:block;height:100%;width:{p.pct}%;background:{TONE_VAR[
                          p.tone
                        ]}"
                      ></i>
                    </span>
                    <span class="v2-num" style="font-size:11px;color:{TONE_VAR[p.tone]}"
                      >{p.label}</span
                    >
                  </div>
                {:else}
                  <span class="v2-num" style="font-size:11.5px;color:{TONE_VAR[p.tone]}"
                    >{p.label}</span
                  >
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="v2-sub v2-pad" style="font-size:12px;padding-bottom:24px">
      {$_('cases.list.showing_prefix')}
      <span class="v2-num">{tickets.length}</span>
      {$_('cases.list.of_connector')}
      <span class="v2-num">{count(totals.count)}</span>
      {#if !data.showAll}
        · <a href={resolve('/tickets?all=1')} style="color:inherit"
          >{$_('cases.list.include_closed_link')}</a
        >
      {:else}
        · <a href={resolve('/tickets')} style="color:inherit">{$_('cases.list.open_only_link')}</a>
      {/if}
    </p>
  {/if}
</div>
