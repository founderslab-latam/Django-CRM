<script>
  /**
   * Personal access tokens: the org-wide oversight view.
   *
   * THE ONE RULE THIS PAGE EXISTS TO KEEP
   * A token value is shown once, in the response to the request that created
   * it, and never again. The server stores a SHA-256 hash plus a 13-character
   * prefix, so there is nothing to re-display even if someone asks. Every row
   * here shows the prefix and stops. The one-time reveal below is the only
   * place a full value ever appears, and it is gone on the next reload.
   *
   * WHO SEES THIS
   * This lists every token across the org, so it is admin-only: `/api/org/tokens/`
   * returns 403 to a member and the page renders "Admins only" rather than a
   * broken table. A consequence rather than a design: because this is the only
   * token page either client has, a member currently has no way to issue
   * themselves one. `/api/profile/tokens/` is open to them; nothing calls it on
   * their behalf. Recorded in `mobile/docs/PARITY.md`.
   *
   * "OWNER DEACTIVATED" IS A DORMANT ROW, NOT A LIVE ONE
   * The mock this page replaced claimed such a token "keeps working with the
   * role they had". It does not: deactivating an account sets profile.is_active
   * false, and that is exactly the flag the token authenticator checks, so the
   * token is refused at login today. It is worth revoking anyway. It would come
   * back if the account were reactivated, which is why it is surfaced in clay
   * (a loose end) rather than rust (a live breach).
   *
   * SCOPES ARE NOW REAL, AND THIS COMMENT USED TO SAY THE OPPOSITE
   * It read: "the model stores scopes for forward-compatibility but nothing
   * enforces them ... a UI that draws a tidy list of scopes would describe a
   * boundary that does not exist." That was true and worth saying. It stopped
   * being true when `common/scopes.py` landed and the middleware began
   * refusing out-of-scope requests before the view runs.
   *
   * So the form offers the choice, and the table names it per row. Two options,
   * not thirty: the backend grammar is `<resource>:<action>` and supports
   * `leads:read`, but a radio pair is the honest shape for a question most
   * people answer once, and "may this token change anything?" is the part that
   * matters. Anyone who wants finer scopes creates the token through the API.
   *
   * An empty scope list still means unrestricted, which is what every token
   * issued before enforcement carries. That is why the table says "Everything
   * <name> can" for those rows rather than pretending they are limited.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { count, relativeDays, shortDate } from '$lib/v2/format.js';
  import { roleKey } from '$lib/common/enums-labels.js';
  import {
    tokenStateKey,
    tokenScopeDescriptor,
    tokenStalenessDescriptor,
    tokenExpiryKey
  } from '$lib/settings/labels.js';
  import { enhance } from '$app/forms';
  import { Plus, ShieldAlert, Copy, Check } from '@lucide/svelte';
  import { tokenStatus, EXPIRY_CHOICES } from '$lib/v2/token-rules.js';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let totals = $derived(data.totals);

  let creating = $state(false);
  let busy = $state(false);
  let copied = $state(false);

  /** A submit handler that flips `busy` while the action runs. */
  const working = () => {
    busy = true;
    return async (/** @type {any} */ { update }) => {
      await update();
      busy = false;
    };
  };

  /** Create both submits and, on success, closes its own form. */
  const createSubmit = () => {
    busy = true;
    return async (/** @type {any} */ { update, result }) => {
      await update();
      busy = false;
      if (result?.type === 'success' && result?.data?.created) creating = false;
    };
  };

  /** @param {string} value */
  async function copyToken(value) {
    try {
      await navigator.clipboard.writeText(value);
      copied = true;
      setTimeout(() => (copied = false), 1600);
    } catch {
      // Clipboard blocked (no https / no permission). The value is on screen to
      // select by hand, nothing else to do, and no error worth alarming over.
    }
  }
</script>

