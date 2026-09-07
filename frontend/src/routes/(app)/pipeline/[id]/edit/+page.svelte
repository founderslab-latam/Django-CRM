<script>
  import { resolve } from '$app/paths';
  /**
   * Editing a deal.
   *
   * Three fields on this form are not what they appear to be, and all three
   * were found by reading `opportunity/models.py` rather than v1's edit page,
   * which offers Amount, Stage and Close date as three plain inputs with no
   * indication that any of them behaves specially.
   *
   * ── AMOUNT IS NOT ALWAYS YOURS TO SET ────────────────────────────────────
   * `Opportunity.recalculate_amount()` sets `amount = SUM(line_items.total)`
   * and flips `amount_source` to CALCULATED whenever any line items exist. A
   * number typed here is then discarded on the next recalculation. So when
   * the deal has line items the input is disabled and says why, instead of
   * accepting a value that will not survive.
   *
   * ── STAGE RESETS A CLOCK SOMEBODY ELSE IS WATCHING ───────────────────────
   * `Opportunity.save()` sets `stage_changed_at = now()` on any stage change,
   * and `stage_changed_at` is what `days_in_current_stage` and
   * `get_aging_status()` are computed from. The pipeline board colours every
   * card by that status. Moving a stage therefore turns a stalled deal green
   *, not because anything improved, but because the clock restarted. That is
   * a legitimate thing to do and an illegitimate thing to do by accident, so
   * the form shows the number that is about to be discarded.
   *
   * ── CLOSING REQUIRES MORE THAN PICKING "CLOSED" ──────────────────────────
   * A closed stage needs `closed_on`, and CLOSED_WON needs `amount`. Both are
   * mirrored below so the requirement appears when you pick the stage rather
   * than after you submit.
   *
   * `Opportunity.clean()` declares both, but DRF never calls `clean()`, so
   * until this module was wired the API accepted a won deal worth nothing with
   * no close date, and only the model's unit tests knew otherwise. They are
   * enforced in `OpportunityCreateSerializer.validate()` now. The rule below is
   * still only a hint; the serializer is what decides.
   *
   * NOT ON THIS FORM, because the server owns them: `amount_source`,
   * `stage_changed_at`, `closed_by`, `kanban_order`, `org`, `created_by`.
   * The amount input is `disabled` when line items own it, and a disabled
   * control submits nothing, which is exactly what PATCH needs, since absent
   * means "leave it alone".
   */
  import { tick, untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import { opportunityStageKey } from '$lib/opportunity/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import { STAGES, OPPORTUNITY_TYPE_LABEL, AGING_TONE, AGING_LABEL } from '$lib/v2/enums.js';
  import { money, longDate } from '$lib/v2/format.js';
  import { ChevronRight, TriangleAlert, Lock } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  /* Read once, on purpose. `originalStage` has to stay the stage this form
     opened on. That is what "the clock is about to reset" is measured
     against, and a revalidation must not quietly redefine it. */
  const { deal, server, originalStage } = untrack(() => ({
    deal: data.deal,
    server: data.server,
    originalStage: data.deal.stage
  }));

  let form = $state(untrack(() => ({ ...data.form })));
  // The deal's people. Held apart from `form` so the `<select multiple>` binds
  // to a plain array; synced back via the `contacts_present` marker.
  let selectedContacts = $state(untrack(() => [...(data.form.contacts ?? [])]));
  let touched = $state(/** @type {Record<string, boolean>} */ ({}));
  let submitted = $state(false);
  let saved = $state(false);

  const amountIsCalculated = server.amount_source === 'CALCULATED';

  let isClosed = $derived(form.stage.startsWith('CLOSED_'));
  let isClosedWon = $derived(form.stage === 'CLOSED_WON');
  let stageChanged = $derived(form.stage !== originalStage);

  let errors = $derived.by(() => {
    /** @type {Record<string, string>} */
    const e = {};
    if (!form.name.trim()) e.name = $_('opportunity.edit.error_name_required');
    if (!form.account) e.account = $_('opportunity.edit.error_account_required');

    /* Only validate what the form can actually send. When the amount is
       server-calculated the input is disabled, so a complaint about it would
       be a complaint about something nobody can fix here. */
    if (!amountIsCalculated) {
      const n = Number(form.amount);
      if (form.amount === '' || form.amount === null) {
        if (isClosedWon) e.amount = $_('opportunity.edit.error_amount_required_won');
      } else if (!Number.isFinite(n)) e.amount = $_('opportunity.edit.error_amount_not_number');
      else if (n < 0) e.amount = $_('opportunity.edit.error_amount_negative');
      else if (n === 0 && isClosedWon) e.amount = $_('opportunity.edit.error_amount_required_won');
    }

    if (isClosed && !form.closed_on)
      e.closed_on = $_('opportunity.edit.error_closed_on_required', {
        values: { stageLabel: $_(opportunityStageKey(form.stage)) }
      });

    const p = Number(form.probability);
    if (form.probability !== '' && (!Number.isFinite(p) || p < 0 || p > 100))
      e.probability = $_('opportunity.edit.error_probability_range');

    return e;
  });

  let valid = $derived(Object.keys(errors).length === 0);
  const show = (field) => (touched[field] || submitted) && errors[field];

  /**
   * Stop the submit when this form's own checks fail, and send focus to the
   * first field that needs work. On a long form the error can be off screen.
   * `await tick()` matters: on the first submit the aria-invalid attributes do
   * not exist until Svelte flushes, so querying now would find nothing.
   *
   * These checks are a UX hint. The serializer is the rule, and its 400 is
   * what `result.error` below reports.
   *
   * @type {import('./$types').SubmitFunction}
   */
  const check = async ({ cancel }) => {
    submitted = true;
    saved = false;
    if (!valid) {
      cancel();
      await tick();
      /** @type {HTMLElement | null} */
      const first = document.querySelector('[aria-invalid="true"]');
      first?.focus();
      return;
    }
    return async ({ update, result: outcome }) => {
      // reset:false keeps what was typed when the server rejects it.
      await update({ reset: false });
      saved = outcome.type === 'success';
    };
  };
</script>

<PageHeader title={$_('opportunity.edit.title', { values: { name: deal.name } })} center>
  {#snippet crumb()}
    <a href={resolve('/pipeline')}>{$_('opportunity.edit.breadcrumb_pipeline')}</a>
    <ChevronRight size={12} />
    <a href={resolve(`/pipeline/${deal.id}`)}>{deal.name}</a>
  {/snippet}
  {#snippet sub()}
    {deal.account.name} · <span class="v2-num">{money(deal.amount, deal.currency)}</span> ·
    {$_('opportunity.edit.stage_duration', {
      values: {
        stageLabel: $_(opportunityStageKey(originalStage)),
        days: server.days_in_current_stage
      }
    })}
  {/snippet}
</PageHeader>

<div class="v2-scroll v2-pad" style="padding-top:18px">
  <form class="v2-form" method="POST" action="?/save" use:enhance={check} novalidate>
    {#if saved}
      <div class="v2-next" style="margin-bottom:18px" role="status">
        <div class="v2-next-body">
          <div class="v2-next-text">{$_('opportunity.edit.saved_heading')}</div>
          <div class="v2-sub" style="margin-top:3px">
            {$_('opportunity.edit.saved_detail', { values: { name: deal.name } })}
          </div>
        </div>
        <a class="v2-btn" href={resolve(`/pipeline/${deal.id}`)}
          >{$_('opportunity.edit.back_to_deal_button')}</a
        >
      </div>
    {/if}

    {#if result?.error}
      <div
        class="v2-next"
        style="background:color-mix(in srgb, var(--v2-rust) 9%, transparent);border-color:color-mix(in srgb, var(--v2-rust) 28%, transparent);margin-bottom:18px"
        role="alert"
      >
        <TriangleAlert size={17} style="color:var(--v2-rust);flex:none" />
        <div class="v2-next-body">
          <div style="font-weight:600">{$_('opportunity.edit.server_error_heading')}</div>
          <div class="v2-sub" style="margin-top:2px">{result.error}</div>
        </div>
      </div>
    {/if}

    {#if submitted && !valid}
      <div
        class="v2-next"
        style="background:color-mix(in srgb, var(--v2-rust) 9%, transparent);border-color:color-mix(in srgb, var(--v2-rust) 28%, transparent);margin-bottom:18px"
        role="alert"
      >
        <TriangleAlert size={17} style="color:var(--v2-rust);flex:none" />
        <div class="v2-next-body">
          <div style="font-weight:600">
            {$_('opportunity.edit.validation_heading', {
              values: { count: Object.keys(errors).length }
            })}
          </div>
          <div class="v2-sub" style="margin-top:2px">
            {$_('opportunity.edit.validation_detail')}
          </div>
        </div>
      </div>
    {/if}

    <div class="v2-field">
      <label for="f-name">{$_('opportunity.edit.label_name')}</label>
      <input
        id="f-name"
        name="name"
        class="v2-input"
        bind:value={form.name}
        onblur={() => (touched.name = true)}
        aria-invalid={show('name') ? 'true' : undefined}
      />
      {#if show('name')}<p class="v2-error">{errors.name}</p>{/if}
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-account">{$_('opportunity.edit.label_account')}</label>
        <select
          id="f-account"
          name="account"
          class="v2-input"
          bind:value={form.account}
          aria-invalid={show('account') ? 'true' : undefined}
        >
          {#each data.accounts as a (a.id)}
            <option value={a.id}>{a.name}</option>
          {/each}
        </select>
        {#if show('account')}<p class="v2-error">{errors.account}</p>{/if}
      </div>
      <div class="v2-field">
        <label for="f-type">{$_('opportunity.edit.label_type')}</label>
        <select
          id="f-type"
          name="opportunity_type"
          class="v2-input"
          bind:value={form.opportunity_type}
        >
          {#each Object.entries(OPPORTUNITY_TYPE_LABEL) as [key, label] (key)}
            <option value={key}>{label}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="v2-field">
      <label for="f-contacts">{$_('opportunity.edit.label_contacts')}</label>
      <select
        id="f-contacts"
        name="contacts"
        class="v2-input"
        multiple
        size="4"
        bind:value={selectedContacts}
      >
        {#each data.contacts as c (c.id)}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
      <input type="hidden" name="contacts_present" value="1" />
      <p class="v2-hint">{$_('opportunity.edit.hint_contacts')}</p>
    </div>

    <div class="v2-field">
      <label for="f-stage">{$_('opportunity.edit.label_stage')}</label>
      <select
        id="f-stage"
        name="stage"
        class="v2-input"
        bind:value={form.stage}
        aria-describedby={stageChanged ? 'stage-effect' : undefined}
      >
        {#each STAGES as s (s)}
          <option value={s}>{$_(opportunityStageKey(s))}</option>
        {/each}
      </select>

      <!--
        The cost of the change, shown before it is made. `days_in_current_stage`
        and the aging pill on the board are both derived from stage_changed_at,
        which save() resets, so this is the number that is about to disappear.
      -->
      {#if stageChanged}
        <div class="consequence" style="--edge:var(--v2-clay)" id="stage-effect">
          <div style="font-weight:600">
            {$_(opportunityStageKey(originalStage))} → {$_(opportunityStageKey(form.stage))}
          </div>
          <p>
            {$_('opportunity.edit.stage_change_intro')}
            <Pill tone={AGING_TONE[server.aging_status]} dot>
              {$_('opportunity.edit.stage_change_days', {
                values: {
                  agingLabel: AGING_LABEL[server.aging_status],
                  days: server.days_in_current_stage
                }
              })}
            </Pill>
            {$_('opportunity.edit.stage_change_outro')}
          </p>
        </div>
      {/if}
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-amount">
          {$_('opportunity.edit.label_amount')}
          {#if amountIsCalculated}<span class="locked"
              ><Lock size={10} />{$_('opportunity.edit.label_amount_locked_badge')}</span
            >{/if}
        </label>
        <input
          id="f-amount"
          name="amount"
          class="v2-input v2-num"
          type="text"
          inputmode="decimal"
          disabled={amountIsCalculated}
          value={amountIsCalculated ? server.line_item_total : form.amount}
          oninput={(e) => (form.amount = e.currentTarget.value)}
          onblur={() => (touched.amount = true)}
          aria-invalid={show('amount') ? 'true' : undefined}
          aria-describedby={amountIsCalculated ? 'h-amount' : undefined}
        />
        {#if show('amount')}
          <p class="v2-error">{errors.amount}</p>
        {:else if amountIsCalculated}
          <p class="v2-hint" id="h-amount">
            <a href={resolve(`/pipeline/${deal.id}`)}
              >{$_('opportunity.edit.hint_amount_locked_link', {
                values: { count: server.line_item_count }
              })}</a
            >
            {$_('opportunity.edit.hint_amount_locked_middle', {
              values: { count: server.line_item_count }
            })}
            <span class="v2-num">{money(server.line_item_total, deal.currency)}</span>{$_(
              'opportunity.edit.hint_amount_locked_tail'
            )}
          </p>
        {:else}
          <p class="v2-hint">
            {$_('opportunity.edit.hint_amount_manual')}
          </p>
        {/if}
      </div>

      <div class="v2-field">
        <label for="f-prob">{$_('opportunity.edit.label_probability')}</label>
        <input
          id="f-prob"
          name="probability"
          class="v2-input v2-num"
          type="text"
          inputmode="numeric"
          bind:value={form.probability}
          onblur={() => (touched.probability = true)}
          aria-invalid={show('probability') ? 'true' : undefined}
        />
        {#if show('probability')}<p class="v2-error">{errors.probability}</p>{/if}
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-closed">
          {isClosed
            ? $_('opportunity.edit.label_closed_on')
            : $_('opportunity.edit.label_expected_close')}
          {#if isClosed}<span class="req">{$_('opportunity.edit.label_required_badge')}</span>{/if}
        </label>
        <input
          id="f-closed"
          name="closed_on"
          class="v2-input"
          type="date"
          bind:value={form.closed_on}
          onblur={() => (touched.closed_on = true)}
          aria-invalid={show('closed_on') ? 'true' : undefined}
        />
        {#if show('closed_on')}
          <p class="v2-error">{errors.closed_on}</p>
        {:else if isClosed}
          <p class="v2-hint">{$_('opportunity.edit.hint_closed_on')}</p>
        {/if}
      </div>
      <div class="v2-field">
        <label for="f-owner">{$_('opportunity.edit.label_owner')}</label>
        <!-- What the select was rendered with. The action compares against it
             so an untouched owner is not sent at all; `assigned_to` is a
             many-to-many and this select is single, so sending it always would
             cut a two-person deal down to one on every save. -->
        <input type="hidden" name="assigned_to_original" value={data.form.assigned_to} />
        <select id="f-owner" name="assigned_to" class="v2-input" bind:value={form.assigned_to}>
          <option value="">{$_('opportunity.edit.option_nobody')}</option>
          {#each data.owners as o (o.id)}
            <!-- The value is the Profile id. The mock used the display name,
                 which looks identical on screen and cannot be saved. -->
            <option value={o.id}>{o.name}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="v2-field">
      <label for="f-source">{$_('opportunity.edit.label_lead_source')}</label>
      <input id="f-source" name="lead_source" class="v2-input" bind:value={form.lead_source} />
    </div>

    <div class="v2-field">
      <label for="f-notes">{$_('opportunity.edit.label_notes')}</label>
      <textarea
        id="f-notes"
        name="description"
        class="v2-input"
        rows="4"
        bind:value={form.description}></textarea>
    </div>

    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit"
        >{$_('opportunity.edit.submit_button')}</button
      >
      <a class="v2-btn" href={resolve(`/pipeline/${deal.id}`)}
        >{$_('opportunity.edit.cancel_button')}</a
      >
      <span class="v2-sub" style="margin-left:auto;font-size:12px">
        {$_('opportunity.edit.last_stage_change_prefix')}
        {longDate(server.stage_changed_at)}
      </span>
    </div>
  </form>
</div>

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .req,
  .locked {
    margin-left: 6px;
    font-size: 10px;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--v2-clay);
  }
  .locked {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    color: var(--v2-slate);
  }
  .consequence {
    border-left: 2px solid var(--edge);
    padding: 2px 0 2px 12px;
    margin-top: 8px;
  }
  .consequence p {
    margin: 4px 0 0;
    font-size: 13px;
    color: var(--v2-slate);
    max-width: 62ch;
    line-height: 1.55;
  }
  .actions {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 22px;
  }
  @media (max-width: 720px) {
    .pair {
      grid-template-columns: 1fr;
    }
    .actions span {
      display: none;
    }
  }
</style>
