<script>
  /**
   * Language switcher — i18n pilot infrastructure (Developer A in
   * ~/harness-engineering/bottle-crm-i18n/PLAN.md). Cookie-based locale, no
   * URL prefix: picking a language writes the `locale` cookie and reloads
   * the page, so the very next SSR render (hooks.server.js) already
   * resolves that locale before anything renders. There is no client-side
   * re-render of the current page's content — the reload IS the mechanism.
   *
   * Uses the placeholder `common.language_switcher.*` keys from
   * frontend/messages/{en,es}.json to prove the catalog pipeline works
   * end-to-end; it does not touch any real Sidebar/Login/Dashboard copy.
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

  /** @param {string} next */
  function setLocale(next) {
    if (next === $currentLocale) return;
    document.cookie = `${LOCALE_COOKIE_NAME}=${next}; path=/; max-age=31536000; samesite=lax`;
    window.location.reload();
  }
</script>

<div class="v2-lang-switcher" role="group" aria-label={$_('common.language_switcher.label')}>
  {#each SUPPORTED_LOCALES as code (code)}
    <button
      type="button"
      class="v2-btn v2-btn-sm"
      class:v2-btn-quiet={$currentLocale !== code}
      aria-pressed={$currentLocale === code}
      onclick={() => setLocale(code)}
    >
      {$_(LOCALE_LABEL_KEYS[code])}
    </button>
  {/each}
</div>

<style>
  .v2-lang-switcher {
    display: flex;
    gap: 6px;
    padding: 4px 0 2px;
  }
  .v2-lang-switcher .v2-btn {
    flex: 1;
    justify-content: center;
  }
</style>
