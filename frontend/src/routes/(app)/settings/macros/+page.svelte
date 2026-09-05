<script>
  /**
   * Canned replies.
   *
   * The body is the whole point of a macro, so it is on the page. V1 hides it
   * behind an edit dialog and lists titles, which means you cannot tell two
   * similarly-named macros apart without opening both.
   *
   * Placeholders are marked inline. `%customer_name%` is substituted by the
   * server; anything outside its seven supported tokens is left literal and
   * goes to the customer exactly as typed. That is the failure this page
   * exists to make visible: `%custmer_name%` has shipped twelve times.
   *
   * The body is org-authored text and is rendered as TEXT, split into
   * segments and placed in elements, never through {@html}. A canned reply is
   * a string a colleague wrote; putting it in the DOM as markup would make the
   * macro editor a stored-XSS form.
   *
   * PERMISSIONS, WHICH ARE NOT ROLE-GATED THE WAY THE REST OF SETTINGS IS
   * Every signed-in member may create, edit and delete their own `personal`
   * macros; only an admin may do any of that to an `org`-scope one.
   * `data.can_create_org` and `data.my_profile_id` are display hints decoded
   * server-side from the JWT (see `macros.js`'s `getMacros`), never the
   * authorization: the backend re-derives both and is what actually decides
   * whether a write succeeds. `canWrite` below mirrors that split so a row
   * only offers Edit/Delete when the click would not just come back as an
   * error.
   */
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import SettingsFormPanel from '$lib/v2/components/SettingsFormPanel.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { count, relativeDays } from '$lib/v2/format.js';
  import { macroScopeKey } from '$lib/settings/labels.js';
  import { Plus, TriangleAlert } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  // `null` when the panel is closed, `'new'` when adding, or the macro
  // object when editing that row. One panel, two modes, so two rows can
  // never be open for edit at once.
  let editing = $state(/** @type {any} */ (null));

  // The scope currently selected in the form. Bound separately from `editing`
  // so the select works the same way in both modes: seeded from the row on
  // edit, defaulted to 'personal' on create, since every member can make a
  // personal macro but not every member can make an org one.
  let scope = $state('personal');

  function openCreate() {
    editing = 'new';
    scope = 'personal';
  }

  function openEdit(m) {
    editing = m;
    scope = m.scope;
  }

  /**
   * May the signed-in viewer write this row. An org macro is writable only
   * by an admin (`data.can_create_org`); a personal macro is writable only
   * by its owner, compared by Profile id (`m.owner.id`, from `getMacros`'s
   * reshape, against `data.my_profile_id`). This is a display decision, not
   * an authorization one: the backend enforces the same split independently
   * (403 on someone else's org macro, 404 on someone else's personal one)
   * and would refuse the write even if this returned true by mistake.
   */
  function canWrite(m) {
    return m.scope === 'org' ? data.can_create_org : m.owner?.id === data.my_profile_id;
  }

  let totals = $derived(data.totals);
  let byUse = $derived([...data.macros].sort((a, b) => b.usage_count - a.usage_count));
  let orgMacros = $derived(byUse.filter((m) => m.scope === 'org'));
  let personalMacros = $derived(byUse.filter((m) => m.scope === 'personal'));

  /**
   * Split a body into text and placeholder segments for rendering.
   *
   * Whether a token is real is decided by the server's `unknown_placeholders`,
   * not by matching against a list kept here. The supported set lives in
   * `macros/render.py` precisely so clients cannot drift from it. A copy in
   * this file would eventually mark a working macro as broken.
   */
  function segments(macro) {
    const re = /%[a-zA-Z_][a-zA-Z0-9_]*%/g;
    const out = [];
    let last = 0;
    let m;
    while ((m = re.exec(macro.body)) !== null) {
      if (m.index > last) out.push({ text: macro.body.slice(last, m.index), token: false });
      out.push({
        text: m[0],
        token: true,
        known: !macro.unknown_placeholders.includes(m[0])
      });
      last = m.index + m[0].length;
    }
    if (last < macro.body.length) out.push({ text: macro.body.slice(last), token: false });
    return out;
  }
</script>

