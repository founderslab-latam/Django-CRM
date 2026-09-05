<script>
  import { resolve } from '$app/paths';
  /**
   * The calendar every response target is measured against.
   *
   * This page is small but it is the reason "answered in 4h" means anything.
   * A ticket opened at 17:20 on Friday and answered at 09:10 on Monday is
   * either fifteen hours late or fifty minutes early, and only this calendar
   * decides which. v1 hid it three levels into a settings dropdown, so the
   * analytics page reported numbers nobody could interpret.
   *
   * Closed days and holidays are shown, not omitted. A blank row for Saturday
   * reads as missing data; "Closed" reads as a decision.
   *
   * "Edit hours" and "Add" open the two panels below. `data.can_edit` only
   * decides whether those controls are offered: it is a display hint decoded
   * from the JWT, never the authorization decision. The backend re-derives
   * admin status from `request.profile` on every write and is what actually
   * refuses a non-admin.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import SettingsCrumb from '$lib/v2/components/SettingsCrumb.svelte';
  import SettingsFormPanel from '$lib/v2/components/SettingsFormPanel.svelte';
  import ConfirmAction from '$lib/v2/components/ConfirmAction.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { shortDate, relativeDays } from '$lib/v2/format.js';
  import { weeklyHours, isAlwaysOn } from './week.js';
  import { Plus, Clock, TriangleAlert } from '@lucide/svelte';

  /** Weekday name → catalog key. The stored value ("Monday") stays the key
   *  everywhere else on this page (form field prefixes, the today comparison);
   *  only what a person reads is translated. */
  const DAY_KEYS = {
    Monday: 'monday',
    Tuesday: 'tuesday',
    Wednesday: 'wednesday',
    Thursday: 'thursday',
    Friday: 'friday',
    Saturday: 'saturday',
    Sunday: 'sunday'
  };
  /** @param {string} day */
  const dayNameKey = (day) => `settings.business_hours.day.${DAY_KEYS[day] ?? day}`;

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let calendar = $derived(data.calendar);

  let weekly = $derived(weeklyHours(calendar.days));

  /** See `week.js`: this is the state where the engine drops the calendar and
   *  runs the clock, so the page has to contradict its own rows. */
  let alwaysOn = $derived(isAlwaysOn(calendar.days));
  const todayName = new Intl.DateTimeFormat('en-GB', { weekday: 'long' }).format(new Date());

  // `null` when the panel is closed. One panel for the week, so only one
  // edit can be in flight at a time.
  let editingHours = $state(false);

  // The week being edited, seeded from `calendar.days` when the panel opens.
  // A day's key is its own name lower-cased ("Monday" → "monday"), the same
  // prefix the model's fourteen flat fields use, so no separate label map is
  // needed here. `closed` drives both the checkbox and whether the two time
  // inputs are disabled; a closed day still carries a sensible default time
  // so re-opening it doesn't hand back a blank field.
  let hourRows = $state(
    /** @type {{ day: string, key: string, open: string, close: string, closed: boolean }[]} */ ([])
  );

  function openHoursEdit() {
    hourRows = calendar.days.map((d) => ({
      day: d.day,
      key: d.day.toLowerCase(),
      open: d.open ?? '09:00',
      close: d.close ?? '17:00',
      closed: !d.open
    }));
    editingHours = true;
  }

  // `null` when the panel is closed.
  let addingHoliday = $state(false);
</script>

