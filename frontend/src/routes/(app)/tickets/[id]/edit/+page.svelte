<script>
  import { resolve } from '$app/paths';
  /**
   * Editing a ticket.
   *
   * Two things this form deliberately does not offer, and says so rather than
   * showing a control that quietly does nothing:
   *
   * - **Account.** `CaseCreateSerializer` marks `account` read-only as soon as
   *   there is an instance, so a select here would be ignored by the API.
   * - **Teams and tags.** They are many-to-many and this form has no editor for
   *   them; the save is a PATCH, which leaves any relation it does not mention
   *   alone. The counts are shown so it is clear what is being preserved.
   */
  import { tick, untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { ChevronRight, TriangleAlert } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  let ticket = $derived(data.ticket);

  // `untrack` so a re-render after a failed save does not throw away what the
  // person typed; `result.values` is the server's echo of the same fields.
  let form = $state(
    untrack(() => ({
      ...data.form,
      ...(result?.values ?? {})
    }))
  );
  let contacts = $state(untrack(() => [...(data.form.contacts ?? [])]));
  let touched = $state(/** @type {Record<string, boolean>} */ ({}));
  let submitted = $state(false);

  let errors = $derived.by(() => {
    /** @type {Record<string, string>} */
    const e = {};
    const name = (form.name ?? '').trim();
    if (!name) e.name = $_('cases.edit.error_name_required');
    else if (name.length > 64)
      e.name = $_('cases.edit.error_name_too_long', { values: { length: name.length } });

    // Mirrors the serializer rule exactly, so the refusal happens at the field
    // rather than as an opaque whole-form rejection after the save.
    if (form.status === 'Closed' && !form.closed_on)
      e.closed_on = $_('cases.edit.error_closed_on_required');

    return e;
  });

  let valid = $derived(Object.keys(errors).length === 0);
  const show = (/** @type {string} */ field) => (touched[field] || submitted) && errors[field];

  /** @type {import('./$types').SubmitFunction} */
  const check = async ({ cancel }) => {
    submitted = true;
    if (!valid) {
      cancel();
      await tick();
      /** @type {HTMLElement | null} */
      const first = document.querySelector('[aria-invalid="true"]');
      first?.focus();
    }
  };
</script>

<PageHeader title={$_('cases.edit.title')} center>
  {#snippet crumb()}
    <a href={resolve('/tickets')}>{$_('cases.edit.breadcrumb_tickets')}</a>
    <ChevronRight size={12} />
    <a href={resolve(`/tickets/${ticket.id}`)}>{ticket.name}</a>
  {/snippet}
</PageHeader>

<div class="v2-scroll v2-pad" style="padding-top:18px">
  <form class="v2-form" method="POST" action="?/save" use:enhance={check} novalidate>
    {#if result?.error}
      <div
        class="v2-next"
        style="background:color-mix(in srgb, var(--v2-rust) 9%, transparent);border-color:color-mix(in srgb, var(--v2-rust) 28%, transparent);margin-bottom:18px"
        role="alert"
      >
        <TriangleAlert size={17} style="color:var(--v2-rust);flex:none" />
        <div class="v2-next-body">
          <div style="font-weight:600">{$_('cases.edit.server_error_heading')}</div>
          <div class="v2-sub" style="margin-top:2px">{result.error}</div>
        </div>
      </div>
    {/if}

    <div class="v2-field">
      <label for="f-name">{$_('cases.edit.label_subject')}</label>
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

    <div class="triple">
      <div class="v2-field">
        <label for="f-status">{$_('cases.edit.label_status')}</label>
        <select id="f-status" name="status" class="v2-input" bind:value={form.status}>
          {#each data.statuses as s (s.value)}
            <option value={s.value}>{s.label}</option>
          {/each}
        </select>
      </div>
      <div class="v2-field">
        <label for="f-priority">{$_('cases.edit.label_priority')}</label>
        <select id="f-priority" name="priority" class="v2-input" bind:value={form.priority}>
          {#each data.priorities as p (p.value)}
            <option value={p.value}>{p.label}</option>
          {/each}
        </select>
      </div>
      <div class="v2-field">
        <label for="f-type">{$_('cases.edit.label_type')}</label>
        <select id="f-type" name="case_type" class="v2-input" bind:value={form.case_type}>
          <option value="">{$_('cases.edit.option_type_not_set')}</option>
          {#each data.caseTypes as t (t.value)}
            <option value={t.value}>{t.label}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-closed">{$_('cases.edit.label_closed_on')}</label>
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
        {:else}
          <p class="v2-hint">{$_('cases.edit.hint_closed_on')}</p>
        {/if}
      </div>
      <div class="v2-field">
        <label for="f-owner">{$_('cases.edit.label_assignee')}</label>
        <select id="f-owner" name="assigned_to" class="v2-input" bind:value={form.assigned_to}>
          <option value="">{$_('cases.edit.option_owner_nobody')}</option>
          {#each data.owners as o (o.id)}
            <option value={o.id}>{o.name}</option>
          {/each}
        </select>
        <!--
          Only sent when it changed. `assigned_to` is many-to-many and this is a
          single select, so an unconditional submit would rewrite the whole list
          from one value and drop every co-assignee.
        -->
        <input type="hidden" name="assigned_to_original" value={data.form.assigned_to} />
        {#if data.server.assignee_count > 1}
          <p class="v2-hint">
            {$_('cases.edit.hint_assignee_count', {
              values: { count: data.server.assignee_count }
            })}
          </p>
        {/if}
      </div>
    </div>

    <div class="v2-field">
      <label for="f-contacts">{$_('cases.edit.label_people_affected')}</label>
      <select
        id="f-contacts"
        name="contacts"
        class="v2-input"
        multiple
        size="4"
        bind:value={contacts}
      >
        {#each data.contacts as c (c.id)}
          <option value={c.id}>{c.name}</option>
        {/each}
      </select>
      <!--
        A multi-select with nothing chosen submits nothing at all, which is
        indistinguishable from a field this form does not own. This marker is
        what makes "remove the last person" expressible.
      -->
      <input type="hidden" name="contacts_present" value="1" />
      <p class="v2-hint">{$_('cases.edit.hint_multi_select')}</p>
    </div>

    <div class="v2-field">
      <label for="f-desc">{$_('cases.edit.label_description')}</label>
      <textarea
        id="f-desc"
        name="description"
        class="v2-input"
        rows="4"
        bind:value={form.description}></textarea>
    </div>

    <p class="v2-sub" style="font-size:12px;margin:6px 0 0">
      {#if data.server.account}
        {$_('cases.edit.account_linked_prefix')}
        <a href={resolve(`/accounts/${data.server.account.id}`)}>{data.server.account.name}</a>{$_(
          'cases.edit.account_linked_suffix'
        )}
      {:else}
        {$_('cases.edit.account_not_linked')}
      {/if}
      {#if data.server.team_count || data.server.tag_count}
        {$_('cases.edit.relations_kept', {
          values: { teams: data.server.team_count, tags: data.server.tag_count }
        })}
      {/if}
    </p>

    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit">{$_('cases.edit.save_button')}</button>
      <a class="v2-btn" href={resolve(`/tickets/${ticket.id}`)}>{$_('cases.edit.cancel_button')}</a>
    </div>
  </form>
</div>

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .triple {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 14px;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-top: 22px;
    padding-bottom: 40px;
  }
  @media (max-width: 720px) {
    .pair,
    .triple {
      grid-template-columns: 1fr;
    }
  }
</style>
