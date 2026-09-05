<script>
  import { resolve } from '$app/paths';
  /**
   * Whether a customer's reply can bring a closed ticket back.
   *
   * One row per org, four fields. Small enough that v1's form is not wrong,
   * just uninformative. The whole question here is what number to put in the
   * window, and the only thing that answers it is how customers actually
   * behave: the median reply comes back in two days, and four replies last
   * month arrived after the window and reopened nothing.
   *
   * Those four are the cost of the current setting. A settings form that shows
   * the field but not the consequence makes the number a guess forever.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import StatCard from '$lib/v2/components/StatCard.svelte';
  import SettingsFormPanel from '$lib/v2/components/SettingsFormPanel.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { count } from '$lib/v2/format.js';
  import { REOPEN_TO_STATUSES } from '$lib/v2/enums.js';
  import { caseStatusKey } from '$lib/cases/labels.js';
  import { RotateCcw, MailX } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let editing = $state(false);

  let p = $derived(data.policy);
</script>

<PageHeader title={$_('settings.reopen.title')}>
  {#snippet crumb()}<SettingsCrumb />{/snippet}
  {#snippet sub()}
    {p.is_enabled
      ? $_('settings.reopen.sub_on', { values: { days: p.reopen_window_days } })
      : $_('settings.reopen.sub_off')}
  {/snippet}
  {#snippet actions()}
    {#if data.can_edit && !editing}
      <button class="v2-btn v2-btn-primary" onclick={() => (editing = true)}>
        {$_('settings.reopen.edit_button')}
      </button>
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-pad" style="padding-top:16px;flex:none">
  <div class="v2-stats">
    <StatCard
      label={$_('settings.reopen.stat_reopened')}
      value={count(p.reopened_last_30d)}
      tone="ink"
      detail={$_('settings.reopen.stat_reopened_detail')}
    />
    <!-- "n/a" rather than 0 while the policy is off. `_evaluate_reopen` returns
         `None` on `if not policy["is_enabled"]` BEFORE it compares the window,
         and the `out_of_reopen_window` flag this metric counts is written only
         for the "out_of_window" return. So with reopening off nothing is ever
         flagged and the count is always zero, in exactly the state where every
         reply to a closed ticket reopens nothing. A plain 0 there is
         reassurance about the one thing certainly happening. -->
    <StatCard
      label={$_('settings.reopen.stat_missed')}
      value={p.is_enabled ? count(p.replies_after_window_30d) : $_('settings.reopen.na')}
      tone={p.is_enabled && p.replies_after_window_30d > 0 ? 'clay' : 'slate'}
      detail={p.is_enabled
        ? $_('settings.reopen.stat_missed_detail_on')
        : $_('settings.reopen.stat_missed_detail_off')}
    />
    <StatCard
      label={$_('settings.reopen.stat_median')}
      value={$_('settings.reopen.days_short', { values: { days: p.median_days_to_reply } })}
      tone="slate"
      detail={$_('settings.reopen.stat_median_detail')}
    />
  </div>
</div>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-bottom:32px">
    {#if editing}
      <SettingsFormPanel
        title={$_('settings.reopen.title')}
        action="?/update"
        error={form?.update?.error}
        submitLabel={$_('settings.reopen.save_button')}
        oncancel={() => (editing = false)}
        ondone={() => (editing = false)}
      >
        {#snippet fields()}
          <div class="v2-field v2-sfp-wide">
            <label for="f-enabled">{$_('settings.reopen.field_enabled')}</label>
            <label style="display:flex;gap:8px;align-items:center;font-weight:400">
              <input
                id="f-enabled"
                type="checkbox"
                name="is_enabled"
                value="true"
                checked={p.is_enabled}
              />
              {$_('settings.reopen.enabled_help')}
            </label>
          </div>

          <div class="v2-field">
            <label for="f-window">{$_('settings.reopen.field_window')}</label>
            <input
              id="f-window"
              class="v2-input"
              type="number"
              name="reopen_window_days"
              min="1"
              max="365"
              required
              value={p.reopen_window_days}
            />
            <p class="v2-hint">{$_('settings.reopen.window_hint')}</p>
          </div>

          <div class="v2-field">
            <label for="f-status">{$_('settings.reopen.field_status')}</label>
            <select id="f-status" class="v2-input" name="reopen_to_status">
              {#each REOPEN_TO_STATUSES as status (status)}
                <option value={status} selected={status === p.reopen_to_status}>
                  {$_(caseStatusKey(status))}
                </option>
              {/each}
            </select>
            <p class="v2-hint">{$_('settings.reopen.status_hint_form')}</p>
          </div>

          <div class="v2-field v2-sfp-wide">
            <label for="f-notify">{$_('settings.reopen.field_notify')}</label>
            <label style="display:flex;gap:8px;align-items:center;font-weight:400">
              <input
                id="f-notify"
                type="checkbox"
                name="notify_assigned"
                value="true"
                checked={p.notify_assigned}
              />
              {$_('settings.reopen.notify_help')}
            </label>
          </div>
        {/snippet}
      </SettingsFormPanel>
    {/if}
    <div class="v2-split">
      <div>
        <div class="v2-label" style="margin-bottom:10px">{$_('settings.reopen.section_rule')}</div>
        <div class="v2-card" style="overflow:hidden">
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('settings.reopen.field_enabled')}</b>
              <span class="v2-sub" style="font-size:11.5px">
                {$_('settings.reopen.enabled_help')}
              </span>
            </div>
            <Pill tone={p.is_enabled ? 'moss' : 'slate'}>
              {p.is_enabled ? $_('settings.reopen.on') : $_('settings.reopen.off')}
            </Pill>
          </div>
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('settings.reopen.card_window')}</b>
              <span class="v2-sub" style="font-size:11.5px">
                {$_('settings.reopen.window_hint')}
              </span>
            </div>
            <span class="v2-num" style="font-size:13px">
              {$_('settings.reopen.window_days_value', { values: { days: p.reopen_window_days } })}
            </span>
          </div>
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('settings.reopen.field_status')}</b>
              <!-- Must be a non-terminal status: reopening a ticket into a
                   closed status would close it again on arrival. -->
              <span class="v2-sub" style="font-size:11.5px">
                {$_('settings.reopen.status_hint_card')}
              </span>
            </div>
            <Pill tone="ink">{$_(caseStatusKey(p.reopen_to_status))}</Pill>
          </div>
          <div class="v2-setting">
            <div class="v2-setting-body">
              <b>{$_('settings.reopen.field_notify')}</b>
              <span class="v2-sub" style="font-size:11.5px">
                {$_('settings.reopen.notify_help')}
              </span>
            </div>
            <Pill tone={p.notify_assigned ? 'moss' : 'slate'}>
              {p.notify_assigned ? $_('settings.reopen.yes') : $_('settings.reopen.no')}
            </Pill>
          </div>
        </div>
      </div>

      <div>
        <div class="v2-label" style="margin-bottom:10px">
          {$_('settings.reopen.section_effect')}
        </div>
        <div class="v2-card" style="padding:15px 16px">
          <div style="display:flex;gap:10px;align-items:flex-start">
            <RotateCcw size={16} style="color:var(--v2-slate);flex:none;margin-top:2px" />
            <p class="v2-sub" style="font-size:12.5px;margin:0;line-height:1.5">
              {#if p.is_enabled}
                {$_('settings.reopen.effect_on_before')}<b
                  style="font-weight:600;color:var(--v2-ink)"
                  >{$_(caseStatusKey(p.reopen_to_status))}</b
                >{$_('settings.reopen.effect_on_after')}
              {:else}
                <!-- Present tense, and the policy is off, so this cannot be
                     written as though a reply still reopened anything. -->
                {$_('settings.reopen.effect_off_before')}<b
                  style="font-weight:600;color:var(--v2-ink)"
                  >{$_(caseStatusKey(p.reopen_to_status))}</b
                >{$_('settings.reopen.effect_off_after')}
              {/if}
            </p>
          </div>
        </div>

        {#if !p.is_enabled}
          <div class="v2-card" style="padding:15px 16px;margin-top:12px">
            <div style="display:flex;gap:10px;align-items:flex-start">
              <MailX size={16} style="color:var(--v2-clay);flex:none;margin-top:2px" />
              <div>
                <div style="font-weight:600;font-size:13px">
                  {$_('settings.reopen.misses_heading')}
                </div>
                <p class="v2-sub" style="font-size:12.5px;margin:5px 0 0;line-height:1.5">
                  {$_('settings.reopen.misses_body')}
                </p>
              </div>
            </div>
          </div>
        {:else if p.replies_after_window_30d > 0}
          <div class="v2-card" style="padding:15px 16px;margin-top:12px">
            <div style="display:flex;gap:10px;align-items:flex-start">
              <MailX size={16} style="color:var(--v2-clay);flex:none;margin-top:2px" />
              <div>
                <div style="font-weight:600;font-size:13px">
                  <span class="v2-num">{count(p.replies_after_window_30d)}</span>
                  {$_('settings.reopen.late_heading', {
                    values: { count: p.replies_after_window_30d }
                  })}
                </div>
                <p class="v2-sub" style="font-size:12.5px;margin:5px 0 0;line-height:1.5">
                  {$_('settings.reopen.late_body_before')}
                  <span class="v2-num">{p.reopen_window_days}</span>
                  {$_('settings.reopen.late_body_after')}
                </p>
              </div>
            </div>
          </div>
        {/if}

        <p class="v2-sub" style="font-size:11.5px;margin-top:14px">
          {$_('settings.reopen.footer_before')}
          <a href={resolve('/settings/inbound-email')} style="color:inherit"
            >{$_('settings.reopen.footer_link')}</a
          >{$_('settings.reopen.footer_after')}
        </p>
      </div>
    </div>
  </div>
</div>
