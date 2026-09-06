<script>
  /**
   * Your own API tokens.
   *
   * THE PAGE THAT WAS MISSING
   * `/api/profile/tokens/` has always been self-scoped and open to any member,
   * and until now nothing in either client called it. The only token page
   * either app had was the org-wide oversight list, which 403s a member on the
   * read, so a rep who wanted to script against their own CRM had to be handed
   * a token by an admin or reach for curl.
   *
   * WHAT IS DELIBERATELY ABSENT
   * No owner column, because every row is yours. No org totals, because you
   * cannot see anybody else's rows to count. No "revoke them all", because that
   * is an offboarding action and offboarding is the admin's page. Copying the
   * oversight layout here would draw an org-wide surface out of a self-scoped
   * one, and the first person to notice would be whoever tried it.
   *
   * A TOKEN VALUE IS SHOWN ONCE
   * The server keeps a SHA-256 hash and a 13-character prefix, so there is
   * nothing to re-display later even if somebody asks. The reveal below is the
   * only place a full value appears, and it is gone on the next load.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { count, relativeDays, shortDate } from '$lib/v2/format.js';
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { Plus, KeyRound, ShieldAlert, Copy, Check } from '@lucide/svelte';
  import { tokenStatus, EXPIRY_CHOICES } from '$lib/v2/token-rules.js';
  import { _ } from '$lib/i18n/index.js';
  import { tokenStateKey, tokenStalenessDescriptor, tokenExpiryKey } from '$lib/settings/labels.js';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let creating = $state(false);
  let busy = $state(false);
  let copied = $state(false);

  const working = () => {
    busy = true;
    return async (/** @type {any} */ { update }) => {
      await update();
      busy = false;
    };
  };

  const createSubmit = () => {
    busy = true;
    return async (/** @type {any} */ { update, result }) => {
      await update();
      busy = false;
      if (result?.type === 'success' && result?.data?.created) creating = false;
    };
  };

  /**
   * What a token may do, in the words this page uses. Mirrors `scopeSummary`
   * (`$lib/v2/token-rules.js`) but with the self-service page's "you" phrasing,
   * so it stays under `profile.tokens.*` rather than borrowing the settings
   * copy that names the owner.
   *
   * @param {any} t
   */
  function scopeText(t) {
    const scopes = t?.scopes ?? [];
    if (scopes.length === 0) return $_('profile.tokens.scope_everything_you');
    if (scopes.every((/** @type {string} */ s) => s.endsWith(':read'))) {
      return $_('profile.tokens.scope_read_only');
    }
    return $_('profile.tokens.scope_list', { values: { scopes: scopes.join(', ') } });
  }

  /** @param {string} value */
  async function copyToken(value) {
    try {
      await navigator.clipboard.writeText(value);
      copied = true;
      setTimeout(() => (copied = false), 1600);
    } catch {
      // Clipboard blocked (no https / no permission). The value is on screen to
      // select by hand, and there is nothing worth alarming over.
    }
  }
</script>

