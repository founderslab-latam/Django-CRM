<script>
  import { resolve } from '$app/paths';
  /**
   * Your own account.
   *
   * The fields that are NOT editable here are the interesting ones. Role is
   * shown and cannot be changed from this page. The API refuses to let anyone
   * change their own role (ProfileSelfUpdateSerializer names only name and
   * phone), and an input that always fails is worse than no input. Same for the
   * organisation: which org you are in decides which rows you can see at all,
   * and it comes from the JWT, not from a form.
   *
   * Two things you CAN do: edit your name and phone (PATCH /profile/), and
   * switch org, a real action that re-issues the token rather than editing a
   * field, so it goes through its own action and the copy says so.
   */
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import { relativeDays, shortDate, count } from '$lib/v2/format.js';
  import { ROLE_TONE } from '$lib/v2/enums.js';
  import { roleKey } from '$lib/common/enums-labels.js';
  import { _ } from '$lib/i18n/index.js';
  import { KeyRound, Lock, ArrowLeftRight } from '@lucide/svelte';
  import LanguageSwitcher from '$lib/v2/components/LanguageSwitcher.svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let p = $derived(data.profile);
  let name = $derived(`${p.user_details.first_name} ${p.user_details.last_name}`.trim());

  // Editing name + phone. The backend stores one `name` on User, so the form
  // offers a single full-name field rather than the split the header renders.
  let editing = $state(false);
  let editName = $state('');
  let editPhone = $state('');

  function openEdit() {
    editName = name;
    editPhone = p.phone || '';
    editing = true;
  }

  const onEdit = (/** @type {any} */ { formData }) => {
    // Only send the field the person actually changed. The PATCH treats an
    // absent field as "leave it alone", so an untouched phone is not
    // re-validated, which matters because some seeded numbers carry an
    // extension the validator rejects, and re-sending one would block a plain
    // name change. Same rule the leads form uses for its owner select.
    if ((formData.get('name') ?? '') === name) formData.delete('name');
    if ((formData.get('phone') ?? '') === (p.phone || '')) formData.delete('phone');

    return async (/** @type {any} */ { result, update }) => {
      if (result.type === 'success') {
        editing = false;
        await update(); // reloads the profile with the saved values
      } else {
        await update({ reset: false }); // keep what they typed, show the message
      }
    };
  };

  // `form` is shared by both actions; the switch action tags its failures.
  let editError = $derived(form?.scope === 'switch' ? '' : (form?.message ?? ''));
  let switchError = $derived(form?.scope === 'switch' ? (form?.message ?? '') : '');
</script>

