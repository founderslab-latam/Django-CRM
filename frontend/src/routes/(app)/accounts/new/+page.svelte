<script>
  import { resolve } from '$app/paths';
  /**
   * A new account.
   *
   * Deliberately short. An account earns its detail from the deals, people and
   * invoices that accumulate against it, and a fourteen-field form standing
   * between somebody and recording a company they just spoke to is how CRMs
   * end up full of records named "asdf". Name is the only thing required;
   * everything else is on the edit page when it is actually known.
   *
   * `org` and `created_by` are not on the form and are not in the request.
   * `AccountsListView.post` derives both from `request.profile`, which comes
   * from the JWT. The only place identity can safely come from.
   */
  import { tick, untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import { isValidRut } from '$lib/common/rut.js';
  import { taxIdLabel, taxIdHint } from '$lib/common/tax-id-label.js';
  import { industryLabel } from '$lib/accounts/industry-labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { ChevronRight, TriangleAlert } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  /* What was typed survives a rejected submit, and `untrack` keeps a
     revalidation from wiping it back to the defaults underneath the cursor. */
  let form = $state(
    untrack(() => ({
      name: '',
      industry: data.defaults.industry,
      website: '',
      email: '',
      phone: '',
      number_of_employees: '',
      annual_revenue: '',
      city: '',
      country: data.defaults.country,
      tax_id: '',
      description: '',
      assigned_to: '',
      ...(result?.values ?? {})
    }))
  );

  let touched = $state(/** @type {Record<string, boolean>} */ ({}));
  let submitted = $state(false);

  let errors = $derived.by(() => {
    /** @type {Record<string, string>} */
    const e = {};
    if (!form.name.trim()) e.name = $_('accounts.new.error_name_required');

    if (form.annual_revenue !== '') {
      const n = Number(form.annual_revenue);
      if (!Number.isFinite(n)) e.annual_revenue = $_('accounts.new.error_revenue_not_number');
      else if (n < 0) e.annual_revenue = $_('accounts.new.error_revenue_negative');
    }
    if (form.number_of_employees !== '') {
      const n = Number(form.number_of_employees);
      if (!Number.isInteger(n))
        e.number_of_employees = $_('accounts.new.error_headcount_not_integer');
      else if (n < 0) e.number_of_employees = $_('accounts.new.error_headcount_negative');
    }
    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email))
      e.email = $_('accounts.new.error_email_invalid');
    // The exact regex from `flexible_phone_validator`.
    if (form.phone && !/^[\d\s\-()+.]{7,25}$/.test(form.phone))
      e.phone = $_('accounts.new.error_phone_invalid');
    // A Chilean account's tax ID is a RUT; the serializer rejects a bad check
    // digit. Mirror that so the field can say so before the round-trip.
    if (form.country === 'CL' && form.tax_id && !isValidRut(form.tax_id))
      e.tax_id = $_('common.tax_id.cl_invalid');

    return e;
  });

  let valid = $derived(Object.keys(errors).length === 0);
  const show = (/** @type {string} */ field) => (touched[field] || submitted) && errors[field];

  // Chile's tax ID is the RUT and has a checkable format; elsewhere it is a
  // free-form tax/VAT number. Only the label and hint change.
  let taxLabel = $derived(taxIdLabel(form.country, $_));
  let taxHint = $derived(taxIdHint(form.country, $_));

  /**
   * The name must be unique in the org, case-insensitively. That check needs
   * the database, so it happens on the server and arrives as `result.error`.
   * This only stops submissions that are wrong on their face.
   *
   * @type {import('./$types').SubmitFunction}
   */
  const check = async ({ cancel }) => {
    submitted = true;
    if (!valid) {
      cancel();
      await tick();
      /** @type {HTMLElement | null} */
      const first = document.querySelector('[aria-invalid="true"]');
      first?.focus();
      return;
    }
    return async ({ update }) => {
      await update({ reset: false });
    };
  };
</script>

