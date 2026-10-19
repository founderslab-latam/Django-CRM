<script>
  import { resolve } from '$app/paths';
  /**
   * The addresses that turn email into tickets.
   *
   * Two things this page is careful about:
   *
   * 1. NO SECRETS. InboundMailbox carries a `webhook_secret` column and a
   *    `topic_arn`, and neither is fetched, rendered, or masked-but-present in
   *    the DOM here or on the form below. There is no field for either, not
   *    even a disabled one: an empty one posted on an edit would blank the
   *    column, and the ARN embeds the AWS account id. What proves a delivery
   *    genuine is the SNS signature plus the topic pin, both checked in
   *    `InboundMailboxWebhookView.post`. The secret column is reserved for
   *    providers that sign with a shared secret, none of which are
   *    implemented, and nothing in the backend compares it; see the card at
   *    the foot of the page, which used to say the opposite.
   * 2. An address that creates nothing does not bounce. It keeps accepting
   *    mail and the webhook stops opening cases, so the sender gets silence
   *    rather than a delivery failure. That is a materially different thing
   *    from "off", and a grey pill saying "Off" does not say it.
   *
   * The three ways an address creates nothing live in `./delivery.js`: turned
   * off, a provider the webhook does not implement, and an SES address whose
   * SNS subscription has never been confirmed. This page drew the last two as
   * "Creating tickets".
   */
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import SettingsFormPanel from '$lib/v2/components/SettingsFormPanel.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { count, relativeDays, relativeTime } from '$lib/v2/format.js';
  import { PRIORITY_TONE } from '$lib/v2/enums.js';
  import { mailboxProviderKey } from '$lib/settings/labels.js';
  import { casePriorityKey, caseTypeKey } from '$lib/cases/labels.js';
  import { missingOption, inactiveOptionLabel } from '$lib/v2/pickers.js';
  import {
    deliveryState,
    deliveryLabel,
    deliveryTone,
    deliveryExplanation,
    deliveringCount,
    silentMailboxes,
    providerChoiceLabel
  } from './delivery.js';
  import { Plus, MailWarning, KeyRound } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  // cases.InboundMailbox.PROVIDER_CHOICES is MAILBOX_PROVIDER_LABEL's key
  // order. PRIORITY_CHOICE and CASE_TYPE mirror ticket-approvals' own local
  // copies: value and label are the same string for both, and no shared map
  // exists to derive them from.
  const PROVIDERS = ['ses', 'mailgun', 'postmark', 'imap'];
  const PRIORITIES = ['Low', 'Normal', 'High', 'Urgent'];
  const CASE_TYPES = ['Question', 'Incident', 'Problem'];

  let totals = $derived(data.totals);
  let mailboxes = $derived(data.mailboxes);
  let delivering = $derived(deliveringCount(mailboxes));
  let silent = $derived(silentMailboxes(mailboxes));

  // `null` when the panel is closed, `'new'` when adding, or the mailbox
  // object when editing that row. One panel, two modes, so two rows can
  // never be open for edit at once.
  let editing = $state(/** @type {any} */ (null));

  // The provider select drives which fields render; the IMAP/SMTP fields are
  // bound so a preset can fill them in. Passwords are deliberately not here:
  // they are never loaded, and a blank one on submit means "keep it".
  let provider = $state('ses');
  let preset = $state('hosting');
  let server = $state(serverFields(null));
  let testing = $state(false);
  let testResult = $state(/** @type {any} */ (null));
  let testFailed = $state(false);

  /** @param {any} m */
  function serverFields(m) {
    return {
      imap_host: m?.imap_host ?? '',
      imap_port: m?.imap_port ?? 993,
      imap_security: m?.imap_security ?? 'ssl',
      imap_username: m?.imap_username ?? '',
      imap_folder: m?.imap_folder || 'INBOX',
      smtp_host: m?.smtp_host ?? '',
      smtp_port: m?.smtp_port ?? 587,
      smtp_security: m?.smtp_security ?? 'starttls',
      smtp_username: m?.smtp_username ?? ''
    };
  }

  // Google's own servers are fixed; a hosting provider's are not, so that
  // preset only sets the standard ports and leaves the hosts as typed.
  function applyPreset() {
    Object.assign(server, {
      imap_port: 993,
      imap_security: 'ssl',
      smtp_port: 587,
      smtp_security: 'starttls',
      ...(preset === 'google' ? { imap_host: 'imap.gmail.com', smtp_host: 'smtp.gmail.com' } : {})
    });
  }

  /** @param {any} m */
  function resetForm(m) {
    provider = m?.provider ?? 'ses';
    server = serverFields(m);
    preset = m?.imap_host === 'imap.gmail.com' ? 'google' : 'hosting';
    testResult = null;
    testFailed = false;
  }

  function openCreate() {
    editing = 'new';
    resetForm(null);
  }

  function openEdit(m) {
    editing = m;
    resetForm(m);
  }

  /** @param {MouseEvent & { currentTarget: HTMLButtonElement }} event */
  async function testConnection(event) {
    const formEl = event.currentTarget.form;
    if (!formEl) return;
    testing = true;
    testFailed = false;
    testResult = null;
    try {
      const res = await fetch(resolve('/settings/inbound-email/test-connection'), {
        method: 'POST',
        body: new FormData(formEl)
      });
      if (res.ok) testResult = await res.json();
      else testFailed = true;
    } catch {
      testFailed = true;
    } finally {
      testing = false;
    }
  }

  // The stored default assignee when the picker cannot offer it, because the
  // profile has been deactivated since it was chosen. `getOrgPeopleAndTeams`
  // returns active profiles only, `InboundMailbox.default_assignee` keeps
  // whoever was set. A select with no matching option submits nothing, which
  // `readValues` reads as `''` and `buildBody` sends as `null`, so an edit
  // made to change the address or the provider would also quietly move this
  // mailbox back to Unassigned.
  let missingAssignee = $derived(
    editing && editing !== 'new' ? missingOption(data.people, editing.default_assignee) : null
  );
