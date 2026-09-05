<script>
  /**
   * Language switcher — i18n pilot infrastructure (Developer A in
   * ~/harness-engineering/bottle-crm-i18n/PLAN.md). Cookie-based locale, no
   * URL prefix: picking a language writes the `locale` cookie and reloads
   * the page, so the very next SSR render (hooks.server.js) already
   * resolves that locale before anything renders. There is no client-side
   * re-render of the current page's content — the reload IS the mechanism.
   *
   * A `<select>` rather than a button row on purpose: `SUPPORTED_LOCALES`
   * is expected to grow past two, and a row of buttons stops scaling well
   * long before a dropdown does.
   *
   * Uses the placeholder `common.language_switcher.*` keys from
   * `src/lib/i18n/messages/{en,es}.json` to prove the catalog pipeline
   * works end-to-end; it does not touch any real Sidebar/Login/Dashboard
   * copy.
   */
  import {
    _,
    locale as currentLocale,
    SUPPORTED_LOCALES,
    LOCALE_COOKIE_NAME
  } from '$lib/i18n/index.js';

  const LOCALE_LABEL_KEYS = {
    en: 'common.language_switcher.english',
    es: 'common.language_switcher.spanish'
  };

  /** @param {Event & { currentTarget: HTMLSelectElement }} event */
  function handleChange(event) {
    const next = event.currentTarget.value;
    if (next === $currentLocale) return;
    document.cookie = `${LOCALE_COOKIE_NAME}=${next}; path=/; max-age=31536000; samesite=lax`;
    window.location.reload();
  }
</script>

<label class="v2-lang-switcher">
  <span class="v2-sr-only">{$_('common.language_switcher.label')}</span>
  <select class="v2-input v2-lang-select" value={$currentLocale} onchange={handleChange}>
    {#each SUPPORTED_LOCALES as code (code)}
      <option value={code}>{$_(LOCALE_LABEL_KEYS[code])}</option>
    {/each}
  </select>
</label>

<style>
  .v2-lang-switcher {
    display: inline-flex;
    padding: 4px 0 2px;
  }
  /* Overrides `.v2-input`'s `width: 100%` — this sits among compact sidebar
     links and a centered login-footer control, never a full-width form. */
  .v2-lang-select {
    width: auto;
    padding: 5px 9px;
    font-size: calc(var(--v2-fs) - 1.6px); /* 12.8px, matches .v2-btn-sm */
    cursor: pointer;
  }
</style>
