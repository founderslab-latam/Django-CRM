<script>
  /**
   * Live Chat / WhatsApp conversations mirrored from Chatwoot, on a Contact
   * or Lead's own detail page -- the embedded half of the Chatwoot
   * integration (email stays on the native pipeline and shows up through
   * the existing case/ticket views instead).
   *
   * Hidden entirely when there are none, unlike the deals/tasks/tickets
   * rails above it on these pages: those are core record types every
   * contact plausibly has zero of and still worth a stated empty state,
   * this is a channel most orgs have not wired up yet, and an always-visible
   * "no conversations" card for a feature nobody turned on yet is clutter.
   *
   * Opening a row embeds Chatwoot's own agent dashboard in an iframe rather
   * than navigating away -- that's the point of embedding it in the CRM.
   * There is no SSO between the two yet: the agent needs to already be
   * signed in to Chatwoot in this browser, or the iframe shows its login
   * screen. The "open in a new tab" link is the fallback for that case.
   */
  import { MessageCircle, ChevronDown, ChevronUp, ExternalLink } from '@lucide/svelte';
  import Pill from './Pill.svelte';
  import { shortDate } from '$lib/v2/format.js';
  import { _ } from '$lib/i18n/index.js';

  /**
   * @typedef {{
   *   id: string, channel: string, channel_display: string,
   *   status: string, status_display: string, chatwoot_conversation_id: number,
   *   embed_url: string, created_at: string, resolved_at: string|null
   * }} ChatwootConversationRow
   */

  /** @type {{ conversations?: ChatwootConversationRow[] }} */
  let { conversations = [] } = $props();

  const STATUS_TONE = /** @type {Record<string, 'moss'|'clay'|'slate'>} */ ({
    open: 'moss',
    pending: 'clay',
    resolved: 'slate'
  });

  /** @type {string | null} */
  let openId = $state(null);
</script>

{#if conversations.length}
  <div class="v2-label" style="margin-bottom:10px">
    {$_('conversations.panel.heading')}
  </div>
  <div class="v2-card" style="overflow:hidden;margin-bottom:22px">
    {#each conversations as c (c.id)}
      <div class="cw-row">
        <button
          type="button"
          class="cw-row-head"
          aria-expanded={openId === c.id}
          onclick={() => (openId = openId === c.id ? null : c.id)}
        >
          <MessageCircle size={15} style="flex:none;color:var(--v2-slate)" />
          <span style="flex:1;font-size:13px;min-width:0">{c.channel_display}</span>
          <Pill tone={STATUS_TONE[c.status] ?? 'slate'}>{c.status_display}</Pill>
          <span class="v2-sub" style="font-size:11.5px;white-space:nowrap">
            {shortDate(c.created_at)}
          </span>
          {#if openId === c.id}
            <ChevronUp size={14} style="flex:none" />
          {:else}
            <ChevronDown size={14} style="flex:none" />
          {/if}
        </button>
        {#if openId === c.id}
          <div class="cw-embed">
            <iframe src={c.embed_url} title={c.channel_display} loading="lazy"></iframe>
            <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- external origin (Chatwoot), not an app route -->
            <a href={c.embed_url} target="_blank" rel="noopener noreferrer" class="cw-open-tab">
              <ExternalLink size={13} />
              {$_('conversations.panel.open_in_new_tab')}
            </a>
          </div>
        {/if}
      </div>
    {/each}
  </div>
{/if}

<style>
  .cw-row {
    border-bottom: 1px solid var(--v2-line-soft);
  }
  .cw-row:last-child {
    border-bottom: none;
  }
  .cw-row-head {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 11px 15px;
    background: none;
    border: 0;
    cursor: pointer;
    font: inherit;
    color: inherit;
    text-align: left;
  }
  .cw-row-head:hover {
    background: var(--v2-line-soft);
  }
  .cw-embed {
    padding: 0 15px 15px;
  }
  .cw-embed iframe {
    width: 100%;
    height: 520px;
    border: 1px solid var(--v2-line-soft);
    border-radius: 8px;
    background: var(--v2-paper);
  }
  .cw-open-tab {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 8px;
    font-size: 12px;
    color: var(--v2-slate);
    text-decoration: none;
  }
  .cw-open-tab:hover {
    color: var(--v2-ink);
  }
</style>
