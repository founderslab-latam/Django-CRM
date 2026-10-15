<script>
  /**
   * Live Chat / WhatsApp conversations mirrored from Chatwoot, on a Contact
   * or Lead's own detail page (email stays on the native pipeline and shows
   * up through the existing case/ticket views instead).
   *
   * Hidden entirely when there are none, unlike the deals/tasks/tickets
   * rails above it on these pages: those are core record types every
   * contact plausibly has zero of and still worth a stated empty state,
   * this is a channel most orgs have not wired up yet, and an always-visible
   * "no conversations" card for a feature nobody turned on yet is clutter.
   *
   * A row expands to the transcript the webhook mirrored, so reading a chat
   * never needs Chatwoot. Replying does: "Open in Chatwoot" opens its agent
   * view in a pop-up window, not an iframe -- Chatwoot sends
   * `X-Frame-Options: SAMEORIGIN`, and in production the two apps live on
   * different sites, so even a frameable Chatwoot would lose its session
   * cookie inside the frame. The link's own href + target is the new-tab
   * fallback when the pop-up is blocked.
   */
  import { MessageCircle, ChevronDown, ChevronUp, ExternalLink } from '@lucide/svelte';
  import Pill from './Pill.svelte';
  import { shortDate, relativeTime } from '$lib/v2/format.js';
  import { _ } from '$lib/i18n/index.js';

  /**
   * @typedef {{
   *   id: string, message_type: string, content: string,
   *   sender_name: string, occurred_at: string
   * }} ChatwootMessageRow
   * @typedef {{
   *   id: string, channel: string, channel_display: string,
   *   status: string, status_display: string, chatwoot_conversation_id: number,
   *   embed_url: string, created_at: string, resolved_at: string|null,
   *   messages: ChatwootMessageRow[]
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

  /**
   * @param {MouseEvent} event
   * @param {string} url
   */
  function openPopup(event, url) {
    // Modified clicks keep their native meaning (new tab, new window, ...).
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    const popup = window.open(url, '_blank', 'popup,width=1100,height=800');
    if (popup) {
      popup.opener = null;
      event.preventDefault();
    }
  }

  /** @param {string} type */
  function side(type) {
    if (type === 'incoming') return 'them';
    if (type === 'outgoing') return 'us';
    return 'system';
  }
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
          <div class="cw-body">
            {#if c.messages?.length}
              <ol class="cw-transcript">
                {#each c.messages as m (m.id)}
                  <li class="cw-msg cw-{side(m.message_type)}">
                    {#if side(m.message_type) !== 'system'}
                      <span class="cw-meta">
                        {m.sender_name} · {relativeTime(m.occurred_at)}
                      </span>
                    {/if}
                    <span class="cw-bubble">{m.content}</span>
                  </li>
                {/each}
              </ol>
            {:else}
              <p class="v2-sub" style="font-size:12px;margin:0 0 10px">
                {$_('conversations.panel.no_messages')}
              </p>
            {/if}
            <!-- eslint-disable svelte/no-navigation-without-resolve -- external origin (Chatwoot), not an app route -->
            <a
              href={c.embed_url}
              target="_blank"
              rel="noopener noreferrer"
              class="cw-open"
              onclick={(e) => openPopup(e, c.embed_url)}
            >
              <ExternalLink size={13} />
              {$_('conversations.panel.open_in_new_tab')}
            </a>
            <!-- eslint-enable svelte/no-navigation-without-resolve -->
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
  .cw-body {
    padding: 0 15px 14px;
  }
  .cw-transcript {
    list-style: none;
    margin: 0 0 10px;
    padding: 10px;
    max-height: 360px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    border: 1px solid var(--v2-line-soft);
    border-radius: 8px;
  }
  .cw-msg {
    display: flex;
    flex-direction: column;
    max-width: 80%;
    gap: 2px;
  }
  .cw-them {
    align-self: flex-start;
  }
  .cw-us {
    align-self: flex-end;
    align-items: flex-end;
  }
  .cw-system {
    align-self: center;
    max-width: 100%;
  }
  .cw-meta {
    font-size: 11px;
    color: var(--v2-slate);
  }
  .cw-bubble {
    font-size: 13px;
    line-height: 1.4;
    padding: 7px 10px;
    border-radius: 10px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    background: var(--v2-line-soft);
  }
  .cw-us .cw-bubble {
    background: var(--v2-paper);
    border: 1px solid var(--v2-line-soft);
  }
  .cw-system .cw-bubble {
    background: none;
    padding: 0;
    font-size: 11.5px;
    color: var(--v2-slate);
    text-align: center;
  }
  .cw-open {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--v2-slate);
    text-decoration: none;
  }
  .cw-open:hover {
    color: var(--v2-ink);
  }
</style>