<PageHeader title={$_('settings.macros.title')}>
  {#snippet crumb()}<SettingsCrumb />{/snippet}
  {#snippet sub()}
    <span class="v2-num">{count(totals.org)}</span>
    {$_('settings.macros.sub_shared', { values: { count: totals.org } })} ·
    <span class="v2-num">{count(totals.personal)}</span>
    {$_('settings.macros.sub_yours', { values: { count: totals.personal } })}
  {/snippet}
  {#snippet actions()}
    {#if !editing}
      <button class="v2-btn v2-btn-primary" onclick={openCreate}>
        <Plus />{$_('settings.macros.new_button')}
      </button>
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-pad" style="padding-top:16px;flex:none">
  <div class="v2-stats">
    <StatCard label={$_('settings.macros.stat_shared')} value={count(totals.org)} tone="ink" />
    <StatCard
      label={$_('settings.macros.stat_yours')}
      value={count(totals.personal)}
      tone="slate"
    />
    <StatCard
      label={$_('settings.macros.stat_broken')}
      value={count(totals.with_unknown_placeholders)}
      tone={totals.with_unknown_placeholders > 0 ? 'rust' : 'slate'}
      detail={$_('settings.macros.stat_broken_detail')}
    />
    <StatCard label={$_('settings.macros.stat_off')} value={count(totals.inactive)} tone="slate" />
  </div>
</div>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-bottom:32px">
    {#if editing}
      <SettingsFormPanel
        title={editing === 'new'
          ? $_('settings.macros.form_new')
          : $_('settings.macros.form_edit', { values: { title: editing.title } })}
        action={editing === 'new' ? '?/create' : '?/update'}
        error={editing === 'new' ? form?.create?.error : form?.update?.error}
        submitLabel={editing === 'new'
          ? $_('settings.macros.add_button')
          : $_('settings.macros.save_button')}
        oncancel={() => (editing = null)}
        ondone={() => (editing = null)}
      >
        {#snippet fields()}
          {#if editing !== 'new'}
            <input type="hidden" name="id" value={editing.id} />
          {/if}

          <div class="v2-field">
            <label for="m-title">{$_('settings.macros.field_title')}</label>
            <input
              id="m-title"
              class="v2-input"
              name="title"
              maxlength="255"
              required
              value={editing === 'new' ? '' : editing.title}
            />
          </div>

          <div class="v2-field">
            <label for="m-scope">{$_('settings.macros.field_scope')}</label>
            <select id="m-scope" class="v2-input" name="scope" bind:value={scope}>
              <option value="personal">{$_('settings.macros.scope_personal')}</option>
              {#if data.can_create_org}
                <option value="org">{$_('settings.macros.scope_org')}</option>
              {/if}
            </select>
            {#if !data.can_create_org}
              <p class="v2-hint">{$_('settings.macros.scope_hint')}</p>
            {/if}
          </div>

          <div class="v2-field v2-sfp-wide">
            <label for="m-body">{$_('settings.macros.field_body')}</label>
            <textarea id="m-body" class="v2-input" name="body" rows="5" required
              >{editing === 'new' ? '' : editing.body}</textarea
            >
            <p class="v2-hint">{$_('settings.macros.body_hint')}</p>
          </div>
        {/snippet}
      </SettingsFormPanel>
    {/if}

    {#if form?.delete?.error}
      <p class="v2-error" style="margin-bottom:12px">{form.delete.error}</p>
    {/if}
    {#if form?.activate?.error}
      <p class="v2-error" style="margin-bottom:12px">{form.activate.error}</p>
    {/if}

    <div class="v2-split-wide">
      <div>
        <div class="v2-label" style="margin-bottom:10px">
          {$_('settings.macros.section_shared')}
        </div>
        <div style="display:flex;flex-direction:column;gap:9px;margin-bottom:24px">
          {#each orgMacros as m (m.id)}
            {@render macro(m)}
          {/each}
        </div>

        <div class="v2-label" style="margin-bottom:10px">{$_('settings.macros.section_yours')}</div>
        <div style="display:flex;flex-direction:column;gap:9px">
          {#each personalMacros as m (m.id)}
            {@render macro(m)}
          {/each}
        </div>
        <p class="v2-sub" style="font-size:11.5px;margin-top:11px">
          {$_('settings.macros.personal_note')}
        </p>
      </div>

      <div>
        <div class="v2-label" style="margin-bottom:10px">
          {$_('settings.macros.section_placeholders')}
        </div>
        <div class="v2-card" style="overflow:hidden">
          {#each data.placeholders as p (p.token)}
            <div class="v2-setting" style="padding:10px 15px">
              <div class="v2-setting-body">
                <code class="v2-token">{p.token}</code>
              </div>
              <span class="v2-sub" style="font-size:11.5px;text-align:right">{p.resolves}</span>
            </div>
          {/each}
        </div>
        <p class="v2-sub" style="font-size:11.5px;margin-top:11px;line-height:1.5">
          {$_('settings.macros.placeholders_note')}
        </p>
      </div>
    </div>
  </div>
</div>

{#snippet macro(m)}
  <div class="v2-card" style="padding:14px 16px;opacity:{m.is_active ? 1 : 0.62}">
    <div style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap">
      <b style="font-size:13.5px">{m.title}</b>
      {#if !m.is_active}<Pill tone="slate">{$_('settings.macros.pill_off')}</Pill>{/if}
      {#if m.unknown_placeholders.length}
        <Pill tone="rust">{$_('settings.macros.pill_broken')}</Pill>
      {/if}
      <span class="v2-sub" style="font-size:11.5px;margin-left:auto">
        {$_('settings.macros.used_prefix')}
        <span class="v2-num">{count(m.usage_count)}</span>
        {$_('settings.macros.used_suffix', { values: { count: m.usage_count } })} · {relativeDays(
          m.updated_at
        )}
      </span>
    </div>

    <!--
      Text nodes and spans, never {@html}.

      Written on one line and held there by prettier-ignore. Svelte collapses
      the newline and indentation between two inline children into a single
      space, so a formatted version of this block renders "%customer_name% ,".
      A space the macro does not contain, in a preview whose whole job is to
      show exactly what the customer receives.
    -->
    <!-- prettier-ignore -->
    <p class="v2-macro-body">{#each segments(m) as seg, i (i)}{#if seg.token}<span class="v2-token" class:v2-token-bad={!seg.known}>{seg.text}</span>{:else}{seg.text}{/if}{/each}</p>

    {#if m.unknown_placeholders.length}
      <div class="v2-macro-flag">
        <TriangleAlert size={14} style="color:var(--v2-rust);flex:none" />
        <span>
          {$_('settings.macros.unknown_flag', {
            values: {
              tokens: m.unknown_placeholders.join(` ${$_('settings.macros.join_and')} `),
              count: m.unknown_placeholders.length
            }
          })}
          {#if m.usage_count > 0}
            {$_('settings.macros.unknown_sent_before')}
            <span class="v2-num">{count(m.usage_count)}</span>
            {$_('settings.macros.unknown_sent_after')}
          {/if}
        </span>
      </div>
    {/if}

    {#if m.owner}
      <div class="v2-sub" style="font-size:11px;margin-top:8px">
        {$_(macroScopeKey(m.scope))} · {m.owner.name}
      </div>
    {/if}

    {#if canWrite(m)}
      <div style="display:flex;gap:6px;align-items:center;justify-content:flex-end;margin-top:10px">
        <button class="v2-btn v2-btn-sm" type="button" onclick={() => openEdit(m)}>
          {$_('settings.macros.edit_button')}
        </button>
        {#if !m.is_active}
          <!-- Turning a macro back on restores nothing that was destroyed, so
               unlike "Turn off"/"Delete" this doesn't need the two-click
               confirm. A plain enhanced form posting just the id keeps the
               request to `{ is_active: true }`; see `activateMacro`'s
               comment for why that has to bypass `updateMacro` rather than
               reuse it. Offered for both scopes on purpose: an org row gets
               here by "Turn off" (soft), a personal row can only be inactive
               from data written before the edit form stopped carrying
               `is_active`, and either way `_get_writable` still enforces
               admin-only for org / owner-only for personal server-side, so
               this can never write a row `canWrite` above disagrees with. -->
          <form method="POST" action="?/activate" use:enhance>
            <input type="hidden" name="id" value={m.id} />
            <button class="v2-btn v2-btn-sm" type="submit">{$_('settings.macros.turn_on')}</button>
          </form>
        {:else if m.scope === 'org'}
          <!-- `MacroDetailView.delete` soft-deletes an org macro: it flips
               `is_active` and leaves the row (and its usage count) in place.
               "Turn off", not "Delete", says what actually happens. -->
          <ConfirmAction
            action="?/delete"
            label={$_('settings.macros.turn_off')}
            confirmLabel={$_('settings.macros.turn_off')}
            explain={$_('settings.macros.turn_off_explain_org')}
            hidden={{ id: m.id }}
          />
        {:else}
          <!-- A personal macro is hard-deleted, not soft-deactivated: this
               button removes the row outright, so once it's gone there is
               nothing left to turn back on. -->
          <ConfirmAction
            action="?/delete"
            label={$_('settings.macros.delete_button')}
            confirmLabel={$_('settings.macros.delete_button')}
            explain={$_('settings.macros.delete_explain')}
            hidden={{ id: m.id }}
          />
        {/if}
      </div>
    {/if}
  </div>
{/snippet}

<style>
  .v2-macro-body {
    font-size: 12.5px;
    color: var(--v2-slate);
    line-height: 1.55;
    white-space: pre-wrap;
    margin: 9px 0 0;
  }
  .v2-token {
    font-family: var(--v2-mono);
    font-size: 11.5px;
    background: var(--v2-hover);
    border-radius: 3px;
    padding: 1px 4px;
    color: var(--v2-ink);
  }
  /* No side padding inside a body preview. Four pixels either side renders
     "%customer_name% ,". A space the macro does not contain, on a screen
     whose only job is to show exactly what the customer will receive. The
     background alone is enough to mark it. */
  .v2-macro-body .v2-token {
    padding: 1px 0;
  }
  /* Rust, not ember: a broken placeholder is a fact about the macro, not a
     button. Ember stays reserved for things you act on. */
  .v2-token-bad {
    color: var(--v2-rust);
    text-decoration: underline wavy;
    text-underline-offset: 2px;
  }
  .v2-macro-flag {
    display: flex;
    gap: 7px;
    align-items: flex-start;
    margin-top: 10px;
    font-size: 12px;
    color: var(--v2-slate);
    line-height: 1.45;
  }
</style>
