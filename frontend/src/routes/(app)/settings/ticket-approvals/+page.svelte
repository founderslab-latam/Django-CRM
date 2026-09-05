<script>
  import { resolve } from '$app/paths';
  /**
   * What gates a ticket close, and who can clear it.
   *
   * The queue at /v2/tickets/approvals answers "what is waiting on me". This
   * answers "what will be gated next time, and by whom", the same rows, a
   * different question, which is why it is a settings page and not a tab.
   *
   * Three states the model permits and the form does not warn about, all
   * flagged on the row here. See `./matching.js`, which owns the rules:
   *
   * - approver_role MANAGER with no named approvers. Profile.role is only
   *   ADMIN or USER, so the rule matches nobody and what it gates can never be
   *   closed by anyone.
   * - Two active rules with identical conditions. Only one rule gates a given
   *   ticket, and among equals the newest takes every case, so the older is
   *   dead however live it looks.
   * - Named approvers read as a narrowing and are a widening: anyone holding
   *   the role clears the rule too.
   *
   * Separation of duties, an admin clearing their own requested close, is
   * NOT a gap to warn about: `ApprovalApproveView` rejects an approval whose
   * requester is the approver, unconditionally (no admin exception), so the API
   * enforces it however a rule is configured. An earlier version of this page
   * flagged "any admin, including the requester" as a hole; the view has since
   * closed it, so the warning is gone.
   */
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import SettingsFormPanel from '$lib/v2/components/SettingsFormPanel.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { count } from '$lib/v2/format.js';
  import { approverRoleKey } from '$lib/settings/labels.js';
  import { casePriorityKey, caseTypeKey } from '$lib/cases/labels.js';
  import { missingOptions, inactiveOptionLabel } from '$lib/v2/pickers.js';
  import {
    approverSentence,
    clearableByNobody,
    ruleMatchSentence,
    shadowedRuleIds,
    shadowedBy
  } from './matching.js';
  import { Plus, TriangleAlert, ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  // cases.approvals: PRIORITY_CHOICE and CASE_TYPE. Not in `$lib/v2/enums.js`
  // because there is no shared label map to derive from: value and label are
  // the same string for both, and no other v2 page reads either list.
  const MATCH_PRIORITIES = ['Low', 'Normal', 'High', 'Urgent'];
  const MATCH_CASE_TYPES = ['Question', 'Incident', 'Problem'];

  /**
   * Everyone who can clear a rule, as a sentence. `approverSentence` hands back
   * a descriptor; the phrasing (and the " or " join) is put together here.
   * @param {ReturnType<typeof approverSentence>} a
   */
  function approverText(a) {
    if (a.kind === 'admin') return $_('settings.ticket_approvals.cleared_admin');
    if (a.kind === 'nobody') return $_('settings.ticket_approvals.cleared_nobody');
    const names = a.named.join(` ${$_('settings.ticket_approvals.or_word')} `);
    if (a.kind === 'named') return names;
    return $_('settings.ticket_approvals.cleared_admin_or', { values: { named: names } });
  }

  /**
   * What a rule gates, as a sentence. Raw enum values from the descriptor are
   * translated through `$lib/cases/labels.js` so the vocabulary matches Cases.
   * @param {ReturnType<typeof ruleMatchSentence>} m
   */
  function matchText(m) {
    if (m.kind === 'every') return $_('settings.ticket_approvals.match_every');
    /** @type {string[]} */
    const parts = [];
    if (m.priority)
      parts.push(
        $_('settings.ticket_approvals.match_priority', {
          values: { priority: $_(casePriorityKey(m.priority)) }
        })
      );
    if (m.caseType) parts.push($_(caseTypeKey(m.caseType)).toLowerCase());
    if (m.team)
      parts.push($_('settings.ticket_approvals.match_team', { values: { team: m.team } }));
    return parts.join(' · ');
  }

  // `null` when the panel is closed, `'new'` when adding, or the rule object
  // when editing that row. One panel, two modes, so two rows can never be
  // open for edit at once.
  let editing = $state(/** @type {any} */ (null));

  function openCreate() {
    editing = 'new';
  }

  function openEdit(r) {
    editing = r;
  }

  let totals = $derived(data.totals);
  let rules = $derived(data.rules);

  // Named approvers the picker cannot offer, because the profile has been
  // deactivated since it was named. Without an option of their own the
  // multi-select submits nothing for them and an unrelated edit drops them,
  // which can widen a rule to "any admin" or, on a MANAGER rule, leave it
  // clearable by nobody.
  let missingApprovers = $derived(
    editing && editing !== 'new' ? missingOptions(data.people, editing.approvers) : []
  );

  let shadowed = $derived(shadowedRuleIds(rules));
</script>

<PageHeader title={$_('settings.ticket_approvals.title')}>
  {#snippet crumb()}<SettingsCrumb />{/snippet}
  {#snippet sub()}
    <span class="v2-num">{count(totals.active)}</span>
    {$_('settings.ticket_approvals.sub_active', { values: { count: totals.active } })} ·
    <span class="v2-num">{count(totals.pending)}</span>
    {$_('settings.ticket_approvals.sub_pending')}
  {/snippet}
  {#snippet actions()}
    {#if data.can_edit && !editing}
      <button class="v2-btn v2-btn-primary" onclick={openCreate}>
        <Plus />{$_('settings.ticket_approvals.new_button')}
      </button>
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:18px;padding-bottom:32px">
    {#if editing}
      <SettingsFormPanel
        title={editing === 'new'
          ? $_('settings.ticket_approvals.form_new')
          : $_('settings.ticket_approvals.form_edit', { values: { name: editing.name } })}
        action={editing === 'new' ? '?/create' : '?/update'}
        error={editing === 'new' ? form?.create?.error : form?.update?.error}
        submitLabel={editing === 'new'
          ? $_('settings.ticket_approvals.add_button')
          : $_('settings.ticket_approvals.save_button')}
        oncancel={() => (editing = null)}
        ondone={() => (editing = null)}
      >
        {#snippet fields()}
          {#if editing !== 'new'}
            <input type="hidden" name="id" value={editing.id} />
          {/if}

          <div class="v2-field">
            <label for="a-name">{$_('settings.ticket_approvals.field_name')}</label>
            <input
              id="a-name"
              class="v2-input"
              name="name"
              maxlength="128"
              required
              value={editing === 'new' ? '' : editing.name}
            />
          </div>

          <div class="v2-field">
            <label for="a-role">{$_('settings.ticket_approvals.field_role')}</label>
            <select id="a-role" class="v2-input" name="approver_role">
              {#each ['ADMIN', 'MANAGER'] as role (role)}
                <option
                  value={role}
                  selected={editing === 'new' ? role === 'ADMIN' : editing.approver_role === role}
                >
                  {$_(approverRoleKey(role))}
                </option>
              {/each}
            </select>
          </div>

          <div class="v2-field v2-sfp-wide">
            <label for="a-approvers">{$_('settings.ticket_approvals.field_approvers')}</label>
            <select
              id="a-approvers"
              class="v2-input"
              name="approver_ids"
              multiple
              style="height:96px"
            >
              <!-- A named approver whose profile is no longer active is not in
                   `data.people`, so it gets an option of its own here. Without
                   one the browser submits nothing for it and saving an
                   unrelated field would drop the approver silently. -->
              {#each missingApprovers as a (a.id)}
                <option value={a.id} selected>{inactiveOptionLabel(a.email)}</option>
              {/each}
              {#each data.people as p (p.id)}
                <option
                  value={p.id}
                  selected={editing !== 'new' && editing.approvers.some((a) => a.id === p.id)}
                >
                  {p.name}
                </option>
              {/each}
            </select>
            <p class="v2-hint">{$_('settings.ticket_approvals.approvers_hint')}</p>
            {#if missingApprovers.length}
              <p class="v2-hint">
                {$_('settings.ticket_approvals.approvers_inactive', {
                  values: { count: missingApprovers.length }
                })}
              </p>
            {/if}
          </div>

          <div class="v2-field">
            <label for="a-priority">{$_('settings.ticket_approvals.field_priority')}</label>
            <select id="a-priority" class="v2-input" name="match_priority">
              <option value="" selected={editing === 'new' || !editing.match_priority}>
                {$_('settings.ticket_approvals.any')}
              </option>
              {#each MATCH_PRIORITIES as p (p)}
                <option value={p} selected={editing !== 'new' && editing.match_priority === p}>
                  {$_(casePriorityKey(p))}
                </option>
              {/each}
            </select>
          </div>

          <div class="v2-field">
            <label for="a-type">{$_('settings.ticket_approvals.field_type')}</label>
            <select id="a-type" class="v2-input" name="match_case_type">
              <option value="" selected={editing === 'new' || !editing.match_case_type}>
                {$_('settings.ticket_approvals.any')}
              </option>
              {#each MATCH_CASE_TYPES as t (t)}
                <option value={t} selected={editing !== 'new' && editing.match_case_type === t}>
                  {$_(caseTypeKey(t))}
                </option>
              {/each}
            </select>
          </div>

          <div class="v2-field">
            <label for="a-team">{$_('settings.ticket_approvals.field_team')}</label>
            <select id="a-team" class="v2-input" name="match_team_id">
              <option value="" selected={editing === 'new' || !editing.match_team}>
                {$_('settings.ticket_approvals.any_team')}
              </option>
              {#each data.teams as t (t.id)}
                <option
                  value={t.id}
                  selected={editing !== 'new' && editing.match_team?.id === t.id}
                >
                  {t.name}
                </option>
              {/each}
            </select>
            {#if !data.teams.length}
              <p class="v2-hint">{$_('settings.ticket_approvals.no_teams')}</p>
            {/if}
          </div>

          {#if editing === 'new'}
            <div class="v2-field">
              <label for="a-active">{$_('settings.ticket_approvals.field_active')}</label>
              <label style="display:flex;gap:8px;align-items:center;font-weight:400">
                <input id="a-active" type="checkbox" name="is_active" value="true" checked />
                {$_('settings.ticket_approvals.active_help')}
              </label>
            </div>
          {/if}
        {/snippet}
      </SettingsFormPanel>
    {/if}

    {#if form?.deactivate?.error}
      <p class="v2-error" style="margin-bottom:12px">{form.deactivate.error}</p>
    {/if}
    {#if form?.activate?.error}
      <p class="v2-error" style="margin-bottom:12px">{form.activate.error}</p>
    {/if}
    {#if form?.remove?.error}
      <p class="v2-error" style="margin-bottom:12px">{form.remove.error}</p>
    {/if}
    {#if form?.remove?.turned_off}
      <!-- What actually happened, not what the button said. The backend
           soft-disables a rule that has approval history rather than
           destroying it, so the row is still in the list below, off, and
           saying nothing here would read as a delete that failed silently. -->
      <div class="v2-rule-flag" style="margin-bottom:12px">
        <TriangleAlert size={14} style="color:var(--v2-clay);flex:none" />
        <span>{$_('settings.ticket_approvals.turned_off_notice')}</span>
      </div>
    {/if}

    <div class="v2-label" style="margin-bottom:4px">
      {$_('settings.ticket_approvals.section_rules')}
    </div>
    <!-- The list reads as cumulative and is not. Worth one line above it,
         since every row below describes a gate and only one of them is ever
         the gate for a given ticket. -->
    <p class="v2-sub" style="font-size:11.5px;margin:0 0 10px">
      {$_('settings.ticket_approvals.rules_note')}
    </p>
    <div style="display:flex;flex-direction:column;gap:9px">
      {#each rules as r (r.id)}
        {@const beatenBy = shadowed.has(r.id) ? shadowedBy(r, rules) : null}
        <div class="v2-card" style="padding:14px 16px;opacity:{r.is_active ? 1 : 0.62}">
          <div style="display:flex;gap:11px;align-items:flex-start">
            <div style="flex:1;min-width:0">
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <b style="font-size:13.5px">{r.name}</b>
                {#if !r.is_active}
                  <Pill tone="slate">{$_('settings.ticket_approvals.pill_off')}</Pill>
                {/if}
                {#if clearableByNobody(r)}
                  <Pill tone="rust">{$_('settings.ticket_approvals.pill_nobody')}</Pill>
                {/if}
                {#if beatenBy}<Pill tone="rust">{$_('settings.ticket_approvals.pill_never')}</Pill
                  >{/if}
              </div>

              <div class="v2-sub" style="font-size:12.5px;margin-top:5px;white-space:normal">
                <b style="font-weight:600;color:var(--v2-ink)"
                  >{$_('settings.ticket_approvals.gates_label')}</b
                >
                {matchText(ruleMatchSentence(r))}
                <b style="font-weight:600;color:var(--v2-ink)">→</b>
                {$_('settings.ticket_approvals.cleared_by', {
                  values: { who: approverText(approverSentence(r)) }
                })}
              </div>

              {#if clearableByNobody(r)}
                <div class="v2-rule-flag">
                  <TriangleAlert size={14} style="color:var(--v2-rust);flex:none" />
                  <span>{$_('settings.ticket_approvals.nobody_flag')}</span>
                </div>
              {/if}

              {#if beatenBy}
                <div class="v2-rule-flag">
                  <TriangleAlert size={14} style="color:var(--v2-rust);flex:none" />
                  <span>
                    <b style="font-weight:600;color:var(--v2-ink)">{beatenBy.name}</b>{$_(
                      'settings.ticket_approvals.shadow_flag_after'
                    )}
                  </span>
                </div>
              {/if}
            </div>

            <div style="flex:none;text-align:right">
              {#if r.pending_count}
                <a
                  href={resolve('/tickets/approvals')}
                  class="v2-sub"
                  style="font-size:12px;display:inline-flex;align-items:center;gap:2px"
                >
                  <span class="v2-num">{count(r.pending_count)}</span>
                  {$_('settings.ticket_approvals.waiting')}
                  <ChevronRight size={13} />
                </a>
              {/if}
            </div>

            {#if data.can_edit}
              <div style="display:flex;gap:6px;align-items:center;flex:none">
                <button class="v2-btn v2-btn-sm" type="button" onclick={() => openEdit(r)}>
                  {$_('settings.ticket_approvals.edit_button')}
                </button>
                {#if r.is_active}
                  <ConfirmAction
                    action="?/deactivate"
                    label={$_('settings.ticket_approvals.turn_off')}
                    confirmLabel={$_('settings.ticket_approvals.turn_off')}
                    explain={$_('settings.ticket_approvals.deactivate_explain')}
                    hidden={{ id: r.id }}
                  />
                {:else}
                  <form method="POST" action="?/activate" use:enhance>
                    <input type="hidden" name="id" value={r.id} />
                    <button class="v2-btn v2-btn-sm" type="submit">
                      {$_('settings.ticket_approvals.turn_on')}
                    </button>
                  </form>
                {/if}
                <!-- Not "deleted permanently". The backend destroys a rule
                     only when it has never been used; one with any approval
                     history, in any state, is turned off instead, because the
                     approval rows have to keep pointing at it. `pending_count`
                     cannot predict which happens: it counts only the pending
                     state, and the backend's check counts every state. So the
                     line names both outcomes, and the page reports which one
                     actually happened afterwards. -->
                <ConfirmAction
                  action="?/remove"
                  label={$_('settings.ticket_approvals.delete_button')}
                  confirmLabel={$_('settings.ticket_approvals.delete_button')}
                  explain={r.pending_count > 0
                    ? $_('settings.ticket_approvals.delete_explain_pending', {
                        values: { count: r.pending_count }
                      })
                    : $_('settings.ticket_approvals.delete_explain_clean')}
                  hidden={{ id: r.id }}
                />
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </div>
</div>

<style>
  .v2-rule-flag {
    display: flex;
    gap: 7px;
    align-items: flex-start;
    margin-top: 9px;
    font-size: 12px;
    color: var(--v2-slate);
    line-height: 1.45;
  }
</style>