</script>

<PageHeader title={$_('settings.inbound_email.title')}>
  {#snippet crumb()}<SettingsCrumb />{/snippet}
  {#snippet sub()}
    <span class="v2-num">{count(delivering)}</span>
    {$_('settings.inbound_email.sub_of')}
    <span class="v2-num">{count(totals.count)}</span>
    {$_('settings.inbound_email.sub_addresses')} ·
    <span class="v2-num">{count(totals.cases_last_30d)}</span>
    {$_('settings.inbound_email.sub_last_30')}
  {/snippet}
  {#snippet actions()}
    {#if data.can_edit && !editing}
      <button class="v2-btn v2-btn-primary" onclick={openCreate}>
        <Plus />{$_('settings.inbound_email.add_button')}
      </button>
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:18px;padding-bottom:32px">
    {#if editing}
      <SettingsFormPanel
        title={editing === 'new'
          ? $_('settings.inbound_email.form_new')
          : $_('settings.inbound_email.form_edit', { values: { address: editing.address } })}
        action={editing === 'new' ? '?/create' : '?/update'}
        error={editing === 'new' ? form?.create?.error : form?.update?.error}
        submitLabel={editing === 'new'
          ? $_('settings.inbound_email.add_address_button')
          : $_('settings.inbound_email.save_address_button')}
        oncancel={() => (editing = null)}
        ondone={() => (editing = null)}
      >
        {#snippet fields()}
          {#if editing !== 'new'}
            <input type="hidden" name="id" value={editing.id} />
          {/if}

          <div class="v2-field">
            <label for="m-address">{$_('settings.inbound_email.field_address')}</label>
            <input
              id="m-address"
              class="v2-input"
              type="email"
              name="address"
              required
              value={editing === 'new' ? '' : editing.address}
            />
            {#if editing !== 'new'}
              <p class="v2-hint">{$_('settings.inbound_email.address_hint')}</p>
            {/if}
          </div>

          <div class="v2-field">
            <label for="m-provider">{$_('settings.inbound_email.field_provider')}</label>
            <select id="m-provider" class="v2-input" name="provider" bind:value={provider}>
              {#each PROVIDERS as p (p)}
                {@const pc = providerChoiceLabel(p, $_(mailboxProviderKey(p)))}
                <option value={p}>{$_(pc.key, { values: pc.values })}</option>
              {/each}
            </select>
            <p class="v2-hint">{$_('settings.inbound_email.provider_hint')}</p>
          </div>

          {#if provider === 'imap'}
            {@const keepImap = editing !== 'new' && editing.has_imap_password}
            {@const keepSmtp = editing !== 'new' && editing.has_smtp_password}
            <div class="v2-field">
              <label for="m-preset">{$_('settings.inbound_email.server_preset')}</label>
              <select id="m-preset" class="v2-input" bind:value={preset} onchange={applyPreset}>
                <option value="hosting">{$_('settings.inbound_email.preset_hosting')}</option>
                <option value="google">{$_('settings.inbound_email.preset_google')}</option>
              </select>
              {#if preset === 'google'}
                <p class="v2-hint">{$_('settings.inbound_email.google_hint')}</p>
              {/if}
            </div>

            <div class="v2-label">{$_('settings.inbound_email.imap_heading')}</div>
            <div class="v2-mbx-server">
              <div class="v2-field v2-mbx-host">
                <label for="m-imap-host">{$_('settings.inbound_email.field_host')}</label>
                <input
                  id="m-imap-host"
                  class="v2-input"
                  name="imap_host"
                  required
                  bind:value={server.imap_host}
                />
              </div>
              <div class="v2-field">
                <label for="m-imap-port">{$_('settings.inbound_email.field_port')}</label>
                <input
                  id="m-imap-port"
                  class="v2-input"
                  type="number"
                  name="imap_port"
                  bind:value={server.imap_port}
                />
              </div>
              <div class="v2-field">
                <label for="m-imap-sec">{$_('settings.inbound_email.field_security')}</label>
                <select
                  id="m-imap-sec"
                  class="v2-input"
                  name="imap_security"
                  bind:value={server.imap_security}
                >
                  <option value="ssl">{$_('settings.inbound_email.security.ssl')}</option>
                  <option value="starttls">{$_('settings.inbound_email.security.starttls')}</option>
                </select>
              </div>
            </div>
            <div class="v2-field">
              <label for="m-imap-user">{$_('settings.inbound_email.field_username')}</label>
              <input
                id="m-imap-user"
                class="v2-input"
                name="imap_username"
                autocomplete="off"
                required
                bind:value={server.imap_username}
              />
            </div>
            <div class="v2-field">
              <label for="m-imap-pass">{$_('settings.inbound_email.field_password')}</label>
              <input
                id="m-imap-pass"
                class="v2-input"
                type="password"
                name="imap_password"
                autocomplete="new-password"
                required={!keepImap}
              />
              {#if keepImap}
                <p class="v2-hint">{$_('settings.inbound_email.password_keep_hint')}</p>
              {/if}
            </div>
            <div class="v2-field">
              <label for="m-imap-folder">{$_('settings.inbound_email.field_folder')}</label>
              <input
                id="m-imap-folder"
                class="v2-input"
                name="imap_folder"
                bind:value={server.imap_folder}
              />
              <p class="v2-hint">{$_('settings.inbound_email.first_poll_hint')}</p>
            </div>

            <div class="v2-label">{$_('settings.inbound_email.smtp_heading')}</div>
            <div class="v2-mbx-server">
              <div class="v2-field v2-mbx-host">
                <label for="m-smtp-host">{$_('settings.inbound_email.field_host')}</label>
                <input
                  id="m-smtp-host"
                  class="v2-input"
                  name="smtp_host"
                  required
                  bind:value={server.smtp_host}
                />
              </div>
              <div class="v2-field">
                <label for="m-smtp-port">{$_('settings.inbound_email.field_port')}</label>
                <input
                  id="m-smtp-port"
                  class="v2-input"
                  type="number"
                  name="smtp_port"
                  bind:value={server.smtp_port}
                />
              </div>
              <div class="v2-field">
                <label for="m-smtp-sec">{$_('settings.inbound_email.field_security')}</label>
                <select
                  id="m-smtp-sec"
                  class="v2-input"
                  name="smtp_security"
                  bind:value={server.smtp_security}
                >
                  <option value="ssl">{$_('settings.inbound_email.security.ssl')}</option>
                  <option value="starttls">{$_('settings.inbound_email.security.starttls')}</option>
                </select>
              </div>
            </div>
            <div class="v2-field">
              <label for="m-smtp-user">{$_('settings.inbound_email.field_username')}</label>
              <input
                id="m-smtp-user"
                class="v2-input"
                name="smtp_username"
                autocomplete="off"
                bind:value={server.smtp_username}
              />
            </div>
            <div class="v2-field">
              <label for="m-smtp-pass">{$_('settings.inbound_email.field_password')}</label>
              <input
                id="m-smtp-pass"
                class="v2-input"
                type="password"
                name="smtp_password"
                autocomplete="new-password"
              />
              <p class="v2-hint">
                {keepSmtp
                  ? $_('settings.inbound_email.password_keep_hint')
                  : $_('settings.inbound_email.smtp_same_hint')}
              </p>
            </div>

            <div class="v2-mbx-test">
              <button
                class="v2-btn v2-btn-sm"
                type="button"
                disabled={testing}
                onclick={testConnection}
              >
                {testing
                  ? $_('settings.inbound_email.testing')
                  : $_('settings.inbound_email.test_button')}
              </button>
              {#if testResult}
                {#each [['imap', 'imap_heading'], ['smtp', 'smtp_heading']] as [half, heading] (half)}
                  {@const r = testResult[half]}
                  <p class={r?.ok ? 'v2-sub' : 'v2-error'} style="margin:0;font-size:12px">
                    {$_(`settings.inbound_email.${heading}`)}:
                    {r?.ok
                      ? $_('settings.inbound_email.test_ok')
                      : $_('settings.inbound_email.test_failed', {
                          values: { error: r?.error ?? '' }
                        })}
                  </p>
                {/each}
              {/if}
              {#if testFailed}
                <p class="v2-error" style="margin:0;font-size:12px">
                  {$_('settings.inbound_email.test_error')}
                </p>
              {/if}
            </div>
          {/if}

          <div class="v2-field">
            <label for="m-priority">{$_('settings.inbound_email.field_priority')}</label>
            <select id="m-priority" class="v2-input" name="default_priority">
              {#each PRIORITIES as p (p)}
                <option
                  value={p}
                  selected={editing === 'new' ? p === 'Normal' : editing.default_priority === p}
                >
                  {$_(casePriorityKey(p))}
                </option>
              {/each}
            </select>
          </div>

          <div class="v2-field">
            <label for="m-type">{$_('settings.inbound_email.field_type')}</label>
            <select id="m-type" class="v2-input" name="default_case_type">
              <option value="" selected={editing === 'new' || !editing.default_case_type}>
                {$_('settings.inbound_email.type_none')}
              </option>
              {#each CASE_TYPES as t (t)}
                <option value={t} selected={editing !== 'new' && editing.default_case_type === t}>
                  {$_(caseTypeKey(t))}
                </option>
              {/each}
            </select>
          </div>

          <div class="v2-field">
            <label for="m-assignee">{$_('settings.inbound_email.field_assignee')}</label>
            <select id="m-assignee" class="v2-input" name="default_assignee_id">
              <option value="" selected={editing === 'new' || !editing.default_assignee}>
                {$_('settings.inbound_email.unassigned')}
              </option>
              {#if missingAssignee}
                <option value={missingAssignee.id} selected>
                  {inactiveOptionLabel(missingAssignee.name)}
                </option>
              {/if}
              {#each data.people as p (p.id)}
                <option
                  value={p.id}
                  selected={editing !== 'new' && editing.default_assignee?.id === p.id}
                >
                  {p.name}
                </option>
              {/each}
            </select>
            {#if missingAssignee}
              <p class="v2-hint">{$_('settings.inbound_email.assignee_inactive_hint')}</p>
            {/if}
          </div>

          {#if editing === 'new'}
            <div class="v2-field">
              <label for="m-active">{$_('settings.inbound_email.field_active')}</label>
              <label style="display:flex;gap:8px;align-items:center;font-weight:400">
                <input id="m-active" type="checkbox" name="is_active" value="true" checked />
                {$_('settings.inbound_email.active_help')}
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

    <!-- On, and creating nothing. A turned-off address is not in here: that
         state was chosen, and the row already reads correctly. These two were
         drawn as working right up until this banner existed. -->
    {#if silent.length}
      <div class="v2-mbx-banner">
        <MailWarning size={17} style="color:var(--v2-clay);flex:none;margin-top:1px" />
        <div>
          <div style="font-weight:600;font-size:13px">
            {$_('settings.inbound_email.silent_heading', {
              values: {
                addresses: silent.map((m) => m.address).join(', '),
                count: silent.length
              }
            })}
          </div>
          <p class="v2-sub" style="font-size:12px;margin:4px 0 0;line-height:1.5">
            {$_('settings.inbound_email.silent_body')}
          </p>
        </div>
      </div>
    {/if}

    <div class="v2-label" style="margin-bottom:10px">
      {$_('settings.inbound_email.section_addresses')}
    </div>
    <div style="display:flex;flex-direction:column;gap:9px">
      {#each mailboxes as m (m.id)}
        {@const state = deliveryState(m)}
        {@const why = deliveryExplanation(state, $_(mailboxProviderKey(m.provider)))}
        <div class="v2-card v2-mbx" style="opacity:{state === 'live' ? 1 : 0.68}">
          <div style="flex:1;min-width:0">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <b style="font-size:13.5px">{m.address}</b>
              <Pill tone={deliveryTone(state)}>{$_(deliveryLabel(state))}</Pill>
            </div>
            <div class="v2-sub" style="font-size:11.5px;margin-top:4px">
              {$_(mailboxProviderKey(m.provider))} ·
              {#if m.cases_last_30d}
                <span class="v2-num">{count(m.cases_last_30d)}</span>
                {$_('settings.inbound_email.tickets_in_30', {
                  values: { count: m.cases_last_30d }
                })}
                · {$_('settings.inbound_email.last_mail')}
                {relativeDays(m.last_received_at)}
              {:else}
                {$_('settings.inbound_email.no_tickets_in_30')} · {$_(
                  'settings.inbound_email.last_mail'
                )}
                {relativeDays(m.last_received_at)}
              {/if}
              {#if m.provider === 'imap'}
                ·
                {m.last_polled_at
                  ? $_('settings.inbound_email.last_checked', {
                      values: { when: relativeTime(m.last_polled_at) }
                    })
                  : $_('settings.inbound_email.never_checked')}
              {/if}
            </div>
            {#if data.can_edit && m.last_poll_error}
              <p class="v2-error" style="font-size:11.5px;margin:6px 0 0">
                {$_('settings.inbound_email.poll_error', { values: { error: m.last_poll_error } })}
              </p>
            {/if}
            {#if why}
              <p class="v2-sub" style="font-size:11.5px;margin:6px 0 0;line-height:1.5">
                {$_(why.key, { values: why.values })}
              </p>
            {/if}

            <!-- What a ticket from here starts out as. These are the defaults
                 a routing rule then reads, so they are worth stating next to
                 the address rather than behind an edit dialog. -->
            <div class="v2-mbx-defaults">
              <span class="v2-sub">{$_('settings.inbound_email.opens_as')}</span>
              <Pill tone={PRIORITY_TONE[m.default_priority]}>
                {$_(casePriorityKey(m.default_priority))}
              </Pill>
              {#if m.default_case_type}
                <Pill tone="slate">{$_(caseTypeKey(m.default_case_type))}</Pill>
              {/if}
              <span class="v2-sub">
                {m.default_assignee
                  ? $_('settings.inbound_email.assigned_to', {
                      values: { name: m.default_assignee.name }
                    })
                  : $_('settings.inbound_email.then_routed')}
              </span>
            </div>
          </div>

          {#if data.can_edit}
            <div style="display:flex;gap:6px;align-items:center;flex:none">
              <button class="v2-btn v2-btn-sm" type="button" onclick={() => openEdit(m)}>
                {$_('settings.inbound_email.edit_button')}
              </button>
              {#if m.is_active}
                <ConfirmAction
                  action="?/deactivate"
                  label={$_('settings.inbound_email.turn_off')}
                  confirmLabel={$_('settings.inbound_email.turn_off')}
                  explain={$_('settings.inbound_email.deactivate_explain')}
                  hidden={{ id: m.id }}
                />
              {:else}
                <form method="POST" action="?/activate" use:enhance>
                  <input type="hidden" name="id" value={m.id} />
                  <button class="v2-btn v2-btn-sm" type="submit">
                    {$_('settings.inbound_email.turn_on')}
                  </button>
                </form>
              {/if}
              <ConfirmAction
                action="?/remove"
                label={$_('settings.inbound_email.delete_button')}
                confirmLabel={$_('settings.inbound_email.delete_button')}
                explain={$_('settings.inbound_email.remove_explain')}
                hidden={{ id: m.id }}
              />
            </div>
          {/if}
        </div>
      {/each}
    </div>

    <!--
      What actually authenticates a delivery, which is not what this card used
      to claim. It described a per-address shared secret the server minted on
      create; the server mints nothing, nothing in the backend compares that
      column, and an admin reading the old wording would have believed their
      inbound mail was protected by a credential that is not in the path. The
      real pair, the SNS signature and the topic pin, is stated instead.
      Neither value is on this page in any form: not shown, not masked, not
      sitting in the payload behind a click-to-reveal, and no field for either
      on the form above.
    -->
    <!-- SES-only: an org receiving through its own IMAP server has no SNS
         delivery to prove, and a card about one would only confuse. -->
    {#if mailboxes.some((m) => m.provider === 'ses')}
      <div class="v2-card" style="padding:15px 16px;margin-top:20px">
        <div style="display:flex;gap:10px;align-items:flex-start">
          <KeyRound size={16} style="color:var(--v2-slate);flex:none;margin-top:2px" />
          <div>
            <div style="font-weight:600;font-size:13px">
              {$_('settings.inbound_email.proof_heading')}
            </div>
            <p class="v2-sub" style="font-size:12.5px;margin:5px 0 0;line-height:1.5">
              {$_('settings.inbound_email.proof_body1')}
            </p>
            <p class="v2-sub" style="font-size:12.5px;margin:8px 0 0;line-height:1.5">
              {$_('settings.inbound_email.proof_body2')}
            </p>
          </div>
        </div>
      </div>
    {/if}

    <p class="v2-sub" style="font-size:11.5px;margin-top:14px">
      {$_('settings.inbound_email.footer_before')}
      <a href={resolve('/settings/routing')} style="color:inherit"
        >{$_('settings.inbound_email.footer_link')}</a
      >{$_('settings.inbound_email.footer_after')}
    </p>
  </div>
</div>

<style>
  .v2-mbx {
    display: flex;
    gap: 13px;
    align-items: flex-start;
    padding: 14px 16px;
  }
  .v2-mbx-defaults {
    display: flex;
    gap: 6px;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 9px;
    font-size: 11.5px;
  }
  .v2-mbx-server {
    display: grid;
    grid-template-columns: 3fr 1fr 1.4fr;
    gap: 10px;
  }
  .v2-mbx-test {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  @media (max-width: 640px) {
    .v2-mbx-server {
      grid-template-columns: 1fr;
    }
  }
  .v2-mbx-banner {
    display: flex;
    gap: 11px;
    align-items: flex-start;
    padding: 14px 16px;
    margin-bottom: 18px;
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    background: var(--v2-card);
  }
</style>