<PageHeader title={$_('settings.business_hours.title')}>
  {#snippet crumb()}<SettingsCrumb />{/snippet}
  {#snippet sub()}
    {calendar.name} · {calendar.timezone} ·
    {#if alwaysOn}
      {$_('settings.business_hours.sub_always_on')}
    {:else}
      <span class="v2-num">{weekly}</span>
      {$_('settings.business_hours.sub_hours_suffix')}
    {/if}
  {/snippet}
  {#snippet actions()}
    {#if data.can_edit && !editingHours}
      <button class="v2-btn v2-btn-primary" onclick={openHoursEdit}>
        {$_('settings.business_hours.edit_hours_button')}
      </button>
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:18px;padding-bottom:32px">
    <div class="v2-split">
      <div>
        <div class="v2-label" style="margin-bottom:10px">
          {$_('settings.business_hours.section_hours')}
        </div>

        {#if editingHours}
          <SettingsFormPanel
            title={$_('settings.business_hours.form_title')}
            action="?/updateHours"
            error={form?.updateHours?.error}
            submitLabel={$_('settings.business_hours.save_hours_button')}
            oncancel={() => (editingHours = false)}
            ondone={() => (editingHours = false)}
          >
            {#snippet fields()}
              <div class="v2-field">
                <label for="bh-name">{$_('settings.business_hours.field_name')}</label>
                <input
                  id="bh-name"
                  class="v2-input"
                  name="name"
                  maxlength="100"
                  required
                  value={calendar.name}
                />
              </div>

              <div class="v2-field">
                <label for="bh-timezone">{$_('settings.business_hours.field_timezone')}</label>
                <input
                  id="bh-timezone"
                  class="v2-input"
                  name="timezone"
                  maxlength="64"
                  required
                  value={calendar.timezone}
                  placeholder="America/New_York"
                />
                <p class="v2-hint">{$_('settings.business_hours.timezone_hint')}</p>
              </div>

              <div class="v2-field v2-sfp-wide">
                <label for="bh-day-0-open">{$_('settings.business_hours.field_week')}</label>
                {#each hourRows as row, i (row.key)}
                  <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px">
                    <span style="width:84px;font-size:13px;flex:none"
                      >{$_(dayNameKey(row.day))}</span
                    >
                    <label
                      style="display:flex;gap:6px;align-items:center;font-size:12px;font-weight:400;flex:none"
                    >
                      <input
                        type="checkbox"
                        name="{row.key}_closed"
                        value="true"
                        bind:checked={row.closed}
                      />
                      {$_('settings.business_hours.closed')}
                    </label>
                    <input
                      id={i === 0 ? 'bh-day-0-open' : undefined}
                      class="v2-input"
                      type="time"
                      name="{row.key}_open"
                      bind:value={row.open}
                      disabled={row.closed}
                      style="width:auto"
                    />
                    <span class="v2-sub">{$_('settings.business_hours.to')}</span>
                    <input
                      class="v2-input"
                      type="time"
                      name="{row.key}_close"
                      bind:value={row.close}
                      disabled={row.closed}
                      style="width:auto"
                    />
                  </div>
                {/each}
              </div>
            {/snippet}
          </SettingsFormPanel>
        {/if}

        {#if alwaysOn}
          <div class="v2-bh-banner">
            <TriangleAlert size={17} style="color:var(--v2-clay);flex:none;margin-top:1px" />
            <div>
              <div style="font-weight:600;font-size:13px">
                {$_('settings.business_hours.always_on_heading')}
              </div>
              <p class="v2-sub" style="font-size:12px;margin:4px 0 0">
                {$_('settings.business_hours.always_on_body')}
              </p>
            </div>
          </div>
        {/if}

        <div class="v2-card" style="overflow:hidden">
          {#each calendar.days as d (d.day)}
            <div class="v2-setting" style={d.day === todayName ? 'background:var(--v2-hover)' : ''}>
              <div class="v2-setting-body">
                <b>{$_(dayNameKey(d.day))}</b>
                {#if d.day === todayName}
                  <span class="v2-sub" style="font-size:11px"
                    >{$_('settings.business_hours.today')}</span
                  >
                {/if}
              </div>
              {#if d.open && d.close}
                <span class="v2-num" style="font-size:13px">{d.open} - {d.close}</span>
              {:else}
                <!-- Named, not blank. A blank cell reads as missing data. -->
                <span class="v2-sub" style="font-size:12.5px"
                  >{$_('settings.business_hours.closed')}</span
                >
              {/if}
            </div>
          {/each}
        </div>

        {#if calendar.is_default}
          <p class="v2-sub" style="font-size:11.5px;margin-top:11px">
            {$_('settings.business_hours.default_note')}
          </p>
        {/if}
      </div>

      <div>
        <div style="display:flex;align-items:baseline;margin-bottom:10px">
          <div class="v2-label">{$_('settings.business_hours.section_holidays')}</div>
          {#if data.can_edit && !addingHoliday}
            <button
              class="v2-btn v2-btn-sm"
              style="margin-left:auto"
              onclick={() => (addingHoliday = true)}
            >
              <Plus size={12} />{$_('settings.business_hours.add_button')}
            </button>
          {/if}
        </div>

        {#if addingHoliday}
          <SettingsFormPanel
            title={$_('settings.business_hours.holiday_form_title')}
            action="?/addHoliday"
            error={form?.addHoliday?.error}
            submitLabel={$_('settings.business_hours.add_holiday_button')}
            oncancel={() => (addingHoliday = false)}
            ondone={() => (addingHoliday = false)}
          >
            {#snippet fields()}
              <div class="v2-field">
                <label for="bh-holiday-date">{$_('settings.business_hours.field_date')}</label>
                <input id="bh-holiday-date" class="v2-input" type="date" name="date" required />
              </div>
              <div class="v2-field">
                <label for="bh-holiday-name">{$_('settings.business_hours.field_name')}</label>
                <input
                  id="bh-holiday-name"
                  class="v2-input"
                  name="name"
                  maxlength="100"
                  required
                  placeholder={$_('settings.business_hours.holiday_name_placeholder')}
                />
              </div>
            {/snippet}
          </SettingsFormPanel>
        {/if}

        {#if form?.removeHoliday?.error}
          <p class="v2-error" style="margin-bottom:12px">{form.removeHoliday.error}</p>
        {/if}
        {#if form?.holidayAlreadyNamed}
          <!-- The POST is idempotent on date and answers 200 with the row that
               was already stored, so the name just typed was discarded. Silence
               here reads as a successful rename. -->
          <p class="v2-sub" style="margin-bottom:12px;font-size:12px">
            {$_('settings.business_hours.holiday_dup_before')}
            <b style="font-weight:600">{form.holidayAlreadyNamed}</b>{$_(
              'settings.business_hours.holiday_dup_after'
            )}
          </p>
        {/if}

        <div class="v2-card" style="overflow:hidden">
          {#each calendar.holidays as h (h.id)}
            <div class="v2-setting">
              <div class="v2-setting-body">
                <b>{h.name}</b>
                <span class="v2-sub" style="font-size:11.5px">{relativeDays(h.date)}</span>
              </div>
              <span class="v2-num" style="font-size:12.5px">{shortDate(h.date)}</span>
              {#if data.can_edit}
                <ConfirmAction
                  action="?/removeHoliday"
                  label={$_('settings.business_hours.remove_button')}
                  confirmLabel={$_('settings.business_hours.remove_button')}
                  explain={$_('settings.business_hours.remove_holiday_explain')}
                  hidden={{ holiday_id: h.id }}
                />
              {/if}
            </div>
          {:else}
            <p class="v2-sub" style="padding:14px 16px;font-size:12.5px;margin:0">
              {$_('settings.business_hours.holidays_empty')}
            </p>
          {/each}
        </div>

        <div
          style="display:flex;gap:10px;align-items:flex-start;margin-top:18px;padding:14px 16px;border:1px solid var(--v2-line);border-radius:var(--v2-radius)"
        >
          <Clock size={16} style="color:var(--v2-slate);flex:none;margin-top:1px" />
          <div>
            <div style="font-weight:600;font-size:13px">
              {$_('settings.business_hours.effect_heading')}
            </div>
            <p class="v2-sub" style="font-size:12px;margin:4px 0 0">
              {#if alwaysOn}
                <!-- The claim above this branch is false when nothing is open:
                     `_has_any_open_window` is what decides whether the calendar
                     is consulted at all, and with no open day it is not. -->
                {$_('settings.business_hours.effect_always_on')}
              {:else}
                {$_('settings.business_hours.effect_before')}
                {#if calendar.days[0].open}
                  {$_('settings.business_hours.effect_starts_at_before')}<span class="v2-num"
                    >{calendar.days[0].open}</span
                  >{$_('settings.business_hours.effect_starts_at_after')}
                {:else}
                  <!-- Monday can be marked closed from this page now, so the
                       fixed "Monday morning" framing can no longer assume an
                       open time exists to quote. -->
                  {$_('settings.business_hours.effect_starts_next')}
                {/if}
                {$_('settings.business_hours.effect_after')}
              {/if}
            </p>
            <p class="v2-sub" style="font-size:12px;margin:8px 0 0">
              <a href={resolve('/tickets/analytics')} style="color:inherit"
                >{$_('settings.business_hours.analytics_link')}</a
              >
              {$_('settings.business_hours.analytics_after')}
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<style>
  .v2-bh-banner {
    display: flex;
    gap: 11px;
    align-items: flex-start;
    padding: 14px 16px;
    margin-bottom: 12px;
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    background: var(--v2-card);
  }
</style>