{#if data.forbidden}
  <PageHeader title={$_('settings.api_tokens.title')}>
    {#snippet crumb()}<SettingsCrumb />{/snippet}
  </PageHeader>
  <div class="v2-pad" style="padding-top:40px">
    <NextAction
      label={$_('settings.api_tokens.forbidden_label')}
      text={$_('settings.api_tokens.forbidden_text')}
    />
  </div>
{:else}
  <PageHeader title={$_('settings.api_tokens.title')}>
    {#snippet crumb()}<SettingsCrumb />{/snippet}
    {#snippet sub()}
      <span class="v2-num">{count(totals.live)}</span>
      {$_('settings.api_tokens.sub_live_of')}
      <span class="v2-num">{count(totals.count)}</span>
      {$_('settings.api_tokens.sub_ever_issued')}
    {/snippet}
    {#snippet actions()}
      <button class="v2-btn v2-btn-primary" onclick={() => (creating = !creating)}>
        <Plus />{$_('settings.api_tokens.new_button')}
      </button>
    {/snippet}
  </PageHeader>

  <div class="v2-pad" style="padding-top:16px;flex:none">
    <div class="v2-stats">
      <StatCard label={$_('settings.api_tokens.stat_live')} value={count(totals.live)} tone="ink" />
      <StatCard
        label={$_('settings.api_tokens.stat_orphaned')}
        value={count(totals.orphaned)}
        tone={totals.orphaned ? 'clay' : 'slate'}
        detail={totals.orphaned
          ? $_('settings.api_tokens.stat_orphaned_detail')
          : $_('settings.api_tokens.detail_none')}
      />
      <StatCard
        label={$_('settings.api_tokens.stat_unused')}
        value={count(totals.unused_90d)}
        tone={totals.unused_90d ? 'clay' : 'slate'}
      />
      <StatCard
        label={$_('settings.api_tokens.stat_total')}
        value={count(totals.count)}
        tone="slate"
      />
    </div>
  </div>

  <div class="v2-scroll">
    <div class="v2-pad" style="padding-bottom:32px">
      {#if form?.created?.token}
        <!-- The one and only time this value is shown. On the next reload it is
             gone; the list will have the prefix and nothing more. -->
        <div
          class="v2-card"
          style="padding:15px 16px;margin-bottom:18px;border-color:color-mix(in srgb, var(--v2-moss) 40%, var(--v2-line))"
        >
          <div style="font-weight:650;font-size:13px">
            {$_('settings.api_tokens.created_heading', { values: { name: form.created.name } })}
          </div>
          <p class="v2-sub" style="font-size:12px;margin:4px 0 10px">
            {$_('settings.api_tokens.created_body')}
          </p>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
            <code
              class="v2-num"
              style="flex:1;min-width:220px;background:var(--v2-bg-sunk);border:1px solid var(--v2-line);border-radius:var(--v2-radius);padding:9px 11px;font-size:12.5px;word-break:break-all"
            >
              {form.created.token}
            </code>
            <button class="v2-btn v2-btn-sm" onclick={() => copyToken(form.created.token)}>
              {#if copied}<Check size={13} />{$_('settings.api_tokens.copied')}{:else}<Copy
                  size={13}
                />{$_('settings.api_tokens.copy')}{/if}
            </button>
          </div>
        </div>
      {/if}

      {#if form?.revokedOrphaned}
        <p
          class="v2-sub"
          style="color:var(--v2-moss);font-size:12.5px;margin:0 0 16px;font-weight:550"
        >
          {$_('settings.api_tokens.revoked_orphaned_result', {
            values: { count: form.revokedOrphaned }
          })}
        </p>
      {:else if form?.error}
        <div style="margin-bottom:16px">
          <NextAction label={$_('settings.api_tokens.error_label')} text={form.error} tone="rust" />
        </div>
      {/if}

      {#if creating}
        <form
          method="POST"
          action="?/create"
          use:enhance={createSubmit}
          class="v2-card"
          style="padding:14px 15px;margin-bottom:18px;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap"
        >
          <div style="flex:1;min-width:220px">
            <label class="v2-label" for="token-name" style="display:block;margin-bottom:4px">
              {$_('settings.api_tokens.form_name_label')}
            </label>
            <input
              id="token-name"
              name="name"
              required
              maxlength="255"
              class="v2-input"
              style="width:100%"
              placeholder={$_('settings.api_tokens.form_name_placeholder')}
            />
          </div>
          <div>
            <label class="v2-label" for="token-access" style="display:block;margin-bottom:4px">
              {$_('settings.api_tokens.form_access_label')}
            </label>
            <select id="token-access" name="access" class="v2-input" style="width:180px">
              <option value="read" selected>{$_('settings.api_tokens.access_read')}</option>
              <option value="full">{$_('settings.api_tokens.access_full')}</option>
            </select>
          </div>
          <div>
            <label class="v2-label" for="token-expiry" style="display:block;margin-bottom:4px">
              {$_('settings.api_tokens.form_expiry_label')}
            </label>
            <select id="token-expiry" name="expiry" class="v2-input" style="width:150px">
              {#each EXPIRY_CHOICES as choice (choice.value)}
                <option value={choice.value}>{$_(tokenExpiryKey(choice.value))}</option>
              {/each}
            </select>
          </div>
          <button class="v2-btn v2-btn-primary" disabled={busy}>
            {$_('settings.api_tokens.form_submit')}
          </button>
          <button type="button" class="v2-btn" disabled={busy} onclick={() => (creating = false)}>
            {$_('settings.api_tokens.form_cancel')}
          </button>
          {#if form?.create?.error}
            <p
              class="v2-sub"
              style="color:var(--v2-rust);font-size:12px;flex-basis:100%;margin:2px 0 0"
            >
              {form.create.error}
            </p>
          {/if}
        </form>
      {/if}

      {#if totals.orphaned}
        <div style="margin-bottom:18px">
          <NextAction
            label={$_('settings.api_tokens.loose_end_label')}
            text={$_('settings.api_tokens.loose_end_text', { values: { count: totals.orphaned } })}
          />
          <form
            method="POST"
            action="?/revokeOrphaned"
            use:enhance={working}
            style="margin-top:10px"
          >
            <button class="v2-btn v2-btn-primary" disabled={busy}>
              {$_('settings.api_tokens.revoke_orphaned_button', {
                values: { count: totals.orphaned }
              })}
            </button>
          </form>
        </div>
      {/if}

      <div class="v2-table-wrap">
        <table class="v2-table">
          <thead>
            <tr>
              <th>{$_('settings.api_tokens.col_token')}</th>
              <th>{$_('settings.api_tokens.col_owner')}</th>
              <th data-m="hide">{$_('settings.api_tokens.col_can_do')}</th>
              <th data-m="hide">{$_('settings.api_tokens.col_last_used')}</th>
              <th data-m="hide">{$_('settings.api_tokens.col_expires')}</th>
              <th class="v2-r">{$_('settings.api_tokens.col_state')}</th>
            </tr>
          </thead>
          <tbody>
            {#each data.tokens as t (t.id)}
              {@const s = tokenStatus(t)}
              {@const stale = tokenStalenessDescriptor(t)}
              {@const scope = tokenScopeDescriptor(t)}
              {@const owner = t.owner ?? {}}
              <tr style={t.is_live ? '' : 'opacity:.55'}>
                <td>
                  <span class="v2-table-primary">{t.name}</span>
                  <!-- The prefix, and only the prefix. There is no full value to
                       show: the server keeps a hash. -->
                  <span class="v2-table-secondary v2-num" style="display:block">
                    {t.token_prefix}…
                  </span>
                </td>
                <td data-m="meta">
                  {owner.name}
                  <span class="v2-table-secondary" style="display:block">
                    {owner.role ? $_(roleKey(owner.role)) : owner.role}{owner.is_active === false
                      ? $_('settings.api_tokens.owner_deactivated_suffix')
                      : ''}
                  </span>
                </td>
                <td data-m="hide">
                  <span class="v2-sub" style="font-size:12px"
                    >{$_(scope.key, { values: scope.values })}</span
                  >
                </td>
                <td data-m="hide">
                  {#if t.last_used_at}
                    {relativeDays(t.last_used_at)}
                  {:else}
                    <span class="v2-muted">{$_('settings.api_tokens.last_used_never')}</span>
                  {/if}
                  {#if stale}
                    <span
                      class="v2-table-secondary"
                      style="display:block;color:var(--v2-clay);font-weight:600"
                    >
                      {$_(stale.key, { values: stale.values })}
                    </span>
                  {/if}
                </td>
                <td data-m="hide">
                  {#if t.expires_at}
                    {shortDate(t.expires_at)}
                  {:else}
                    <span class="v2-sub">{$_('settings.api_tokens.never_expires')}</span>
                  {/if}
                </td>
                <td class="v2-r">
                  <span style="display:inline-flex;gap:7px;align-items:center">
                    <Pill tone={s.tone}>{$_(tokenStateKey(t))}</Pill>
                    {#if t.is_live}
                      <form method="POST" action="?/revoke" use:enhance={working}>
                        <input type="hidden" name="id" value={t.id} />
                        <button class="v2-btn v2-btn-sm" disabled={busy}>
                          {$_('settings.api_tokens.revoke_button')}
                        </button>
                      </form>
                    {/if}
                  </span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div
        style="display:flex;gap:10px;align-items:flex-start;margin-top:20px;padding:14px 16px;border:1px solid var(--v2-line);border-radius:var(--v2-radius)"
      >
        <ShieldAlert size={16} style="color:var(--v2-clay);flex:none;margin-top:1px" />
        <div>
          <div style="font-weight:600;font-size:13px">
            {$_('settings.api_tokens.footer_heading')}
          </div>
          <p class="v2-sub" style="font-size:12px;margin:4px 0 0">
            {$_('settings.api_tokens.footer_body')}
          </p>
        </div>
      </div>
    </div>
  </div>
{/if}
