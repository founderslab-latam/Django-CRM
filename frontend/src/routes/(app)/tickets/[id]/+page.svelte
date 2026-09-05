<script>
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import { casePriorityKey, caseStatusKey, caseTypeKey } from '$lib/cases/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import {
    relativeDays,
    shortAge,
    longDate,
    relativeTime,
    money,
    hoursMinutes as hm
  } from '$lib/v2/format.js';
  import { PRIORITY_TONE, CASE_STATUS_TONE } from '$lib/v2/enums.js';
  import { cascadeSummary } from './close.js';
  import {
    ChevronRight,
    Lock,
    Paperclip,
    Pencil,
    Play,
    Plus,
    Square,
    Ticket,
    Trash2,
    X
  } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let { ticket, conversation, articles, alsoOpen, contacts, attachments, activity, canReply } =
    $derived(data);

  /*
   * Closing a parent takes a confirm step, because it can close other people's
   * tickets. `data.close` is present only when the ticket has children, so an
   * ordinary ticket keeps the one-click Close it always had.
   *
   * The checkbox starts where the org set it
   * (`auto_close_children_on_parent_close`), which is the only place that
   * setting reaches a web user, and the person closing can always move it. It
   * is disabled when nothing linked is open, since there is nothing for a
   * cascade to do.
   */
  let closePanel = $state(false);
  let cascade = $state(false);
  let hasOpenChildren = $derived((data.close?.descendants ?? []).length > 0);

  function openClosePanel() {
    cascade = hasOpenChildren && data.close?.cascade_default === true;
    closePanel = true;
  }

  /*
   * The composer owns its own text rather than reading it back from `data`, so
   * a revalidation cannot wipe a half-written reply. It is cleared only on a
   * send that actually succeeded; `update({ reset: false })` below leaves it
   * alone otherwise, which is what makes a rejected send recoverable.
   */
  let body = $state('');
  let internal = $state(false);
  let sending = $state(false);

  // The picked file's name, mirrored out of the input so the composer can show
  // and clear it. `fileInput` is the element itself. A file input's value can
  // only be cleared through the DOM, not by rebinding.
  let fileName = $state('');
  /** @type {HTMLInputElement | undefined} */
  let fileInput = $state();

  /** @param {Event} e */
  function pickFile(e) {
    fileName = /** @type {HTMLInputElement} */ (e.currentTarget).files?.[0]?.name ?? '';
  }
  function clearFile() {
    if (fileInput) fileInput.value = '';
    fileName = '';
  }

  // A ticket accepts a file on its own, the API saves the attachment in a block
  // separate from the comment, so the composer sends when there is either text
  // or a file.
  let canSend = $derived(Boolean(body.trim() || fileName));

  /** @type {import('@sveltejs/kit').SubmitFunction} */
  const send = () => {
    sending = true;
    return async ({ result, update }) => {
      sending = false;
      if (result.type === 'success') {
        body = '';
        clearFile();
      }
      await update({ reset: false });
    };
  };

  /*
   * ── Time ──────────────────────────────────────────────────────────────
   *
   * `data.time.entries` holds what THIS person may see: their own rows, or
   * the whole team's for an admin, which is the API's decision. The totals
   * beside the heading come from `ticket.time_summary` instead, computed
   * across everybody, so a ticket three agents have worked does not report a
   * third of its time to each of them. Adding up the rows on screen would.
   *
   * `entries` is null, not empty, when the fetch failed. The two are
   * different answers and the panel says which.
   */
  let time = $derived(data.time);
  let entries = $derived(time.entries);
  let timeSummary = $derived(ticket.time_summary);

  /** Minutes since this page loaded, added to the server's own measurement. */
  let sinceLoad = $state(0);
  onMount(() => {
    const opened = Date.now();
    const id = setInterval(() => {
      sinceLoad = Math.floor((Date.now() - opened) / 60000);
    }, 30000);
    return () => clearInterval(id);
  });

  /**
   * How long a running timer has been going.
   *
   * Measured server-side up to page load, ticked locally after that. The
   * browser only ever contributes minutes it watched pass, so a machine with
   * the wrong date cannot report a timer as eight hours old.
   *
   * @param {any} entry
   */
  const runningMinutes = (entry) =>
    Math.floor((Date.parse(time.now) - Date.parse(entry.started_at)) / 60000) + sinceLoad;

  /**
   * Whose entry this is. Both sides are User ids: `user_details.id` on the
   * row, and the JWT's `user_id` passed down by the loader. Comparing the
   * Profile id to it would be false for everyone, silently, and the Stop
   * button would never appear.
   *
   * @param {any} entry
   */
  const isMine = (entry) => entry.profile?.user_details?.id === time.viewerUserId;

  /** This person's own running timer, if they have one on this ticket. */
  let myTimer = $derived((entries ?? []).find((/** @type {any} */ e) => !e.ended_at && isMine(e)));

  let timeBusy = $state(false);

  /**
   * The entry whose row is asking "delete?", if any.
   *
   * An in-page step rather than the native `confirm()`, which blocks the
   * browser automation this app is smoke-tested with. Deleting is the one
   * control here that needs JavaScript; it is also the only one that destroys
   * something, so a version of this page with scripting off losing it is the
   * right way round.
   */
  let confirmDelete = $state('');

  /** @type {import('@sveltejs/kit').SubmitFunction} */
  const timeSubmit = () => {
    timeBusy = true;
    return async ({ update }) => {
      timeBusy = false;
      // `reset: false` keeps a rejected "log time" form filled in. Retyping
      // the description because the minutes were wrong is a small insult.
      await update({ reset: false });
    };
  };

  /**
   * The one thing that needs a person right now, said as the state it is.
   * Ember when the ball is in our court, rust when a target has already been
   * missed. Only "needs you" states earn a banner: a ticket waiting on the
   * customer is not blocked on us, so it stays a quiet line below, and a healthy
   * open ticket gets nothing at all.
   *
   * The mock had a `next_action` sentence telling the agent what to do; nothing
   * on `Case` supports inventing that, so this states the situation and stops.
   *
   * @type {{ tone: 'ember'|'rust', label: string, text: string } | null}
   */
  let alert = $derived.by(() => {
    if (!ticket.is_open) return null;
    if (!ticket.first_response_at) {
      return ticket.first_response_breached
        ? {
            tone: 'rust',
            label: $_('cases.detail.alert_first_reply_overdue_label'),
            text: $_('cases.detail.alert_first_reply_overdue_text')
          }
        : {
            tone: 'ember',
            label: $_('cases.detail.alert_needs_first_reply_label'),
            text: $_('cases.detail.alert_needs_first_reply_text')
          };
    }
    // Waiting on the customer is not something we can act on, so it is not a
    // banner. It falls through to the quiet line below.
    if (ticket.status === 'Pending') return null;
    if (!ticket.assignee) {
      return {
        tone: 'ember',
        label: $_('cases.detail.alert_no_owner_label'),
        text: $_('cases.detail.alert_no_owner_text')
      };
    }
    return null;
  });

  let waiting = $derived(
    ticket.is_open && ticket.status === 'Pending' && Boolean(ticket.first_response_at)
  );

  /**
   * The three SLA states, in the palette's own terms: rust for missed, clay
   * for the warning band ("aging_status yellow" is exactly what clay is for),
   * and ordinary text for on track. Breached wins, because the two are
   * exclusive server-side and a tie would mean a bug worth seeing as red.
   */
  function slaColor(breached, atRisk) {
    if (breached) return 'color:var(--v2-rust)';
    if (atRisk) return 'color:var(--v2-clay)';
    return '';
  }
