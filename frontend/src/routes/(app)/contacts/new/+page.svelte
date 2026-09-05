<script>
  import { resolve } from '$app/paths';
  /**
   * Adding a person.
   *
   * Deliberately shorter than the edit form. Everything optional is left off
   * until there is a record to hang it on: address, LinkedIn, notes and the
   * inactive flag are all on the edit page, and a new contact is by definition
   * somebody who still works there.
   *
   * `?account=<id>` preselects the company, so "add somebody at this account"
   * arrives with the account already chosen.
   */
  import { tick, untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { ChevronRight, TriangleAlert } from '@lucide/svelte';
  import { _ } from '$lib/i18n/index.js';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  // `untrack` so a re-render after a failed save does not throw away what the
  // person typed; `result.values` is the server's echo of the same fields.
  let form = $state(
    untrack(() => ({
      first_name: '',
      last_name: '',
      email: '',
      phone: '',
      title: '',
      department: '',
      organization: '',
      account: data.defaults.account ?? '',
      assigned_to: '',
      do_not_call: false,
      ...(result?.values ?? {})
    }))
  );
  let touched = $state(/** @type {Record<string, boolean>} */ ({}));
  let submitted = $state(false);

  let errors = $derived.by(() => {
    /** @type {Record<string, string>} */
    const e = {};
    if (!form.first_name.trim()) e.first_name = $_('contacts.new.error_first_name_required');
    if (!form.last_name.trim()) e.last_name = $_('contacts.new.error_last_name_required');

    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email))
      e.email = $_('contacts.new.error_email_invalid');

    // The exact regex from `flexible_phone_validator`. Extensions like "x123"
    // are rejected by the model, so they are caught at the field rather than
    // as an opaque whole-form refusal after the save.
    if (form.phone && !/^[\d\s\-()+.]{7,25}$/.test(form.phone))
      e.phone = $_('contacts.new.error_phone_invalid');

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

  let chosenAccount = $derived(
    data.accounts.find((/** @type {any} */ a) => a.id === form.account) ?? null
  );
</script>

<PageHeader title={$_('contacts.new.heading')} center>
  {#snippet crumb()}
    <a href={resolve('/contacts')}>{$_('contacts.new.breadcrumb_contacts')}</a>
    <ChevronRight size={12} />
    <span>{$_('contacts.new.breadcrumb_new')}</span>
  {/snippet}
  {#snippet sub()}
    {$_('contacts.new.subheading')}
  {/snippet}
</PageHeader>

<div class="v2-scroll v2-pad" style="padding-top:18px">
  <form class="v2-form" method="POST" action="?/create" use:enhance={check} novalidate>
    {#if result?.error}
      <div
        class="v2-next"
        style="background:color-mix(in srgb, var(--v2-rust) 9%, transparent);border-color:color-mix(in srgb, var(--v2-rust) 28%, transparent);margin-bottom:18px"
        role="alert"
      >
        <TriangleAlert size={17} style="color:var(--v2-rust);flex:none" />
        <div class="v2-next-body">
          <div style="font-weight:600">{$_('contacts.new.server_error_heading')}</div>
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
            {$_('contacts.new.fields_need_you', { values: { count: Object.keys(errors).length } })}
          </div>
          <div class="v2-sub" style="margin-top:2px">{$_('contacts.new.nothing_created')}</div>
        </div>
      </div>
    {/if}

    <div class="pair">
      <div class="v2-field">
        <label for="f-first">{$_('contacts.new.label_first_name')}</label>
        <input
          id="f-first"
          name="first_name"
          class="v2-input"
          bind:value={form.first_name}
          onblur={() => (touched.first_name = true)}
          aria-invalid={show('first_name') ? 'true' : undefined}
        />
        {#if show('first_name')}<p class="v2-error">{errors.first_name}</p>{/if}
      </div>
      <div class="v2-field">
        <label for="f-last">{$_('contacts.new.label_last_name')}</label>
        <input
          id="f-last"
          name="last_name"
          class="v2-input"
          bind:value={form.last_name}
          onblur={() => (touched.last_name = true)}
          aria-invalid={show('last_name') ? 'true' : undefined}
        />
        {#if show('last_name')}<p class="v2-error">{errors.last_name}</p>{/if}
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-email">{$_('contacts.new.label_email')}</label>
        <input
          id="f-email"
          name="email"
          class="v2-input"
          type="email"
          bind:value={form.email}
          onblur={() => (touched.email = true)}
          aria-invalid={show('email') ? 'true' : undefined}
        />
        {#if show('email')}
          <p class="v2-error">{errors.email}</p>
        {:else}
          <p class="v2-hint">{$_('contacts.new.hint_email_unique')}</p>
        {/if}
      </div>
      <div class="v2-field">
        <label for="f-phone">{$_('contacts.new.label_phone')}</label>
        <input
          id="f-phone"
          name="phone"
          class="v2-input"
          bind:value={form.phone}
          onblur={() => (touched.phone = true)}
          aria-invalid={show('phone') ? 'true' : undefined}
        />
        {#if show('phone')}<p class="v2-error">{errors.phone}</p>{/if}
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-title">{$_('contacts.new.label_job_title')}</label>
        <input id="f-title" name="title" class="v2-input" bind:value={form.title} />
      </div>
      <div class="v2-field">
        <label for="f-dept">{$_('contacts.new.label_department')}</label>
        <input id="f-dept" name="department" class="v2-input" bind:value={form.department} />
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-account">{$_('contacts.new.label_account')}</label>
        <select id="f-account" name="account" class="v2-input" bind:value={form.account}>
          <option value="">{$_('contacts.new.option_not_linked')}</option>
          {#each data.accounts as a (a.id)}
            <option value={a.id}>{a.name}</option>
          {/each}
        </select>
        {#if chosenAccount}
          <p class="v2-hint">
            {$_('contacts.new.hint_account_chosen', { values: { name: chosenAccount.name } })}
          </p>
        {:else if data.account_total > data.accounts.length}
          <p class="v2-hint">
            {$_('contacts.new.hint_showing_accounts_prefix')}
            <span class="v2-num">{data.accounts.length}</span>
            {$_('contacts.new.hint_showing_accounts_middle')}
            <span class="v2-num">{data.account_total}</span>
            {$_('contacts.new.hint_showing_accounts_suffix')}
          </p>
        {:else}
          <p class="v2-hint">{$_('contacts.new.hint_account_optional')}</p>
        {/if}
      </div>
      <div class="v2-field">
        <label for="f-owner">{$_('contacts.new.label_owner')}</label>
        <select id="f-owner" name="assigned_to" class="v2-input" bind:value={form.assigned_to}>
          <option value="">{$_('contacts.new.option_nobody')}</option>
          {#each data.owners as o (o.id)}
            <option value={o.id}>{o.name}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="v2-field">
      <label for="f-org">{$_('contacts.new.label_company_typed_in')}</label>
      <input id="f-org" name="organization" class="v2-input" bind:value={form.organization} />
      <p class="v2-hint">
        {$_('contacts.new.hint_company_typed_in')}
      </p>
    </div>

    <label class="flag">
      <input type="checkbox" name="do_not_call" bind:checked={form.do_not_call} />
      <span>
        <strong>{$_('contacts.new.flag_do_not_call_label')}</strong>
        <span class="v2-sub">{$_('contacts.new.flag_do_not_call_hint')}</span>
      </span>
    </label>

    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit">{$_('contacts.new.create_button')}</button
      >
      <a class="v2-btn" href={resolve('/contacts')}>{$_('contacts.new.cancel_button')}</a>
    </div>
  </form>
</div>

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .flag {
    display: flex;
    gap: 9px;
    align-items: flex-start;
    font-size: 13px;
    margin: 4px 0 18px;
  }
  .flag span {
    display: block;
  }
  .flag .v2-sub {
    display: block;
    font-size: 11.5px;
    margin-top: 2px;
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 9px;
    margin-top: 22px;
    padding-bottom: 40px;
  }
  @media (max-width: 720px) {
    .pair {
      grid-template-columns: 1fr;
    }
  }
</style>