<PageHeader title={$_('accounts.new.title')} center>
  {#snippet crumb()}
    <a href={resolve('/accounts')}>{$_('accounts.new.breadcrumb_accounts')}</a>
    <ChevronRight size={12} />
    <span>{$_('accounts.new.breadcrumb_new')}</span>
  {/snippet}
  {#snippet sub()}
    {$_('accounts.new.subheading')}
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
          <div style="font-weight:600">{$_('accounts.new.server_error_heading')}</div>
          <div class="v2-sub" style="margin-top:2px">{result.error}</div>
        </div>
      </div>
    {/if}

    <div class="v2-field">
      <label for="f-name">{$_('accounts.new.label_name')}</label>
      <input
        id="f-name"
        name="name"
        class="v2-input"
        bind:value={form.name}
        onblur={() => (touched.name = true)}
        aria-invalid={show('name') ? 'true' : undefined}
      />
      {#if show('name')}
        <p class="v2-error">{errors.name}</p>
      {:else}
        <p class="v2-hint">{$_('accounts.new.hint_name_unique')}</p>
      {/if}
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-industry">{$_('accounts.new.label_industry')}</label>
        <select id="f-industry" name="industry" class="v2-input" bind:value={form.industry}>
          <option value="">{$_('accounts.new.option_not_recorded')}</option>
          {#each data.industries as i (i.value)}
            <option value={i.value}>{industryLabel(i.value, $_)}</option>
          {/each}
        </select>
      </div>
      <div class="v2-field">
        <label for="f-owner">{$_('accounts.new.label_owner')}</label>
        <select id="f-owner" name="assigned_to" class="v2-input" bind:value={form.assigned_to}>
          <option value="">{$_('accounts.new.option_nobody')}</option>
          {#each data.owners as o (o.id)}
            <!-- The value is the Profile id, not the display name. -->
            <option value={o.id}>{o.name}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-email">{$_('accounts.new.label_email')}</label>
        <input
          id="f-email"
          name="email"
          class="v2-input"
          type="email"
          bind:value={form.email}
          onblur={() => (touched.email = true)}
          aria-invalid={show('email') ? 'true' : undefined}
        />
        {#if show('email')}<p class="v2-error">{errors.email}</p>{/if}
      </div>
      <div class="v2-field">
        <label for="f-phone">{$_('accounts.new.label_phone')}</label>
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

    <div class="v2-field">
      <label for="f-website">{$_('accounts.new.label_website')}</label>
      <input id="f-website" name="website" class="v2-input" type="url" bind:value={form.website} />
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-staff">{$_('accounts.new.label_headcount')}</label>
        <input
          id="f-staff"
          name="number_of_employees"
          class="v2-input v2-num"
          type="text"
          inputmode="numeric"
          bind:value={form.number_of_employees}
          onblur={() => (touched.number_of_employees = true)}
          aria-invalid={show('number_of_employees') ? 'true' : undefined}
        />
        {#if show('number_of_employees')}<p class="v2-error">{errors.number_of_employees}</p>{/if}
      </div>
      <div class="v2-field">
        <label for="f-revenue">{$_('accounts.new.label_annual_revenue')}</label>
        <input
          id="f-revenue"
          name="annual_revenue"
          class="v2-input v2-num"
          type="text"
          inputmode="decimal"
          bind:value={form.annual_revenue}
          onblur={() => (touched.annual_revenue = true)}
          aria-invalid={show('annual_revenue') ? 'true' : undefined}
        />
        {#if show('annual_revenue')}<p class="v2-error">{errors.annual_revenue}</p>{/if}
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-city">{$_('accounts.new.label_city')}</label>
        <input id="f-city" name="city" class="v2-input" bind:value={form.city} />
      </div>
      <div class="v2-field">
        <label for="f-country">{$_('accounts.new.label_country')}</label>
        <select id="f-country" name="country" class="v2-input" bind:value={form.country}>
          <option value="">{$_('accounts.new.option_not_recorded')}</option>
          {#each data.countries as c (c.value)}
            <option value={c.value}>{c.label}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="v2-field">
      <label for="f-tax">{taxLabel}</label>
      <input
        id="f-tax"
        name="tax_id"
        class="v2-input"
        maxlength="50"
        bind:value={form.tax_id}
        placeholder={form.country === 'CL' ? $_('common.tax_id.cl_placeholder') : undefined}
        onblur={() => (touched.tax_id = true)}
        aria-invalid={show('tax_id') ? 'true' : undefined}
      />
      {#if show('tax_id')}
        <p class="v2-error">{errors.tax_id}</p>
      {:else if taxHint}
        <p class="v2-hint">{taxHint}</p>
      {/if}
    </div>

    <div class="v2-field">
      <label for="f-notes">{$_('accounts.new.label_notes')}</label>
      <textarea
        id="f-notes"
        name="description"
        class="v2-input"
        rows="3"
        bind:value={form.description}></textarea>
    </div>

    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit">{$_('accounts.new.submit_button')}</button
      >
      <a class="v2-btn" href={resolve('/accounts')}>{$_('accounts.new.cancel_button')}</a>
    </div>
  </form>
</div>

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
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
    .pair {
      grid-template-columns: 1fr;
    }
  }
</style>
