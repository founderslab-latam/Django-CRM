<script>
  import { resolve } from '$app/paths';
  /**
   * Editing a contact.
   *
   * ── EMAIL IS UNIQUE PER ORG, CASE-INSENSITIVELY ──────────────────────────
   * `unique_contact_email_per_org` is a database constraint on `Lower(email)`.
   * `CreateContactSerializer.validate_email` catches it first and returns a
   * clean 400, so what appears below is the server's own sentence rather than
   * a 500.
   *
   * ── WHAT THIS FORM DOES NOT OWN ─────────────────────────────────────────
   * Teams, tags and co-assignees are not on it. `ContactDetailView.put` clears
   * all three unconditionally, which is why the action uses PATCH and why the
   * summary at the bottom states what is being left alone. The one relation
   * this form touches is the owner, and even that is only sent when it changed.
   *
   * Membership of other accounts is not editable here either: this form sets
   * the *primary* account, and the server adds that account's people list to
   * match. Removing somebody from an account is done from the account.
   */
  import { tick, untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { ChevronRight, TriangleAlert } from '@lucide/svelte';
  import { _ } from '$lib/i18n/index.js';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  const { contact, server } = untrack(() => ({ contact: data.contact, server: data.server }));

  let form = $state(untrack(() => ({ ...data.form })));
  let touched = $state(/** @type {Record<string, boolean>} */ ({}));
  let submitted = $state(false);
  let saved = $state(false);

  let errors = $derived.by(() => {
    /** @type {Record<string, string>} */
    const e = {};
    if (!form.first_name.trim()) e.first_name = $_('contacts.edit.error_first_name_required');
    if (!form.last_name.trim()) e.last_name = $_('contacts.edit.error_last_name_required');

    if (form.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email))
      e.email = $_('contacts.edit.error_email_invalid');

    // The exact regex from `flexible_phone_validator` in
    // `common/validators.py`, which Contact, Account and Lead all use.
    // Surfaced at the field, because otherwise a seeded number carrying an
    // "x123" extension rejects the entire save without naming a field, and
    // seven of the fifteen seeded contacts carry exactly that.
    if (form.phone && !/^[\d\s\-()+.]{7,25}$/.test(form.phone))
      e.phone = $_('contacts.edit.error_phone_invalid');

    if (form.linkedin_url && !/^https?:\/\/\S+$/.test(form.linkedin_url))
      e.linkedin_url = $_('contacts.edit.error_linkedin_invalid');

    return e;
  });

  let valid = $derived(Object.keys(errors).length === 0);
  const show = (/** @type {string} */ field) => (touched[field] || submitted) && errors[field];

  /**
   * These checks are a UX hint. The serializer is the rule, and its 400 is
   * what `result.error` reports.
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
      await update({ reset: false });
      saved = outcome.type === 'success';
    };
  };

  let untouchedRelations = $derived(
    [
      server.owner_count > 1 &&
        $_('contacts.edit.relation_owners', { values: { count: server.owner_count } }),
      server.team_count &&
        $_('contacts.edit.relation_teams', { values: { count: server.team_count } }),
      server.tag_count &&
        $_('contacts.edit.relation_tags', { values: { count: server.tag_count } }),
      server.linked_account_count &&
        $_('contacts.edit.relation_account_links', {
          values: { count: server.linked_account_count }
        })
    ].filter(Boolean)
  );
</script>

<PageHeader title={$_('contacts.edit.heading', { values: { name: contact.name } })} center>
  {#snippet crumb()}
    <a href={resolve('/contacts')}>{$_('contacts.edit.breadcrumb_contacts')}</a>
    <ChevronRight size={12} />
    <a href={resolve(`/contacts/${contact.id}`)}>{contact.name}</a>
  {/snippet}
  {#snippet sub()}
    {[
      contact.title,
      server.deal_count
        ? $_('contacts.edit.deal_count_label', { values: { count: server.deal_count } })
        : null,
      server.ticket_count
        ? $_('contacts.edit.ticket_count_label', { values: { count: server.ticket_count } })
        : null
    ]
      .filter(Boolean)
      .join(' · ') || $_('contacts.edit.no_related_records')}
  {/snippet}
</PageHeader>

<div class="v2-scroll v2-pad" style="padding-top:18px">
  <form class="v2-form" method="POST" action="?/save" use:enhance={check} novalidate>
    {#if saved}
      <div class="v2-next" style="margin-bottom:18px" role="status">
        <div class="v2-next-body">
          <div class="v2-next-text">{$_('contacts.edit.saved_heading')}</div>
          <div class="v2-sub" style="margin-top:3px">
            {$_('contacts.edit.saved_detail', { values: { name: contact.name } })}
          </div>
        </div>
        <a class="v2-btn" href={resolve(`/contacts/${contact.id}`)}
          >{$_('contacts.edit.back_to_contact_button')}</a
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
          <div style="font-weight:600">{$_('contacts.edit.server_error_heading')}</div>
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
            {$_('contacts.edit.fields_need_you', { values: { count: Object.keys(errors).length } })}
          </div>
          <div class="v2-sub" style="margin-top:2px">{$_('contacts.edit.nothing_saved')}</div>
        </div>
      </div>
    {/if}

    <div class="pair">
      <div class="v2-field">
        <label for="f-first">{$_('contacts.edit.label_first_name')}</label>
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
        <label for="f-last">{$_('contacts.edit.label_last_name')}</label>
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
        <label for="f-email">{$_('contacts.edit.label_email')}</label>
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
          <p class="v2-hint">{$_('contacts.edit.hint_email_unique')}</p>
        {/if}
      </div>
      <div class="v2-field">
        <label for="f-phone">{$_('contacts.edit.label_phone')}</label>
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
        <label for="f-title">{$_('contacts.edit.label_job_title')}</label>
        <input id="f-title" name="title" class="v2-input" bind:value={form.title} />
      </div>
      <div class="v2-field">
        <label for="f-dept">{$_('contacts.edit.label_department')}</label>
        <input id="f-dept" name="department" class="v2-input" bind:value={form.department} />
      </div>
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-account">{$_('contacts.edit.label_account')}</label>
        <select id="f-account" name="account" class="v2-input" bind:value={form.account}>
          <option value="">{$_('contacts.edit.option_not_linked')}</option>
          {#each data.accounts as a (a.id)}
            <option value={a.id}>{a.name}</option>
          {/each}
        </select>
        {#if data.account_total > data.accounts.length}
          <p class="v2-hint">
            {$_('contacts.edit.hint_showing_accounts_prefix')}
            <span class="v2-num">{data.accounts.length}</span>
            {$_('contacts.edit.hint_showing_accounts_middle')}
            <span class="v2-num">{data.account_total}</span>
            {$_('contacts.edit.hint_showing_accounts_suffix')}
          </p>
        {:else}
          <p class="v2-hint">{$_('contacts.edit.hint_account_link')}</p>
        {/if}
      </div>
      <div class="v2-field">
        <label for="f-owner">{$_('contacts.edit.label_owner')}</label>
        <!-- What the select was rendered with. The action compares against it
             so an untouched owner is not sent at all; `assigned_to` is a
             many-to-many and this select is single, so sending it always would
             cut a two-person contact down to one on every save. -->
        <input type="hidden" name="assigned_to_original" value={data.form.assigned_to} />
        <select id="f-owner" name="assigned_to" class="v2-input" bind:value={form.assigned_to}>
          <option value="">{$_('contacts.edit.option_nobody')}</option>
          {#each data.owners as o (o.id)}
            <option value={o.id}>{o.name}</option>
          {/each}
        </select>
        {#if server.owner_count > 1}
          <p class="v2-hint">
            <span class="v2-num">{server.owner_count}</span>
            {$_('contacts.edit.hint_multiple_owners_suffix')}
          </p>
        {/if}
      </div>
    </div>

    <div class="v2-field">
      <label for="f-org">{$_('contacts.edit.label_company_typed_in')}</label>
      <input id="f-org" name="organization" class="v2-input" bind:value={form.organization} />
      <p class="v2-hint">
        {$_('contacts.edit.hint_company_typed_in')}
      </p>
    </div>

    <div class="v2-field">
      <label for="f-linkedin">{$_('contacts.edit.label_linkedin')}</label>
      <input
        id="f-linkedin"
        name="linkedin_url"
        class="v2-input"
        type="url"
        bind:value={form.linkedin_url}
        onblur={() => (touched.linkedin_url = true)}
        aria-invalid={show('linkedin_url') ? 'true' : undefined}
      />
      {#if show('linkedin_url')}<p class="v2-error">{errors.linkedin_url}</p>{/if}
    </div>

    <div class="v2-field">
      <label for="f-address">{$_('contacts.edit.label_address')}</label>
      <input id="f-address" name="address_line" class="v2-input" bind:value={form.address_line} />
    </div>

    <div class="triple">
      <div class="v2-field">
        <label for="f-city">{$_('contacts.edit.label_city')}</label>
        <input id="f-city" name="city" class="v2-input" bind:value={form.city} />
      </div>
      <div class="v2-field">
        <label for="f-state">{$_('contacts.edit.label_state')}</label>
        <input id="f-state" name="state" class="v2-input" bind:value={form.state} />
      </div>
      <div class="v2-field">
        <label for="f-postcode">{$_('contacts.edit.label_postcode')}</label>
        <input id="f-postcode" name="postcode" class="v2-input" bind:value={form.postcode} />
      </div>
    </div>

    <div class="v2-field">
      <label for="f-country">{$_('contacts.edit.label_country')}</label>
      <select id="f-country" name="country" class="v2-input" bind:value={form.country}>
        <option value="">{$_('contacts.edit.option_not_recorded')}</option>
        {#each data.countries as c (c.value)}
          <option value={c.value}>{c.label}</option>
        {/each}
      </select>
    </div>

    <div class="v2-field">
      <label for="f-notes">{$_('contacts.edit.label_notes')}</label>
      <textarea
        id="f-notes"
        name="description"
        class="v2-input"
        rows="4"
        bind:value={form.description}></textarea>
    </div>

    <!--
      A cleared checkbox submits nothing, which is indistinguishable from a
      field this form does not own, and "absent means leave alone" is what
      makes PATCH safe everywhere else. The hidden partner is always sent, so
      the action can tell the two apart and switching either flag off works.
    -->
    <div class="flags">
      <input type="hidden" name="do_not_call_present" value="1" />
      <label class="flag">
        <input type="checkbox" name="do_not_call" bind:checked={form.do_not_call} />
        <span>
          <strong>{$_('contacts.edit.flag_do_not_call_label')}</strong>
          <span class="v2-sub">{$_('contacts.edit.flag_do_not_call_hint')}</span>
        </span>
      </label>

      <input type="hidden" name="is_active_present" value="1" />
      <label class="flag">
        <input type="checkbox" name="is_active" bind:checked={form.is_active} />
        <span>
          <strong>{$_('contacts.edit.flag_still_works_label')}</strong>
          <span class="v2-sub">
            {$_('contacts.edit.flag_still_works_hint')}
          </span>
        </span>
      </label>
    </div>

    {#if untouchedRelations.length}
      <p class="v2-hint" style="margin-bottom:14px">
        {$_('contacts.edit.untouched_relations_prefix')}
        {untouchedRelations.join(', ')}
        {$_('contacts.edit.untouched_relations_suffix')}
      </p>
    {/if}

    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit">{$_('contacts.edit.save_button')}</button>
      <a class="v2-btn" href={resolve(`/contacts/${contact.id}`)}
        >{$_('contacts.edit.cancel_button')}</a
      >
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
    grid-template-columns: 2fr 1fr 1fr;
    gap: 14px;
  }
  .flags {
    display: grid;
    gap: 10px;
    margin: 4px 0 18px;
  }
  .flag {
    display: flex;
    gap: 9px;
    align-items: flex-start;
    font-size: 13px;
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
    .pair,
    .triple {
      grid-template-columns: 1fr;
    }
  }
</style>
