<script>
  import { resolve } from '$app/paths';
  /**
   * Every row here is a decision, so every row carries the decision. v1 sent
   * you into the case, then into a modal, to answer a yes/no question that was
   * already fully stated in the list.
   *
   * Two things this page refuses to fake:
   *
   * 1. `can_act` comes from the server (Approval.can_be_acted_on_by, minus your
   *    own requests). The client does not recompute it, the answer depends on
   *    rule.approvers and on your role, and guessing wrong means a button that
   *    403s.
   * 2. A row you cannot act on is shown, greyed, with the reason. Hiding it
   *    makes a stuck approval invisible to the only person who might chase the
   *    approver, which is how the oldest one here reached twenty hours.
   */
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import { casePriorityKey, caseTypeKey, approvalStateKey } from '$lib/cases/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SectionTabs from '$lib/v2/components/SectionTabs.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { count, shortAge, relativeDays } from '$lib/v2/format.js';
  import { APPROVAL_STATE_TONE, PRIORITY_TONE } from '$lib/v2/enums.js';
  import { ShieldCheck, TriangleAlert, ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let totals = $derived(data.totals);
  let pending = $derived(data.approvals.filter((a) => a.state === 'pending'));

  /**
   * The first row you can actually act on. Only that one gets the ember
   * button: same rule as the Today queue, and for the same reason: a column
   * of identical orange buttons is a column with no emphasis in it, so the
   * colour stops meaning "start here". The rest are ordinary buttons and work
   * exactly the same.
   */
  let firstActionable = $derived(pending.find((a) => a.can_act)?.id ?? null);
  let decided = $derived(data.approvals.filter((a) => a.state !== 'pending'));
  let rules = $derived(data.rules);

  /** The one row whose reject-reason box is open (a rejection needs a reason). */
  let rejectingId = $state(/** @type {string | null} */ (null));

  /**
   * Why a non-actionable row is blocked, in the words of the rule that says so.
   * Only called for rows that are neither yours nor actionable. An own request
   * gets its own banner, so this never has to explain that case.
   */
  function blockedReason(a) {
    if (a.rule.approvers.length)
      return $_('cases.approvals.blocked_named', {
        values: { approvers: a.rule.approvers.join(` ${$_('cases.approvals.or_connector')} `) }
      });
    return $_('cases.approvals.blocked_role', {
      values: { role: a.rule.approver_role }
    });
  }
</script>

<PageHeader title={$_('cases.approvals.title')}>
  {#snippet sub()}
    <span class="v2-num">{count(totals.awaiting_you)}</span>
    {$_('cases.approvals.sub_waiting_on_you')} ·
    <span class="v2-num">{count(totals.pending)}</span>
    {$_('cases.approvals.sub_pending_org')}
  {/snippet}
</PageHeader>

<SectionTabs set="tickets" />

{#if form?.error}
  <div class="v2-pad" style="padding-top:12px;flex:none">
    <div class="v2-approval-error">{form.error}</div>
  </div>
{/if}

<div class="v2-pad" style="padding-top:16px;flex:none">
  <div class="v2-stats">
    <StatCard
      label={$_('cases.approvals.stat_waiting_on_you')}
      value={count(totals.awaiting_you)}
      tone="clay"
      detail={$_('cases.approvals.stat_waiting_on_you_detail')}
    />
    <StatCard
      label={$_('cases.approvals.stat_pending_org')}
      value={count(totals.pending)}
      tone="ink"
    />
    <StatCard
      label={$_('cases.approvals.stat_oldest_waiting')}
      value={`${totals.oldest_pending_hours}h`}
      tone={totals.oldest_pending_hours > 8 ? 'rust' : 'slate'}
      detail={$_('cases.approvals.stat_oldest_waiting_detail')}
    />
    <StatCard
      label={$_('cases.approvals.stat_decided_week')}
      value={count(totals.decided_this_week)}
      tone="moss"
    />
  </div>
</div>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-bottom:30px">
    {#if pending.length === 0}
      <EmptyState title={$_('cases.approvals.empty_title')} body={$_('cases.approvals.empty_body')}>
        {#snippet icon()}<ShieldCheck size={21} />{/snippet}
      </EmptyState>
    {:else}
      <div class="v2-label" style="margin-bottom:10px">{$_('cases.approvals.pending_label')}</div>
      <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:26px">
        {#each pending as a (a.id)}
          {@const blocked = !a.is_own_request && !a.can_act ? blockedReason(a) : null}
          <div class="v2-card" style="padding:15px 16px;opacity:{blocked ? 0.62 : 1}">
            <div class="v2-approval">
              <div style="flex:1;min-width:0">
                <div class="v2-sub" style="font-size:11.5px;margin-bottom:3px">
                  {#if a.case.account}{a.case.account.name} ·
                  {/if}{$_('cases.approvals.row_requested_by', {
                    values: { name: a.requested_by }
                  })} · {$_('cases.approvals.row_waiting')}
                  <span class="v2-num">{shortAge(a.created_at)}</span>
                </div>
                <a
                  href={resolve(`/tickets/${a.case.id}`)}
                  style="color:inherit;font-weight:600;font-size:14px;text-decoration:none"
                >
                  {a.case.name}
                </a>
                <div style="display:flex;gap:6px;align-items:center;margin-top:7px;flex-wrap:wrap">
                  <Pill tone={PRIORITY_TONE[a.case.priority]}
                    >{$_(casePriorityKey(a.case.priority))}</Pill
                  >
                  <span class="v2-sub" style="font-size:11.5px">{a.rule.name}</span>
                </div>
              </div>

              <!-- The decision, in the row. Approve is the one ember control
                   on this page; reject is quiet, because the destructive
                   option should not be the eye-catching one. -->
              <div class="v2-approval-actions">
                {#if a.is_own_request}
                  <!-- You cannot decide your own request; withdrawing it is the
                       only action you have on your own row. -->
                  <form method="POST" action="?/cancel" use:enhance>
                    <input type="hidden" name="id" value={a.id} />
                    <button class="v2-btn" type="submit"
                      >{$_('cases.approvals.withdraw_button')}</button
                    >
                  </form>
                {:else if a.can_act}
                  {#if rejectingId === a.id}
                    <form method="POST" action="?/reject" use:enhance class="v2-reject-form">
                      <input type="hidden" name="id" value={a.id} />
                      <!-- svelte-ignore a11y_autofocus -->
                      <input
                        name="reason"
                        placeholder={$_('cases.approvals.reject_reason_placeholder')}
                        required
                        autofocus
                        class="v2-reject-input"
                      />
                      <button class="v2-btn" type="submit"
                        >{$_('cases.approvals.reject_confirm_button')}</button
                      >
                      <button class="v2-btn" type="button" onclick={() => (rejectingId = null)}>
                        {$_('cases.approvals.reject_cancel_button')}
                      </button>
                    </form>
                  {:else}
                    <button class="v2-btn" onclick={() => (rejectingId = a.id)}
                      >{$_('cases.approvals.reject_button')}</button
                    >
                    <form method="POST" action="?/approve" use:enhance>
                      <input type="hidden" name="id" value={a.id} />
                      <button
                        class="v2-btn"
                        class:v2-btn-primary={a.id === firstActionable}
                        type="submit"
                      >
                        {$_('cases.approvals.approve_button')}
                      </button>
                    </form>
                  {/if}
                {:else}
                  <span class="v2-sub v2-approval-reason">
                    {blocked}
                  </span>
                {/if}
              </div>
            </div>

            {#if a.is_own_request}
              <!-- Separation of duties is now enforced in ApprovalApproveView:
                   the requester cannot approve or reject their own request, so
                   `can_act` is false here and the buttons above are absent.
                   This explains why. -->
              <div
                style="display:flex;gap:9px;align-items:center;margin-top:12px;padding-top:11px;border-top:1px solid var(--v2-line-soft)"
              >
                <TriangleAlert size={15} style="color:var(--v2-clay);flex:none" />
                <span class="v2-sub" style="font-size:12px">
                  {$_('cases.approvals.own_request_note')}
                </span>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    {#if decided.length}
      <div class="v2-label" style="margin-bottom:10px">
        {$_('cases.approvals.recently_decided_label')}
      </div>
      <div class="v2-card" style="overflow:hidden;margin-bottom:26px">
        {#each decided as a (a.id)}
          <div
            style="display:flex;gap:12px;align-items:flex-start;padding:12px 15px;border-bottom:1px solid var(--v2-line-soft)"
          >
            <div style="flex:1;min-width:0">
              <a
                href={resolve(`/tickets/${a.case.id}`)}
                style="color:inherit;font-size:13px;font-weight:550;text-decoration:none"
              >
                {a.case.name}
              </a>
              <div class="v2-sub" style="font-size:11.5px;margin-top:2px">
                {a.state === 'cancelled'
                  ? $_('cases.approvals.decided_withdrawn_by', {
                      values: { name: a.requested_by }
                    })
                  : $_('cases.approvals.decided_by', {
                      values: {
                        state: $_(approvalStateKey(a.state)),
                        approver: a.approver,
                        when: relativeDays(a.decided_at)
                      }
                    })}
              </div>
              <!-- A rejection always carries a reason: the endpoint returns
                   400 without one, so the column is never empty. -->
              {#if a.reason}
                <div class="v2-sub" style="font-size:12px;margin-top:5px;white-space:normal">
                  “{a.reason}”
                </div>
              {:else if a.note}
                <div class="v2-sub" style="font-size:12px;margin-top:5px;white-space:normal">
                  “{a.note}”
                </div>
              {/if}
            </div>
            <Pill tone={APPROVAL_STATE_TONE[a.state]}>{$_(approvalStateKey(a.state))}</Pill>
          </div>
        {/each}
      </div>
    {/if}

    <div class="v2-label" style="margin-bottom:10px">{$_('cases.approvals.rules_title')}</div>
    <div class="v2-card" style="overflow:hidden">
      {#each rules as r (r.id)}
        <div class="v2-setting">
          <div class="v2-setting-body">
            <b>{r.name}</b>
            <span class="v2-sub" style="font-size:11.5px">
              <!-- What the rule matches, in the order a person would say it.
                   A rule with no filters matches every close, which is worth
                   reading as a sentence rather than as three empty columns. -->
              {[
                r.match_priority
                  ? $_('cases.approvals.rule_match_priority', {
                      values: { priority: $_(casePriorityKey(r.match_priority)) }
                    })
                  : null,
                r.match_case_type ? $_(caseTypeKey(r.match_case_type)) : null,
                r.match_team
                  ? $_('cases.approvals.rule_match_team', { values: { team: r.match_team.name } })
                  : null
              ]
                .filter(Boolean)
                .join(' · ') || $_('cases.approvals.rule_match_every')}
              {$_('cases.approvals.rule_cleared_by', {
                values: {
                  who: r.approvers.length
                    ? r.approvers.join(` ${$_('cases.approvals.or_connector')} `)
                    : $_('cases.approvals.rule_any_role', { values: { role: r.approver_role } })
                }
              })}
            </span>
          </div>
          {#if r.pending_count}
            <span class="v2-sub v2-num" style="font-size:12px"
              >{$_('cases.approvals.rule_pending_count', {
                values: { count: r.pending_count }
              })}</span
            >
          {/if}
          <Pill tone={r.is_active ? 'moss' : 'slate'}
            >{r.is_active
              ? $_('cases.approvals.rule_active')
              : $_('cases.approvals.rule_off')}</Pill
          >
          <ChevronRight size={15} style="color:var(--v2-slate);flex:none" />
        </div>
      {/each}
    </div>

    <!-- MANAGER is a valid approver_role on the model but not a valid
         Profile.role, so a rule set to MANAGER currently matches nobody. Said
         here rather than left for someone to discover via a stuck queue. -->
    {#if rules.some((r) => r.is_active && r.approver_role === 'MANAGER' && !r.approvers.length)}
      <p class="v2-sub" style="font-size:12px;margin-top:12px">
        {$_('cases.approvals.rules_manager_warning')}
      </p>
    {/if}
  </div>
</div>

<style>
  .v2-approval {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .v2-approval-actions {
    display: flex;
    gap: 7px;
    flex: none;
    align-items: center;
  }
  .v2-approval-actions form {
    display: contents;
  }
  .v2-reject-form {
    display: flex !important;
    gap: 6px;
    align-items: center;
  }
  .v2-reject-input {
    font: inherit;
    font-size: 12.5px;
    padding: 5px 9px;
    border: 1px solid var(--v2-line);
    border-radius: 6px;
    background: var(--v2-bg);
    color: inherit;
    min-width: 160px;
  }
  .v2-approval-error {
    padding: 11px 14px;
    border: 1px solid var(--v2-rust);
    border-radius: 8px;
    background: color-mix(in srgb, var(--v2-rust) 8%, transparent);
    color: var(--v2-rust);
    font-size: 13px;
  }
  .v2-approval-reason {
    font-size: 11.5px;
    max-width: 230px;
    text-align: right;
  }

  /* At 414px the desktop row leaves the ticket title about five words per
     line while the reason text takes half the width. Stack instead: the
     question first, the answer under it. */
  @media (max-width: 768px) {
    .v2-approval {
      flex-wrap: wrap;
    }
    .v2-approval-actions {
      width: 100%;
      margin-top: 12px;
      justify-content: flex-end;
    }
    /* flex:1 so the reason fills the row and reads from the left margin.
       Right-aligned prose in a flex-end container looks like a caption. */
    .v2-approval-reason {
      flex: 1;
      max-width: none;
      text-align: left;
    }
  }
</style>