</script>

<PageHeader title={ticket.name} record>
  {#snippet leading()}
    <!-- Whose ticket this is, at a glance. The account's mark where there is
         one; a ticket glyph where nobody is attached. -->
    {#if ticket.account}
      <Avatar name={ticket.account.name} size={42} />
    {:else}
      <span class="ticket-glyph" aria-hidden="true"><Ticket size={20} /></span>
    {/if}
  {/snippet}
  {#snippet crumb()}
    <a href={resolve('/tickets')}>{$_('cases.detail.breadcrumb_tickets')}</a>
    {#if ticket.account}
      <ChevronRight size={12} />
      <a href={resolve(`/accounts/${ticket.account.id}`)}>{ticket.account.name}</a>
    {/if}
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn" href={resolve(`/tickets/${ticket.id}/edit`)}
      ><Pencil size={12} />{$_('cases.detail.edit_button')}</a
    >
    {#if ticket.is_open}
      <form method="POST" action="?/setStatus" use:enhance style="display:contents">
        {#if ticket.status !== 'Pending'}
          <button class="v2-btn" name="status" value="Pending"
            >{$_('cases.detail.set_pending_button')}</button
          >
        {/if}
        {#if !data.close}
          <button class="v2-btn v2-btn-primary" name="status" value="Closed"
            >{$_('cases.detail.close_button')}</button
          >
        {/if}
      </form>
      <!-- A parent ticket closes through a confirm step, since the same click
           can close tickets belonging to other people. Outside the form above
           so this button never submits it. -->
      {#if data.close && !closePanel}
        <button class="v2-btn v2-btn-primary" type="button" onclick={openClosePanel}
          >{$_('cases.detail.close_button')}</button
        >
      {/if}
    {:else}
      <form method="POST" action="?/setStatus" use:enhance style="display:contents">
        <button class="v2-btn" name="status" value="New">{$_('cases.detail.reopen_button')}</button>
      </form>
    {/if}
  {/snippet}
</PageHeader>

<div style="display:flex;flex:1;min-height:0;overflow:hidden">
  <div class="v2-main">
    <div
      class="v2-pad"
      style="padding-top:12px;display:flex;gap:7px;align-items:center;flex-wrap:wrap;flex:none"
    >
      <Pill tone={PRIORITY_TONE[ticket.priority]}>{$_(casePriorityKey(ticket.priority))}</Pill>
      <Pill tone={CASE_STATUS_TONE[ticket.status]}>{$_(caseStatusKey(ticket.status))}</Pill>
      {#if ticket.case_type}<Pill tone="slate">{$_(caseTypeKey(ticket.case_type))}</Pill>{/if}
      <span class="v2-sub">
        <!-- There is no ticket number. `Case` has a UUID and a subject, so the
             subject is the identifier and the age is the useful fact. -->
        {$_('cases.detail.opened_ago', { values: { age: shortAge(ticket.opened_at) } })}
        {#if ticket.first_response_at}
          · {$_('cases.detail.first_reply_when', {
            values: { when: relativeTime(ticket.first_response_at) }
          })}
        {/if}
        {#if ticket.escalation_count > 0}
          · <span style="color:var(--v2-rust)"
            >{$_('cases.detail.escalated_count', {
              values: { count: ticket.escalation_count }
            })}</span
          >
        {/if}
      </span>
    </div>

    <div class="v2-scroll">
      <div class="v2-pad" style="padding-top:14px;padding-bottom:24px">
        {#if form?.error}
          <p
            class="v2-card"
            style="padding:10px 13px;margin-bottom:16px;color:var(--v2-rust);font-size:13px"
          >
            {form.error}
          </p>
        {/if}

        {#if form?.closed}
          <p class="v2-card" style="padding:10px 13px;margin-bottom:16px;font-size:13px">
            {form.closed}
          </p>
        {/if}

        <!--
          The confirm step for closing a parent. It names the tickets that go
          with it before anything happens, because they may belong to someone
          else and nobody is asked twice.

          The list is the subtree the API would actually close: open, active
          descendants of THIS ticket. Not the whole tree it sits in, which is
          what `/tree/` returns and what the earlier unwired version of this
          feature showed.
        -->
        {#if closePanel && data.close}
          {@const cs = cascadeSummary({
            count: data.close.descendants.length,
            truncated: data.close.truncated
          })}
          <div class="v2-card v2-close-panel">
            <form
              method="POST"
              action="?/closeWithChildren"
              use:enhance={() =>
                async ({ update }) => {
                  await update();
                  closePanel = false;
                }}
            >
              <div style="font-weight:600;font-size:13.5px">
                {$_('cases.detail.close_panel_title', { values: { name: ticket.name } })}
              </div>
              <p class="v2-sub" style="font-size:12.5px;margin:6px 0 0;line-height:1.5">
                {$_(cs.key, cs.values ? { values: cs.values } : {})}
              </p>

              {#if hasOpenChildren}
                <ul class="v2-close-list">
                  {#each data.close.descendants as child (child.id)}
                    <li>
                      <span class="v2-close-name">{child.name}</span>
                      <Pill tone={CASE_STATUS_TONE[child.status]}
                        >{$_(caseStatusKey(child.status))}</Pill
                      >
                    </li>
                  {/each}
                </ul>

                <label class="v2-close-check">
                  <input type="checkbox" name="cascade" bind:checked={cascade} />
                  <span>
                    <span style="font-weight:600">{$_('cases.detail.close_cascade_label')}</span>
                    <span class="v2-sub" style="display:block;font-size:11.5px;margin-top:2px">
                      {$_('cases.detail.close_cascade_hint')}
                    </span>
                  </span>
                </label>

                <div class="v2-field" style="margin-top:12px">
                  <label for="close-comment">{$_('cases.detail.close_reason_label')}</label>
                  <textarea
                    id="close-comment"
                    class="v2-input"
                    name="resolution_comment"
                    rows="2"
                    maxlength="1000"
                    placeholder={$_('cases.detail.close_reason_placeholder')}></textarea>
                </div>
              {/if}

              <div style="display:flex;gap:8px;margin-top:14px">
                <button class="v2-btn v2-btn-primary" type="submit">
                  {cascade
                    ? $_('cases.detail.close_submit_cascade')
                    : $_('cases.detail.close_submit_single')}
                </button>
                <button class="v2-btn" type="button" onclick={() => (closePanel = false)}>
                  {$_('cases.detail.cancel_button')}
                </button>
              </div>
            </form>
          </div>
        {/if}

        {#if alert}
          <div style="margin-bottom:18px">
            <NextAction label={alert.label} text={alert.text} tone={alert.tone} />
          </div>
        {:else if waiting}
          <p class="v2-sub" style="margin:0 0 18px;font-size:12.5px">
            {$_('cases.detail.waiting_on_customer')}
          </p>
        {/if}

        {#if ticket.description}
          <div class="v2-card" style="padding:13px 15px;margin-bottom:18px">
            <div class="v2-label" style="margin-bottom:7px">
              {$_('cases.detail.reported_label')}
            </div>
            <div style="font-size:13.5px;line-height:1.55;white-space:pre-wrap">
              {ticket.description}
            </div>
          </div>
        {/if}

        <!--
          Time on this ticket.

          Above the conversation rather than under it. The timer is what an
          agent reaches for on arriving, and a forty-message thread would
          otherwise sit between them and the button. Every control is a form
          post, so the panel works by keyboard and, apart from the delete
          confirm, without JavaScript at all; `enhance` only saves the reload.
        -->
        <section class="v2-card time-panel">
          <div class="time-head">
            <div class="time-title">
              <div class="v2-label">{$_('cases.detail.time_label')}</div>
              <div class="v2-sub time-total">
                {#if timeSummary?.total_minutes}
                  <b class="v2-num">{hm(timeSummary.total_minutes)}</b>
                  {$_('cases.detail.time_logged_suffix')}
                  {#if timeSummary.billable_minutes}
                    · {$_('cases.detail.time_billable_suffix', {
                      values: { amount: hm(timeSummary.billable_minutes) }
                    })}
                  {/if}
                {:else}
                  {$_('cases.detail.time_nothing_logged')}
                {/if}
              </div>
            </div>

            <!-- The person's own timer, and only theirs. An admin sees the
                 team's rows here, and stopping someone else's clock from a
                 button labelled "Stop" with no name on it is not something to
                 do by accident; that one is on its row. -->
            {#if myTimer}
              <form method="POST" action="?/stopTimer" use:enhance={timeSubmit} class="time-timer">
                <input type="hidden" name="entry_id" value={myTimer.id} />
                <button class="v2-btn v2-btn-primary" disabled={timeBusy}>
                  <Square size={12} />{$_('cases.detail.timer_stop_button', {
                    values: { elapsed: hm(runningMinutes(myTimer)) }
                  })}
                </button>
              </form>
            {:else}
              <form method="POST" action="?/startTimer" use:enhance={timeSubmit} class="time-timer">
                <button class="v2-btn" disabled={timeBusy}
                  ><Play size={12} />{$_('cases.detail.timer_start_button')}</button
                >
              </form>
            {/if}

            <!-- Native disclosure, so the form opens without JavaScript. Open,
                 it takes a row of its own rather than the button's column. -->
            <details class="time-log">
              <summary class="v2-btn"
                ><Plus size={12} />{$_('cases.detail.log_time_button')}</summary
              >
              <form method="POST" action="?/logTime" use:enhance={timeSubmit} class="time-log-form">
                <div class="v2-field">
                  <label for="time-minutes">{$_('cases.detail.log_minutes_label')}</label>
                  <input
                    id="time-minutes"
                    class="v2-input"
                    name="minutes"
                    type="number"
                    inputmode="numeric"
                    min="1"
                    max="1440"
                    step="1"
                    value="30"
                    required
                  />
                </div>
                <div class="v2-field">
                  <label for="time-rate">{$_('cases.detail.log_rate_label')}</label>
                  <input
                    id="time-rate"
                    class="v2-input"
                    name="hourly_rate"
                    type="number"
                    inputmode="decimal"
                    min="0"
                    step="0.01"
                    placeholder={$_('cases.detail.log_rate_placeholder')}
                  />
                </div>
                <div class="v2-field time-wide">
                  <label for="time-what">{$_('cases.detail.log_description_label')}</label>
                  <input
                    id="time-what"
                    class="v2-input"
                    name="description"
                    placeholder={$_('cases.detail.log_description_placeholder')}
                    required
                  />
                </div>
                <div class="time-wide time-log-foot">
                  <label class="time-check">
                    <input type="checkbox" name="billable" />
                    {$_('cases.detail.log_billable_label')}
                  </label>
                  <button class="v2-btn v2-btn-primary" disabled={timeBusy}
                    >{$_('cases.detail.log_time_submit')}</button
                  >
                </div>
                <p class="v2-hint time-wide">
                  {$_('cases.detail.log_time_hint')}
                </p>
              </form>
            </details>
          </div>

          {#if form?.timeError}
            <p class="v2-error time-error">
              <span>{form.timeError}</span>
              {#if form.runningTicketId}
                <a href={resolve(`/tickets/${form.runningTicketId}`)}
                  >{$_('cases.detail.time_open_that_ticket')}</a
                >
              {/if}
            </p>
          {/if}

          {#if entries === null}
            <p class="v2-sub time-empty">
              {$_('cases.detail.time_load_failed')}
            </p>
          {:else if entries.length === 0}
            <p class="v2-sub time-empty">
              {$_('cases.detail.time_none_yet')}
            </p>
          {:else}
            <div class="v2-table-wrap">
              <table class="v2-table">
                <thead>
                  <tr>
                    <th>{$_('cases.detail.time_col_what')}</th>
                    <th>{$_('cases.detail.time_col_who')}</th>
                    <th>{$_('cases.detail.time_col_when')}</th>
                    <th class="v2-r">{$_('cases.detail.time_col_logged')}</th>
                    <th class="v2-r">{$_('cases.detail.time_col_billing')}</th>
                  </tr>
                </thead>
                <tbody>
                  {#each entries as e (e.id)}
                    <tr>
                      <td data-m="title">
                        {e.description || $_('cases.detail.time_no_description')}
                        {#if !e.ended_at}<span class="time-running"
                            >{$_('cases.detail.time_running')}</span
                          >{/if}
                        {#if e.auto_stopped}
                          <span class="v2-sub" title={$_('cases.detail.time_auto_stopped_title')}
                            >{$_('cases.detail.time_auto_stopped')}</span
                          >
                        {/if}
                      </td>
                      <td data-m="meta">
                        {e.profile?.user_details?.name ||
                          e.profile?.user_details?.email ||
                          $_('cases.detail.time_someone')}
                      </td>
                      <td data-m="meta"
                        >{$_('cases.detail.time_ago', {
                          values: { age: shortAge(e.started_at) }
                        })}</td
                      >
                      <td class="v2-num v2-r" data-m="tag">
                        {e.ended_at ? hm(e.duration_minutes) : hm(runningMinutes(e))}
                      </td>
                      <td class="v2-r time-row-actions">
                        {#if !e.ended_at}
                          <form method="POST" action="?/stopTimer" use:enhance={timeSubmit}>
                            <input type="hidden" name="entry_id" value={e.id} />
                            <button class="v2-btn v2-btn-sm" disabled={timeBusy}>
                              <Square size={11} />{$_('cases.detail.time_stop_short')}
                            </button>
                          </form>
                        {:else if e.invoice}
                          <!-- Billed. The toggle and the delete are both gone:
                               the API refuses to delete an invoiced entry, and
                               flipping one to non-billable after it has been
                               charged for would leave the invoice standing. -->
                          <a class="v2-sub" href={resolve(`/invoices/${e.invoice}`)}
                            >{$_('cases.detail.time_invoiced')}</a
                          >
                        {:else if confirmDelete === e.id}
                          <form method="POST" action="?/deleteTime" use:enhance={timeSubmit}>
                            <input type="hidden" name="entry_id" value={e.id} />
                            <button class="v2-btn v2-btn-sm time-danger" disabled={timeBusy}>
                              {$_('cases.detail.time_delete')}
                            </button>
                          </form>
                          <button
                            type="button"
                            class="v2-btn v2-btn-sm"
                            onclick={() => (confirmDelete = '')}
                          >
                            {$_('cases.detail.time_keep')}
                          </button>
                        {:else}
                          <form method="POST" action="?/setBillable" use:enhance={timeSubmit}>
                            <input type="hidden" name="entry_id" value={e.id} />
                            <!-- The value to move to, decided when the row was
                                 rendered, so two quick clicks cannot both send
                                 "make it billable". -->
                            <input
                              type="hidden"
                              name="billable"
                              value={e.billable ? 'false' : 'true'}
                            />
                            <button
                              class="v2-btn v2-btn-sm"
                              class:time-billable={e.billable}
                              disabled={timeBusy}
                              title={e.billable
                                ? $_('cases.detail.time_mark_non_billable')
                                : $_('cases.detail.time_mark_billable')}
                            >
                              {#if e.billable}
                                {e.hourly_rate
                                  ? $_('cases.detail.time_rate_per_hour', {
                                      values: { rate: money(e.hourly_rate, e.currency) }
                                    })
                                  : $_('cases.detail.time_billable')}
                              {:else}
                                {$_('cases.detail.time_not_billable')}
                              {/if}
                            </button>
                          </form>
                          <button
                            type="button"
                            class="v2-btn v2-btn-sm"
                            aria-label={$_('cases.detail.time_delete_entry_title')}
                            title={$_('cases.detail.time_delete_entry_title')}
                            onclick={() => (confirmDelete = e.id)}
                          >
                            <Trash2 size={11} />
                          </button>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>

        {#if conversation.length === 0}
          <p class="v2-sub" style="margin:0 0 18px;font-size:12.5px">
            {$_('cases.detail.conversation_empty')}
          </p>
        {/if}

        {#each conversation as m (m.id)}
          {#if m.direction === 'note'}
            <!-- An internal note is not part of the conversation with the
                 customer, so it does not sit on either side of it. -->
            <div
              class="v2-card"
              style="padding:11px 13px;margin-bottom:14px;border-style:dashed;background:transparent"
            >
              <div
                class="v2-sub"
                style="font-size:11.5px;margin-bottom:5px;display:flex;align-items:center;gap:5px"
              >
                <Lock size={11} />
                <b style="color:var(--v2-ink);font-weight:600">{m.author}</b>
                · {$_('cases.detail.msg_internal_note')} · {$_('cases.detail.ago', {
                  values: { age: shortAge(m.at) }
                })}
              </div>
              <div style="font-size:13.5px;line-height:1.55;white-space:pre-wrap">{m.body}</div>
            </div>
          {:else}
            <div
              style="display:flex;gap:12px;margin-bottom:14px;{m.direction === 'out'
                ? 'flex-direction:row-reverse'
                : ''}"
            >
              <Avatar name={m.author} size={30} />
              <div
                class="v2-card"
                style="padding:12px 14px;max-width:72%;{m.direction === 'out'
                  ? 'background:var(--v2-line-soft)'
                  : ''}"
              >
                <div class="v2-sub" style="font-size:11.5px;margin-bottom:5px">
                  <b style="color:var(--v2-ink);font-weight:600">{m.author}</b>
                  {#if m.kind === 'email'}· {$_('cases.detail.msg_email')}{/if}
                  · {$_('cases.detail.ago', { values: { age: shortAge(m.at) } })}
                </div>
                {#if m.subject}
                  <div style="font-size:12.5px;font-weight:600;margin-bottom:4px">{m.subject}</div>
                {/if}
                <div style="font-size:13.5px;line-height:1.55;white-space:pre-wrap">{m.body}</div>
              </div>
            </div>
          {/if}
        {/each}

        {#if canReply}
          <form method="POST" action="?/reply" enctype="multipart/form-data" use:enhance={send}>
            <div class="v2-card" style="padding:13px 14px;margin-top:18px">
              <textarea
                name="body"
                bind:value={body}
                rows="3"
                placeholder={internal
                  ? $_('cases.detail.composer_placeholder_note')
                  : $_('cases.detail.composer_placeholder_reply')}
                style="width:100%;border:none;background:transparent;resize:vertical;font:inherit;font-size:13.5px;line-height:1.55;color:var(--v2-ink);outline:none"
              ></textarea>
              <div
                style="display:flex;gap:9px;align-items:center;border-top:1px solid var(--v2-line);padding-top:12px;flex-wrap:wrap"
              >
                <label
                  class="v2-sub"
                  style="display:flex;align-items:center;gap:5px;font-size:12px;cursor:pointer"
                >
                  <input type="checkbox" name="internal" bind:checked={internal} />
                  {$_('cases.detail.composer_internal_note')}
                </label>
                <!-- The whole chip is the click target: a label wrapping a hidden
                     input. A file may ride with the reply or go on its own. -->
                <label class="attach" class:has-file={fileName}>
                  <Paperclip size={13} />
                  <span class="attach-label">{fileName || $_('cases.detail.composer_attach')}</span>
                  <input
                    bind:this={fileInput}
                    type="file"
                    name="attachment"
                    onchange={pickFile}
                    hidden
                  />
                </label>
                {#if fileName}
                  <button
                    type="button"
                    class="clear-file"
                    onclick={clearFile}
                    title={$_('cases.detail.composer_remove_file')}
                  >
                    <X size={12} />
                  </button>
                {/if}
                <span class="v2-sub" style="margin-left:auto;font-size:11.5px"
                  >{$_('cases.detail.composer_status_on_send')}</span
                >
                <!-- Answering and moving the ticket is one decision, so it is
                     one submit. Empty means "leave the status alone". -->
                <select name="status" class="v2-input" style="width:auto;font-size:12px">
                  <option value="">{$_('cases.detail.composer_status_unchanged')}</option>
                  <option value="Assigned">{$_(caseStatusKey('Assigned'))}</option>
                  <option value="Pending">{$_(caseStatusKey('Pending'))}</option>
                </select>
                <button class="v2-btn v2-btn-primary" disabled={sending || !canSend}>
                  {sending
                    ? $_('cases.detail.composer_sending')
                    : body.trim()
                      ? internal
                        ? $_('cases.detail.composer_add_note')
                        : $_('cases.detail.composer_send_reply')
                      : fileName
                        ? $_('cases.detail.composer_attach_file')
                        : internal
                          ? $_('cases.detail.composer_add_note')
                          : $_('cases.detail.composer_send_reply')}
                </button>
              </div>
            </div>
            {#if internal}
              <p class="v2-sub" style="margin:8px 2px 0;font-size:11.5px">
                {$_('cases.detail.composer_note_hint')}
              </p>
            {/if}
          </form>
        {:else}
          <p class="v2-sub" style="margin-top:18px;font-size:12.5px">
            {$_('cases.detail.cannot_reply')}
          </p>
        {/if}
      </div>
    </div>
  </div>

  <aside class="v2-rail">
    <div class="v2-label v2-rail-head">{$_('cases.detail.rail_ticket_label')}</div>
    <dl class="v2-kv">
      <dt>{$_('cases.detail.rail_priority')}</dt>
      <dd>
        <Pill tone={PRIORITY_TONE[ticket.priority]}>{$_(casePriorityKey(ticket.priority))}</Pill>
      </dd>
      <dt>{$_('cases.detail.rail_status')}</dt>
      <dd>
        <Pill tone={CASE_STATUS_TONE[ticket.status]}>{$_(caseStatusKey(ticket.status))}</Pill>
      </dd>
      <dt>{$_('cases.detail.rail_type')}</dt>
      <dd>
        {ticket.case_type ? $_(caseTypeKey(ticket.case_type)) : $_('cases.detail.rail_not_set')}
      </dd>
      <dt>{$_('cases.detail.rail_assignee')}</dt>
      <dd>
        {ticket.assignee ?? $_('cases.detail.rail_unassigned')}
        {#if ticket.assignee_count > 1}
          <span class="v2-sub">+{ticket.assignee_count - 1}</span>
        {/if}
      </dd>
      <dt>{$_('cases.detail.rail_opened')}</dt>
      <dd>{longDate(ticket.opened_at)}</dd>
      <dt>{$_('cases.detail.rail_first_reply')}</dt>
      <dd>
        {#if ticket.first_response_at}
          {relativeTime(ticket.first_response_at)}
        {:else if ticket.first_response_deadline}
          <span style={slaColor(ticket.first_response_breached, ticket.first_response_at_risk)}>
            {$_('cases.detail.rail_due_when', {
              values: { when: relativeTime(ticket.first_response_deadline) }
            })}
          </span>
        {:else}
          {$_('cases.detail.rail_no_target')}
        {/if}
      </dd>
      {#if ticket.resolved_at}
        <dt>{$_('cases.detail.rail_resolved')}</dt>
        <dd>{longDate(ticket.resolved_at)}</dd>
      {:else if ticket.resolution_deadline}
        <dt>{$_('cases.detail.rail_resolve_by')}</dt>
        <dd>
          <span style={slaColor(ticket.resolution_breached, ticket.resolution_at_risk)}>
            {relativeTime(ticket.resolution_deadline)}
          </span>
        </dd>
      {/if}
      {#if ticket.paused_at}
        <dt>{$_('cases.detail.rail_sla')}</dt>
        <dd>{$_('cases.detail.rail_sla_paused')}</dd>
      {/if}
    </dl>

    {#if ticket.account}
      <div class="v2-label v2-rail-head">{$_('cases.detail.rail_account_label')}</div>
      <a
        class="v2-rail-row"
        href={resolve(`/accounts/${ticket.account.id}`)}
        style="color:inherit;text-decoration:none"
      >
        <Avatar name={ticket.account.name} size={29} />
        <div>
          <div style="font-size:12.5px;font-weight:550">{ticket.account.name}</div>
          <div class="v2-sub" style="font-size:11px">
            {#if contacts.length === 1}
              {$_('cases.detail.rail_reported_by', { values: { name: contacts[0].name } })}
            {:else if contacts.length > 1}
              {$_('cases.detail.rail_people_count', { values: { count: contacts.length } })}
            {:else}
              {$_('cases.detail.rail_nobody_named')}
            {/if}
          </div>
        </div>
      </a>
    {/if}

    {#if contacts.length}
      <div class="v2-label v2-rail-head">{$_('cases.detail.rail_people_label')}</div>
      {#each contacts as c (c.id)}
        <a
          class="v2-rail-row"
          href={resolve(`/contacts/${c.id}`)}
          style="color:inherit;text-decoration:none"
        >
          <Avatar name={c.name} size={26} />
          <div style="font-size:12.5px;font-weight:550">{c.name}</div>
        </a>
      {/each}
    {/if}

    {#if articles.length}
      <!-- Articles filed against this ticket, not keyword guesses. The mock
           called these "suggested"; suggestions are a different endpoint. -->
      <div class="v2-label v2-rail-head">{$_('cases.detail.rail_articles_label')}</div>
      {#each articles as a (a.id)}
        <a
          class="v2-rail-row"
          href={resolve(`/solutions/${a.id}`)}
          style="color:inherit;text-decoration:none"
        >
          <div>
            <div style="font-size:12.5px;font-weight:550;line-height:1.35">{a.title}</div>
            <div class="v2-sub" style="font-size:11px">
              {a.is_published
                ? $_('cases.detail.rail_article_published')
                : $_('cases.detail.rail_article_unpublished')} · {$_(
                'cases.detail.rail_article_updated',
                { values: { when: relativeDays(a.updated_at) } }
              )}
            </div>
          </div>
        </a>
      {/each}
    {/if}

    {#if attachments.length}
      <div class="v2-label v2-rail-head">{$_('cases.detail.rail_attachments_label')}</div>
      {#each attachments as f (f.id)}
        {#if f.url}
          <!-- A download now, not dead text: the path was always in the payload
               and the rail simply never linked it. -->
          <a
            class="v2-rail-row att"
            href={f.url}
            target="_blank"
            rel="external noreferrer noopener"
            style="color:inherit;text-decoration:none"
          >
            <Paperclip size={13} />
            <div style="font-size:12.5px;font-weight:550;overflow-wrap:anywhere">{f.name}</div>
          </a>
        {:else}
          <div class="v2-rail-row">
            <Paperclip size={13} />
            <div style="font-size:12.5px;font-weight:550;overflow-wrap:anywhere">{f.name}</div>
          </div>
        {/if}
      {/each}
    {/if}

    {#if alsoOpen.length}
      <div class="v2-label v2-rail-head">{$_('cases.detail.rail_also_open_label')}</div>
      {#each alsoOpen as t (t.id)}
        <a
          class="v2-rail-row"
          href={resolve(`/tickets/${t.id}`)}
          style="color:inherit;text-decoration:none"
        >
          <div>
            <div style="font-size:12.5px;font-weight:550;line-height:1.35">{t.name}</div>
            <div class="v2-sub" style="font-size:11px">
              {$_(casePriorityKey(t.priority))} · {$_('cases.detail.rail_age_old', {
                values: { age: shortAge(t.opened_at) }
              })}
            </div>
          </div>
        </a>
      {/each}
    {/if}

    {#if activity.length}
      <div class="v2-label v2-rail-head">{$_('cases.detail.rail_history_label')}</div>
      {#each activity.slice(0, 8) as a (a.id)}
        <div class="v2-rail-row">
          <div>
            <div style="font-size:12.5px;font-weight:550;line-height:1.35">{a.label}</div>
            <div class="v2-sub" style="font-size:11px">
              {a.by ?? $_('cases.detail.rail_system')} · {$_('cases.detail.ago', {
                values: { age: shortAge(a.at) }
              })}
            </div>
          </div>
        </div>
      {/each}
    {/if}
  </aside>
</div>

<style>
  /* The confirm step for closing a parent. Everything in it stacks, so it
     holds at 390px without a media query of its own. */
  .v2-close-panel {
    padding: 15px 16px;
    margin-bottom: 18px;
  }
  .v2-close-list {
    list-style: none;
    margin: 10px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 180px;
    overflow-y: auto;
  }
  .v2-close-list li {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    font-size: 12.5px;
  }
  /* The name truncates and the status pill never does: which tickets these are
     matters less than the fact that they are open. */
  .v2-close-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .v2-close-check {
    display: flex;
    gap: 9px;
    align-items: flex-start;
    margin-top: 13px;
    font-size: 12.5px;
    cursor: pointer;
  }
  .v2-close-check input {
    margin-top: 2px;
    flex: none;
  }

  /* Identity mark for a ticket that has no account to show a face for. */
  .ticket-glyph {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: var(--v2-line-soft);
    border: 1px solid var(--v2-line);
    color: var(--v2-slate);
  }

  /* The composer's attach control, sized to sit in the action row beside the
     Internal-note toggle. */
  .attach {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 9px;
    font-size: 12px;
    color: var(--v2-slate);
    border: 1px solid var(--v2-line);
    border-radius: 7px;
    cursor: pointer;
  }
  .attach:hover,
  .attach.has-file {
    color: var(--v2-ink);
    border-color: var(--v2-slate);
  }
  .attach .attach-label {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .clear-file {
    display: grid;
    place-items: center;
    padding: 4px;
    border: none;
    background: transparent;
    color: var(--v2-slate);
    cursor: pointer;
    border-radius: 6px;
  }
  .clear-file:hover {
    color: var(--v2-rust);
    background: var(--v2-hover);
  }

  /* The whole attachment row lifts slightly on hover to read as a download. */
  .att:hover {
    background: var(--v2-hover);
  }

  /* ── time panel ─────────────────────────────────────────────────────── */
  .time-panel {
    margin-bottom: 18px;
    padding: 13px 15px;
  }
  .time-head {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    flex-wrap: wrap;
  }
  /* Pushes the two controls to the right without either of them owning a
     margin, so they stay put when the disclosure below drops to its own row. */
  .time-title {
    margin-right: auto;
  }
  .time-total {
    font-size: 12.5px;
    margin-top: 3px;
  }
  /* The summary is the button; the default triangle would sit inside it. */
  .time-log > summary {
    list-style: none;
    cursor: pointer;
  }
  .time-log > summary::-webkit-details-marker {
    display: none;
  }
  .time-log[open] > summary {
    border-color: var(--v2-slate);
  }
  /* Open, the disclosure claims the whole row: a two-column form inside a
     button-width column would be two columns of nothing. Closed, it is just
     the button and sits beside Start. */
  .time-log[open] {
    flex: 1 0 100%;
  }
  .time-log-form {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 12px;
    padding-top: 13px;
    border-top: 1px solid var(--v2-line);
  }
  .time-wide {
    grid-column: 1 / -1;
  }
  .time-log-form .v2-field {
    margin-bottom: 0;
  }
  .time-log-foot {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .time-check {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    cursor: pointer;
  }
  .time-log-form .v2-hint {
    margin: 0;
  }
  .time-error {
    margin: 12px 0 0;
    gap: 8px;
    flex-wrap: wrap;
  }
  .time-empty {
    font-size: 12.5px;
    margin: 12px 0 2px;
  }
  .time-panel .v2-table-wrap {
    margin: 12px -15px -13px;
    border: 0;
  }
  .time-running {
    color: var(--v2-ember);
    font-size: 11.5px;
    font-weight: 600;
    margin-left: 6px;
  }
  .time-row-actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
    align-items: center;
  }
  .time-billable {
    color: var(--v2-moss);
    border-color: color-mix(in srgb, var(--v2-moss) 40%, transparent);
  }
  .time-danger {
    color: var(--v2-rust);
    border-color: color-mix(in srgb, var(--v2-rust) 40%, transparent);
  }

  @media (max-width: 768px) {
    /* One field per line, and both controls full width: two half-width
       buttons at the top of a 390px card are two small targets. */
    .time-log-form {
      grid-template-columns: 1fr;
    }
    .time-title,
    .time-timer,
    .time-log {
      flex: 1 0 100%;
    }
    .time-timer .v2-btn,
    .time-log > summary {
      width: 100%;
      justify-content: center;
      min-height: 44px;
    }
    /* A row's controls are the smallest things on the panel and the ones
       pressed with a thumb, so they get 44px in both directions, the delete
       button included: it holds an icon and nothing else, and 12px of padding
       around a 11px trash can is a 40px target. */
    .time-row-actions {
      justify-content: flex-start;
      margin-top: 8px;
    }
    .time-row-actions .v2-btn {
      min-height: 44px;
      min-width: 44px;
      padding-inline: 12px;
    }
    .time-log-form .v2-btn,
    .time-check {
      min-height: 44px;
    }
  }
</style>