<PageHeader title={name} record>
  {#snippet sub()}
    {$_(roleKey(p.role))} · {data.org.name} · {$_('profile.main.joined', {
      values: { date: shortDate(p.joined_at) }
    })}
  {/snippet}
  {#snippet actions()}
    {#if !editing}
      <button class="v2-btn v2-btn-primary" onclick={openEdit}
        >{$_('profile.main.edit_details')}</button
      >
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:18px;padding-bottom:32px">
    <div class="v2-split">
      <div>
        <div class="v2-label" style="margin-bottom:10px">{$_('profile.main.section_you')}</div>

        {#if editing}
          <form
            class="v2-card"
            method="POST"
            action="?/edit"
            use:enhance={onEdit}
            style="padding:17px 18px;margin-bottom:20px"
          >
            <div class="v2-field">
              <label for="f-name">{$_('profile.main.field_name')}</label>
              <input
                id="f-name"
                name="name"
                class="v2-input"
                bind:value={editName}
                maxlength="255"
              />
            </div>
            <div class="v2-field" style="margin-top:12px">
              <label for="f-phone">{$_('profile.main.field_phone')}</label>
              <input
                id="f-phone"
                name="phone"
                class="v2-input"
                bind:value={editPhone}
                placeholder="+44 20 7946 0100"
              />
              <p class="v2-hint">{$_('profile.main.hint_phone')}</p>
            </div>
            {#if editError}
              <p class="v2-error" style="margin-top:10px">{editError}</p>
            {/if}
            <div style="display:flex;gap:8px;margin-top:16px">
              <button class="v2-btn v2-btn-primary" type="submit">{$_('profile.main.save')}</button>
              <button class="v2-btn" type="button" onclick={() => (editing = false)}
                >{$_('profile.main.cancel')}</button
              >
            </div>
          </form>
        {:else}
          <div class="v2-card" style="padding:17px 18px;margin-bottom:20px">
            <div style="display:flex;gap:13px;align-items:center;margin-bottom:16px">
              <Avatar {name} size={46} />
              <div style="min-width:0">
                <div style="font-weight:640;font-size:15px">{name}</div>
                <div class="v2-sub" style="font-size:12.5px">{p.user_details.email}</div>
              </div>
            </div>
            <dl class="v2-kv">
              <dt>{$_('profile.main.field_phone')}</dt>
              <dd class="v2-num" style="font-size:12px">{p.phone || '—'}</dd>
              <dt>{$_('profile.main.kv_teams')}</dt>
              <dd>{p.teams.join(', ') || '—'}</dd>
              <dt>{$_('profile.main.kv_joined')}</dt>
              <dd>{shortDate(p.joined_at)}</dd>
              <dt>{$_('profile.main.kv_last_login')}</dt>
              <dd>{relativeDays(p.last_login)}</dd>
            </dl>
          </div>
        {/if}

        <div class="v2-label" style="margin-bottom:10px">{$_('profile.main.section_orgs')}</div>
        <div class="v2-card" style="overflow:hidden">
          {#each p.orgs as o (o.id)}
            <div class="v2-setting">
              <div class="v2-setting-body">
                <b>{o.name}</b>
                <span class="v2-sub" style="font-size:11.5px">
                  {$_('profile.main.org_you_are', {
                    values: {
                      role:
                        o.role === 'ADMIN'
                          ? $_('profile.main.org_role_admin')
                          : $_('profile.main.org_role_member')
                    }
                  })}
                </span>
              </div>
              {#if o.is_current}
                <Pill tone="ink" dot>{$_('profile.main.org_current')}</Pill>
              {:else}
                <!-- Switching org re-issues the token; it does not edit a field
                     on this page. The action swaps the cookies and reloads. -->
                <form method="POST" action="?/switchOrg" use:enhance class="v2-inline-form">
                  <input type="hidden" name="org_id" value={o.id} />
                  <button class="v2-btn v2-btn-sm" type="submit">
                    <ArrowLeftRight size={12} />{$_('profile.main.org_switch')}
                  </button>
                </form>
              {/if}
            </div>
          {/each}
        </div>
        {#if switchError}
          <p class="v2-error" style="margin-top:9px">{switchError}</p>
        {/if}
        <p class="v2-sub" style="font-size:11.5px;margin-top:11px">
          {$_('profile.main.orgs_note')}
        </p>
      </div>

      <div>
        <div class="v2-label" style="margin-bottom:10px">{$_('profile.main.section_access')}</div>
        <div class="v2-card" style="overflow:hidden;margin-bottom:20px">
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('profile.main.access_role')}</b>
              <!-- Displayed, never editable from here. -->
              <span class="v2-sub" style="font-size:11.5px">
                {$_('profile.main.access_role_note')}
              </span>
            </div>
            <Lock size={14} style="color:var(--v2-slate);flex:none" />
            <Pill tone={ROLE_TONE[p.role]}>{$_(roleKey(p.role))}</Pill>
          </div>
          <!-- /profile/tokens, not /settings/api-tokens. The settings page is
               the org-wide oversight list and 403s a member, so this count used
               to lead most of the people who clicked it to "Admins only". -->
          <a class="v2-setting" href={resolve('/profile/tokens')}>
            <div class="v2-setting-body">
              <b>{$_('profile.main.access_tokens')}</b>
              <span class="v2-sub" style="font-size:11.5px">
                {$_('profile.main.access_tokens_note')}
              </span>
            </div>
            <KeyRound size={14} style="color:var(--v2-slate);flex:none" />
            <span class="v2-num" style="font-size:13px;font-weight:600">
              {count(p.active_token_count)}
            </span>
          </a>
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('profile.main.access_signin')}</b>
              <!-- It used to say "Google, on <email>", which is false for
                   anyone who signed in with an emailed code. Nothing in the
                   payload says which was used, so this states what holds for
                   both rather than guessing. -->
              <span class="v2-sub" style="font-size:11.5px">
                {$_('profile.main.access_signin_note', { values: { email: p.user_details.email } })}
              </span>
            </div>
          </div>
        </div>

        <!-- i18n pilot: this was in the Sidebar (reaches every screen, not
             just this one) as an infra placeholder; a per-user preference
             belongs on the page that owns "your own account" settings, not
             in the global nav. Cookie-based today (see LanguageSwitcher.svelte),
             not yet a real column on Profile — see PLAN.md's roadmap for
             persisting it server-side. -->
        <div class="v2-label" style="margin-bottom:10px">
          {$_('profile.main.section_preferences')}
        </div>
        <div class="v2-card" style="overflow:hidden;margin-bottom:20px">
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('profile.main.pref_language')}</b>
              <span class="v2-sub" style="font-size:11.5px">
                {$_('profile.main.pref_language_note')}
              </span>
            </div>
            <LanguageSwitcher />
          </div>
        </div>

        <div class="v2-label" style="margin-bottom:10px">{$_('profile.main.section_work')}</div>
        <div class="v2-card" style="overflow:hidden">
          <a class="v2-setting" href={resolve('/goals')}>
            <div class="v2-setting-body">
              <b>{$_('profile.main.work_goals')}</b>
              <span class="v2-sub" style="font-size:11.5px"
                >{$_('profile.main.work_goals_note')}</span
              >
            </div>
          </a>
          <a class="v2-setting" href={resolve('/timesheet')}>
            <div class="v2-setting-body">
              <b>{$_('profile.main.work_timesheet')}</b>
              <span class="v2-sub" style="font-size:11.5px"
                >{$_('profile.main.work_timesheet_note')}</span
              >
            </div>
          </a>
          <a class="v2-setting" href={resolve('/tasks')}>
            <div class="v2-setting-body">
              <b>{$_('profile.main.work_tasks')}</b>
              <span class="v2-sub" style="font-size:11.5px"
                >{$_('profile.main.work_tasks_note')}</span
              >
            </div>
          </a>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  /* The Switch button sits in a form so it can POST; keep it laid out exactly
     as the bare button was (the row uses flex; the form must not add a box). */
  .v2-inline-form {
    display: contents;
  }
</style>