<PageHeader title={$_('profile.tokens.title')}>
  {#snippet crumb()}<a href={resolve('/profile')}>{$_('profile.tokens.crumb')}</a> ›{/snippet}
  {#snippet sub()}
    <span class="v2-num">{count(data.live)}</span>
    {$_('profile.tokens.sub_live_of')}
    <span class="v2-num">{count(data.tokens.length)}</span>
    {$_('profile.tokens.sub_issued')}
  {/snippet}
  {#snippet actions()}
    <button class="v2-btn v2-btn-primary" onclick={() => (creating = !creating)}>
      <Plus />{$_('profile.tokens.new_button')}
    </button>
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:18px;padding-bottom:32px">
    {#if form?.created?.token}
      <!-- The one and only time this value is shown. -->
      <div
        class="v2-card"
        style="padding:15px 16px;margin-bottom:18px;border-color:color-mix(in srgb, var(--v2-moss) 40%, var(--v2-line))"
      >
        <div style="font-weight:650;font-size:13px">
          {$_('profile.tokens.created_heading', { values: { name: form.created.name } })}
        </div>
        <p class="v2-sub" style="font-size:12px;margin:4px 0 10px">
          {$_('profile.tokens.created_body')}
        </p>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <code
            class="v2-num"
            style="flex:1;min-width:200px;background:var(--v2-bg-sunk);border:1px solid var(--v2-line);border-radius:var(--v2-radius);padding:9px 11px;font-size:12.5px;word-break:break-all"
          >
            {form.created.token}
          </code>
          <button class="v2-btn v2-btn-sm" onclick={() => copyToken(form.created.token)}>
            {#if copied}<Check size={13} />{$_('profile.tokens.copied')}{:else}<Copy
                size={13}
              />{$_('profile.tokens.copy')}{/if}
          </button>
        </div>
      </div>
    {/if}

    {#if form?.error}
      <div style="margin-bottom:16px">
        <NextAction label={$_('profile.tokens.error_label')} text={form.error} tone="rust" />
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
        <div style="flex:1;min-width:200px">
          <label class="v2-label" for="token-name" style="display:block;margin-bottom:4px">
            {$_('profile.tokens.form_name_label')}
          </label>
          <input
            id="token-name"
            name="name"
            required
            maxlength="255"
            class="v2-input"
            style="width:100%"
            placeholder={$_('profile.tokens.form_name_placeholder')}
          />
        </div>
        <div style="flex:1;min-width:160px">
          <label class="v2-label" for="token-access" style="display:block;margin-bottom:4px">
            {$_('profile.tokens.form_access_label')}
          </label>
          <select id="token-access" name="access" class="v2-input" style="width:100%">
            <option value="read" selected>{$_('profile.tokens.access_read')}</option>
            <!-- "Everything you can", not "everything": a token acts as you and
                 inherits your role, so it can never reach past what you can. -->
            <option value="full">{$_('profile.tokens.access_full')}</option>
          </select>
        </div>
        <div style="flex:1;min-width:140px">
          <label class="v2-label" for="token-expiry" style="display:block;margin-bottom:4px">
            {$_('profile.tokens.form_expiry_label')}
          </label>
          <select id="token-expiry" name="expiry" class="v2-input" style="width:100%">
            {#each EXPIRY_CHOICES as choice (choice.value)}
              <option value={choice.value}>{$_(tokenExpiryKey(choice.value))}</option>
            {/each}
          </select>
        </div>
        <button class="v2-btn v2-btn-primary" disabled={busy}
          >{$_('profile.tokens.form_submit')}</button
        >
        <button type="button" class="v2-btn" disabled={busy} onclick={() => (creating = false)}>
          {$_('profile.tokens.form_cancel')}
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

    {#if data.tokens.length === 0}
      <EmptyState title={$_('profile.tokens.empty_title')} body={$_('profile.tokens.empty_body')}>
        {#snippet icon()}<KeyRound size={21} />{/snippet}
        {#snippet actions()}
          <button class="v2-btn v2-btn-primary" onclick={() => (creating = true)}>
            {$_('profile.tokens.empty_action')}
          </button>
        {/snippet}
      </EmptyState>
    {:else}
      <div class="v2-table-wrap">
        <table class="v2-table">
          <thead>
            <tr>
              <th>{$_('profile.tokens.col_token')}</th>
              <th data-m="hide">{$_('profile.tokens.col_can_do')}</th>
              <th data-m="hide">{$_('profile.tokens.col_last_used')}</th>
              <th data-m="hide">{$_('profile.tokens.col_expires')}</th>
              <th class="v2-r">{$_('profile.tokens.col_state')}</th>
            </tr>
          </thead>
          <tbody>
            {#each data.tokens as t (t.id)}
              {@const s = tokenStatus(t)}
              {@const stale = tokenStalenessDescriptor(t)}
              <tr style={t.is_live ? '' : 'opacity:.55'}>
                <td data-m="title">
                  <span class="v2-table-primary">{t.name}</span>
                  <!-- The prefix, and only the prefix. The server keeps a hash. -->
                  <span class="v2-table-secondary v2-num" style="display:block">
                    {t.token_prefix}…
                  </span>
                </td>
                <td data-m="meta">
                  <span class="v2-sub" style="font-size:12px">
                    {scopeText(t)}
                  </span>
                </td>
                <td data-m="meta">
                  {#if t.last_used_at}
                    {relativeDays(t.last_used_at)}
                  {:else}
                    <span class="v2-muted">{$_('profile.tokens.last_used_never')}</span>
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
                    <span class="v2-sub">{$_('profile.tokens.never_expires')}</span>
                  {/if}
                </td>
                <td class="v2-r" data-m="tag">
                  <span style="display:inline-flex;gap:7px;align-items:center">
                    <Pill tone={s.tone}>{$_(tokenStateKey(t))}</Pill>
                    {#if t.is_live}
                      <form method="POST" action="?/revoke" use:enhance={working}>
                        <input type="hidden" name="id" value={t.id} />
                        <button class="v2-btn v2-btn-sm" disabled={busy}
                          >{$_('profile.tokens.revoke_button')}</button
                        >
                      </form>
                    {/if}
                  </span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <div
      style="display:flex;gap:10px;align-items:flex-start;margin-top:20px;padding:14px 16px;border:1px solid var(--v2-line);border-radius:var(--v2-radius)"
    >
      <ShieldAlert size={16} style="color:var(--v2-clay);flex:none;margin-top:1px" />
      <div>
        <div style="font-weight:600;font-size:13px">{$_('profile.tokens.warn_title')}</div>
        <p class="v2-sub" style="font-size:12px;margin:4px 0 0">
          {$_('profile.tokens.warn_body')}
        </p>
      </div>
    </div>
  </div>
</div>
