<script>
  /**
   * Root layout, above both the `(app)` and `(no-layout)` route groups.
   * Renders nothing of its own - each group keeps its own shell/markup.
   *
   * i18n pilot: keeps the client-side svelte-i18n store in sync with the
   * locale `hooks.server.js` already resolved and rendered this request
   * with (see `+layout.server.js` and `$lib/i18n`). On the server this call
   * just re-affirms what hooks.server.js set; on the client (first load and
   * every navigation) it's what actually loads the catalog into the
   * browser's own store.
   */
  import { setupI18n } from '$lib/i18n/index.js';

  /** @type {{ data: { locale: string }, children: import('svelte').Snippet }} */
  let { data, children } = $props();

  // Intentionally not reactive: this pilot only ever changes locale via a
  // full page reload (see LanguageSwitcher.svelte), never a soft
  // client-side navigation, so re-running this per `data` update isn't
  // needed - the first value on mount is the only one that matters.
  setupI18n(data.locale);
</script>

{@render children()}
