<script>
  import { resolve } from '$app/paths';
  /**
   * Editing the organisation.
   *
   * Admin-only. A non-admin who reaches this URL directly gets an "Admins only"
   * state, not the form, but that is the courtesy, not the control: the save
   * posts to `PATCH /api/org/settings/`, which the backend refuses for anyone
   * whose role is not ADMIN. `result.error` reports that refusal.
   *
   * What this form owns is the org's own settings: the company profile printed
   * on invoices, the locale defaults, and the two org-wide case-handling
   * switches. What it deliberately does NOT own: the org API key (a credential,
   * rotated through its own audited action) and `is_active` (the org kill
   * switch). Neither is a field here, and the server would not accept them if
   * they were smuggled into the request.
   *
   * The two switches submit an explicit on/off, so turning one OFF is a real
   * choice the save records, not the "left blank, so unchanged" behaviour of
   * the text fields.
   */
  import { tick, untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { isValidRut } from '$lib/common/rut.js';
  import { taxIdLabel, taxIdHint } from '$lib/common/tax-id-label.js';
  import { CURRENCY_CODES } from '$lib/constants/filters.js';
  import { ChevronRight, TriangleAlert } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  // A supported currency is required (the column is non-blank with a default),
  // so the empty "Select Currency" placeholder is dropped from the options.
  const currencyOptions = CURRENCY_CODES.filter((/** @type {any} */ c) => c.value);

  // A compact country list. Every value is a real code in the backend COUNTRIES
  // set, so the select can never offer one the serializer rejects.
  const countryOptions = [
    { value: 'US', label: 'United States' },
    { value: 'GB', label: 'United Kingdom' },
    { value: 'CA', label: 'Canada' },
    { value: 'AU', label: 'Australia' },
    { value: 'DE', label: 'Germany' },
    { value: 'FR', label: 'France' },
    { value: 'IN', label: 'India' },
    { value: 'JP', label: 'Japan' },
    { value: 'SG', label: 'Singapore' },
    { value: 'AE', label: 'United Arab Emirates' },
    { value: 'BR', label: 'Brazil' },
    { value: 'MX', label: 'Mexico' },
    { value: 'CL', label: 'Chile' },
    { value: 'CH', label: 'Switzerland' },
    { value: 'NL', label: 'Netherlands' },
    { value: 'ES', label: 'Spain' },
    { value: 'IT', label: 'Italy' }
  ];

  const org = untrack(() => data.org ?? {});
  // Always includes the org's current value, because the API builds the list
  // from the same database the value was validated against. A stored zone with
  // no matching option would make the select submit its first entry instead.
  const timezones = untrack(() => data.timezones ?? [{ name: 'UTC', label: 'UTC' }]);

  let form = $state(
    untrack(() => ({
      name: org.name ?? '',
      company_name: org.company_name ?? '',
      address_line: org.address_line ?? '',
      city: org.city ?? '',
      state: org.state ?? '',
      postcode: org.postcode ?? '',
      country: org.country ?? '',
      phone: org.phone ?? '',
      email: org.email ?? '',
      website: org.website ?? '',
      tax_id: org.tax_id ?? '',
      default_currency: org.default_currency || 'USD',
      default_country: org.default_country ?? '',
      timezone: org.timezone || 'UTC',
      // Booleans travel as strings so the select always submits an explicit value.
      csat_enabled: String(org.csat_enabled ?? true),
      auto_close_children_on_parent_close: String(org.auto_close_children_on_parent_close ?? false)
    }))
  );

  let touched = $state(/** @type {Record<string, boolean>} */ ({}));
  let submitted = $state(false);

  let errors = $derived.by(() => {
    /** @type {Record<string, string>} */
    const e = {};
    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email))
      e.email = $_('settings.organization.edit.err_email');
    // The model stores this in a URLField, which wants a real URL. A light check
    // here saves a server round-trip; the serializer is the actual rule.
    if (form.website && !/^https?:\/\/.+\..+/.test(form.website))
      e.website = $_('settings.organization.edit.err_website');
    // A Chilean org's tax ID is a RUT, and the serializer rejects one whose
    // check digit does not match. Mirror that here so the field can say so.
    if (form.country === 'CL' && form.tax_id && !isValidRut(form.tax_id))
      e.tax_id = $_('common.tax_id.cl_invalid');
    return e;
  });

  let valid = $derived(Object.keys(errors).length === 0);

  // The company tax ID is called different things by country. Chile's is the
  // RUT; everywhere else the generic label stands. The field and its stored
  // value do not change, only what it is called.
  let taxLabel = $derived(taxIdLabel(form.country, $_));
  let taxHint = $derived(taxIdHint(form.country, $_));
  const show = (/** @type {string} */ field) => (touched[field] || submitted) && errors[field];

  /**
   * These checks are a UX hint. The serializer is the rule, and its 400 is what
   * `result.error` reports.
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
      // Keep the entered values on a server rejection so nothing is retyped.
      await update({ reset: false });
    };
  };
</script>

{#if data.forbidden}
  <PageHeader title={$_('settings.organization.edit.forbidden_title')}>
    {#snippet crumb()}<SettingsCrumb />{/snippet}
  </PageHeader>
  <div class="v2-pad" style="padding-top:40px">
    <NextAction
      label={$_('settings.organization.edit.forbidden_label')}
      text={$_('settings.organization.edit.forbidden_text')}
    />
  </div>
{:else}
  <PageHeader title={$_('settings.organization.edit.title')} center>
    {#snippet crumb()}
      <a href={resolve('/settings')}>{$_('settings.organization.edit.crumb_settings')}</a>
      <ChevronRight size={12} />
      <a href={resolve('/settings/organization')}
        >{$_('settings.organization.edit.crumb_organization')}</a
      >
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
            <div style="font-weight:600">
              {$_('settings.organization.edit.server_error_heading')}
            </div>
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
            <!-- Counted, not assumed. Only two fields are checked here, but one
                 of them failing on its own is the common case. -->
            <div style="font-weight:600">
              {Object.keys(errors).length === 1
                ? $_('settings.organization.edit.one_field')
                : $_('settings.organization.edit.two_fields')}
            </div>
            <div class="v2-sub" style="margin-top:2px">
              {$_('settings.organization.edit.nothing_saved')}
            </div>
          </div>
        </div>
      {/if}

      <div class="v2-label" style="margin-bottom:12px">
        {$_('settings.organization.edit.section_customers')}
      </div>
      <p class="v2-hint" style="margin-top:-4px;margin-bottom:14px">
        {$_('settings.organization.edit.customers_note')}
      </p>

      <div class="v2-field">
        <label for="f-company">{$_('settings.organization.edit.legal_name')}</label>
        <input
          id="f-company"
          name="company_name"
          class="v2-input"
          maxlength="255"
          bind:value={form.company_name}
        />
        <p class="v2-hint">{$_('settings.organization.edit.legal_name_hint')}</p>
      </div>

      <div class="v2-field">
        <label for="f-name">{$_('settings.organization.edit.trading_name')}</label>
        <input id="f-name" name="name" class="v2-input" maxlength="100" bind:value={form.name} />
        <p class="v2-hint">{$_('settings.organization.edit.trading_name_hint')}</p>
      </div>

      <div class="pair">
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
          <label for="f-phone">{$_('settings.organization.edit.phone')}</label>
          <input
            id="f-phone"
            name="phone"
            class="v2-input"
            maxlength="25"
            bind:value={form.phone}
          />
        </div>
      </div>

      <div class="pair">
        <div class="v2-field">
          <label for="f-email">{$_('settings.organization.edit.email')}</label>
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
          <label for="f-website">{$_('settings.organization.edit.website')}</label>
          <input
            id="f-website"
            name="website"
            class="v2-input"
            type="url"
            bind:value={form.website}
            onblur={() => (touched.website = true)}
            aria-invalid={show('website') ? 'true' : undefined}
          />
          {#if show('website')}<p class="v2-error">{errors.website}</p>{/if}
        </div>
      </div>

      <div class="v2-field">
        <label for="f-address">{$_('settings.organization.edit.address')}</label>
        <input
          id="f-address"
          name="address_line"
          class="v2-input"
          maxlength="255"
          bind:value={form.address_line}
        />
      </div>

      <div class="triple">
        <div class="v2-field">
          <label for="f-city">{$_('settings.organization.edit.city')}</label>
          <input id="f-city" name="city" class="v2-input" maxlength="100" bind:value={form.city} />
        </div>
        <div class="v2-field">
          <label for="f-state">{$_('settings.organization.edit.state')}</label>
          <input
            id="f-state"
            name="state"
            class="v2-input"
            maxlength="100"
            bind:value={form.state}
          />
        </div>
        <div class="v2-field">
          <label for="f-postcode">{$_('settings.organization.edit.postcode')}</label>
          <input
            id="f-postcode"
            name="postcode"
            class="v2-input"
            maxlength="20"
            bind:value={form.postcode}
          />
        </div>
      </div>

      <div class="v2-field">
        <label for="f-country">{$_('settings.organization.edit.country')}</label>
        <select id="f-country" name="country" class="v2-input" bind:value={form.country}>
          <option value="">{$_('settings.organization.edit.country_none')}</option>
          {#each countryOptions as c (c.value)}
            <option value={c.value}>{c.label}</option>
          {/each}
        </select>
      </div>

      <div class="v2-label" style="margin:24px 0 12px">
        {$_('settings.organization.edit.section_defaults')}
      </div>
      <div class="pair">
        <div class="v2-field">
          <label for="f-currency">{$_('settings.organization.edit.currency')}</label>
          <select
            id="f-currency"
            name="default_currency"
            class="v2-input"
            bind:value={form.default_currency}
          >
            {#each currencyOptions as c (c.value)}
              <option value={c.value}>{c.label}</option>
            {/each}
          </select>
          <p class="v2-hint">{$_('settings.organization.edit.currency_hint')}</p>
        </div>
        <div class="v2-field">
          <label for="f-defcountry">{$_('settings.organization.edit.country_default')}</label>
          <select
            id="f-defcountry"
            name="default_country"
            class="v2-input"
            bind:value={form.default_country}
          >
            <option value="">{$_('settings.organization.edit.country_default_none')}</option>
            {#each countryOptions as c (c.value)}
              <option value={c.value}>{c.label}</option>
            {/each}
          </select>
          <p class="v2-hint">{$_('settings.organization.edit.country_default_hint')}</p>
        </div>
      </div>

      <div class="v2-field">
        <label for="f-timezone">{$_('settings.organization.edit.timezone')}</label>
        <select id="f-timezone" name="timezone" class="v2-input" bind:value={form.timezone}>
          {#each timezones as zone (zone.name)}
            <option value={zone.name}>{zone.label}</option>
          {/each}
        </select>
        <p class="v2-hint">
          {$_('settings.organization.edit.timezone_hint')}
        </p>
      </div>

      <div class="v2-label" style="margin:24px 0 12px">
        {$_('settings.organization.edit.section_behaviour')}
      </div>

      <div class="v2-field">
        <label for="f-csat">{$_('settings.organization.edit.csat')}</label>
        <select id="f-csat" name="csat_enabled" class="v2-input" bind:value={form.csat_enabled}>
          <option value="true">{$_('settings.organization.edit.csat_on')}</option>
          <option value="false">{$_('settings.organization.edit.csat_off')}</option>
        </select>
        <p class="v2-hint">
          {$_('settings.organization.edit.csat_hint')}
        </p>
      </div>

      <div class="v2-field">
        <label for="f-cascade">{$_('settings.organization.edit.cascade')}</label>
        <select
          id="f-cascade"
          name="auto_close_children_on_parent_close"
          class="v2-input"
          bind:value={form.auto_close_children_on_parent_close}
        >
          <option value="true">{$_('settings.organization.edit.cascade_on')}</option>
          <option value="false">{$_('settings.organization.edit.cascade_off')}</option>
        </select>
        <p class="v2-hint">
          {$_('settings.organization.edit.cascade_hint')}
        </p>
      </div>

      <div class="actions">
        <button class="v2-btn v2-btn-primary" type="submit">
          {$_('settings.organization.edit.save')}
        </button>
        <a class="v2-btn" href={resolve('/settings/organization')}>
          {$_('settings.organization.edit.cancel')}
        </a>
      </div>
    </form>
  </div>
{/if}

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .triple {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
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
