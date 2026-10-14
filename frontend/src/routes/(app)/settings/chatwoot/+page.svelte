<script>
  /**
   * The org's Chatwoot account: credentials for Live Chat + WhatsApp, kept
   * apart from any one person's own Chatwoot login. Admin-only, same posture
   * as `/settings/organization/edit`: a non-admin who reaches this URL gets
   * an "Admins only" state, and the actual refusal is the backend's
   * (`ChatwootAccountView` checks `is_org_admin` before every write).
   *
   * One row per org, never a list: the form is always the current state,
   * not an "add" panel toggled open. `api_access_token` never arrives from
   * the server at all (`has_api_access_token` is a boolean, not the value),
   * so leaving the field blank on save means "leave it alone" -- it is never
   * possible to accidentally overwrite a real token with an empty one by
   * submitting the form without having typed into it.
   */
  import { untrack } from 'svelte';
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { TriangleAlert, Copy, Check } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form: result } = $props();

  const account = untrack(() => data.account ?? null);

  let form = $state({
    base_url: account?.base_url ?? '',
    account_id: account?.account_id != null ? String(account.account_id) : '',
    api_access_token: '',
    seat_limit: account?.seat_limit != null ? String(account.seat_limit) : '3',
    is_active: String(account?.is_active ?? true)
  });

  let copied = $state(false);
  /** @param {string} text */
  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch {
      // Clipboard access can be denied (permissions, non-HTTPS context in
      // dev); the URL is still selectable text, so there's nothing to recover.
    }
  }
</script>

{#if !data.can_edit}
  <PageHeader title={$_('settings.chatwoot.forbidden_title')}>
    {#snippet crumb()}<SettingsCrumb />{/snippet}
  </PageHeader>
  <div class="v2-pad" style="padding-top:40px">
    <NextAction
      label={$_('settings.chatwoot.forbidden_label')}
      text={$_('settings.chatwoot.forbidden_text')}
    />
  </div>
{:else}
  <PageHeader title={$_('settings.chatwoot.title')}>
    {#snippet crumb()}<SettingsCrumb />{/snippet}
  </PageHeader>

  <div class="v2-scroll v2-pad" style="padding-top:18px;max-width:560px">
    <p class="v2-hint" style="margin:-4px 0 18px">
      {$_('settings.chatwoot.intro')}
    </p>

    {#if result?.save?.error || result?.remove?.error}
      <div
        class="v2-next"
        style="background:color-mix(in srgb, var(--v2-rust) 9%, transparent);border-color:color-mix(in srgb, var(--v2-rust) 28%, transparent);margin-bottom:18px"
        role="alert"
      >
        <TriangleAlert size={17} style="color:var(--v2-rust);flex:none" />
        <div class="v2-next-body">
          <div class="v2-sub">{result.save?.error ?? result.remove?.error}</div>
        </div>
      </div>
    {/if}

    {#if account}
      <div class="v2-field">
        <label for="f-webhook">{$_('settings.chatwoot.webhook_url_label')}</label>
        <div style="display:flex;gap:8px">
          <input id="f-webhook" class="v2-input" readonly value={account.webhook_url} />
          <button
            type="button"
            class="v2-btn v2-btn-sm"
            onclick={() => copy(account.webhook_url)}
            aria-label={$_('settings.chatwoot.copy_webhook_url')}
          >
            {#if copied}<Check size={14} />{:else}<Copy size={14} />{/if}
          </button>
        </div>
        <p class="v2-hint">{$_('settings.chatwoot.webhook_url_hint')}</p>
      </div>
    {/if}

    <form
      class="v2-form"
      method="POST"
      action="?/save"
      use:enhance={() => {
        return async ({ update }) => {
          await update({ reset: false });
        };
      }}
    >
      <div class="v2-field">
        <label for="f-base-url">{$_('settings.chatwoot.base_url_label')}</label>
        <input
          id="f-base-url"
          name="base_url"
          class="v2-input"
          placeholder="https://chat.founderslab.cloud"
          bind:value={form.base_url}
          required
        />
        <p class="v2-hint">{$_('settings.chatwoot.base_url_hint')}</p>
      </div>

      <div class="v2-field">
        <label for="f-account-id">{$_('settings.chatwoot.account_id_label')}</label>
        <input
          id="f-account-id"
          name="account_id"
          type="number"
          min="1"
          class="v2-input"
          bind:value={form.account_id}
          required
        />
        <p class="v2-hint">{$_('settings.chatwoot.account_id_hint')}</p>
      </div>

      <div class="v2-field">
        <label for="f-token">{$_('settings.chatwoot.token_label')}</label>
        <input
          id="f-token"
          name="api_access_token"
          type="password"
          class="v2-input"
          placeholder={account?.has_api_access_token
            ? $_('settings.chatwoot.token_placeholder_set')
            : $_('settings.chatwoot.token_placeholder_unset')}
          bind:value={form.api_access_token}
          autocomplete="off"
        />
        <p class="v2-hint">{$_('settings.chatwoot.token_hint')}</p>
      </div>

      <div class="v2-field">
        <label for="f-seats">{$_('settings.chatwoot.seat_limit_label')}</label>
        <input
          id="f-seats"
          name="seat_limit"
          type="number"
          min="1"
          class="v2-input"
          style="max-width:120px"
          bind:value={form.seat_limit}
        />
        <p class="v2-hint">{$_('settings.chatwoot.seat_limit_hint')}</p>
      </div>

      <div class="v2-field">
        <label for="f-active">{$_('settings.chatwoot.active_label')}</label>
        <select id="f-active" name="is_active" class="v2-input" bind:value={form.is_active}>
          <option value="true">{$_('settings.chatwoot.active_on')}</option>
          <option value="false">{$_('settings.chatwoot.active_off')}</option>
        </select>
        <p class="v2-hint">{$_('settings.chatwoot.active_hint')}</p>
      </div>

      <div class="actions">
        <button class="v2-btn v2-btn-primary" type="submit">
          {$_('settings.chatwoot.save')}
        </button>
      </div>
    </form>

    {#if account}
      <div class="v2-label" style="margin:28px 0 10px">
        {$_('settings.chatwoot.danger_heading')}
      </div>
      <div class="v2-card" style="padding:15px 16px;display:flex;align-items:center;gap:12px">
        <p class="v2-sub" style="flex:1;margin:0">{$_('settings.chatwoot.disconnect_explain')}</p>
        <ConfirmAction
          action="?/remove"
          label={$_('settings.chatwoot.disconnect')}
          confirmLabel={$_('common.actions.confirm')}
          explain={$_('settings.chatwoot.disconnect_explain')}
        />
      </div>
    {/if}
  </div>
{/if}

<style>
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 6px;
  }
</style>
