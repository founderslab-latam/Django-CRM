<script>
  /**
   * A conversation, not a record view. The customer wants to know what was said
   * and to say something back, so the thread is the page and the case fields are
   * a header above it.
   *
   * The header answers the three questions a customer opens this page with:
   * which case is this (the reference their emails carry), where does it stand
   * (status, priority, dates), and is anyone waiting on them.
   */
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PortalShell from '$lib/v2/components/PortalShell.svelte';
  import { casePriorityKey, caseStatusKey } from '$lib/cases/labels.js';
  import { _, locale } from '$lib/i18n/index.js';

  let { data, form } = $props();

  const OPEN_STATUSES = new Set(['New', 'Assigned', 'Pending']);

  function formatWhen(value) {
    if (!value) return '';
    return new Date(value).toLocaleString($locale ?? undefined, {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /** `closed_on` is a bare date; parsing it as UTC would show the day before
   *  anywhere west of Greenwich, so build it as a local date. */
  function formatDay(value) {
    if (!value) return '';
    const [y, m, d] = value.slice(0, 10).split('-').map(Number);
    return new Date(y, m - 1, d).toLocaleDateString($locale ?? undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  let isOpen = $derived(OPEN_STATUSES.has(data.case.status));
  let lastComment = $derived(data.comments.at(-1));

  /** The later of the case's own last save and its last public message. */
  let lastUpdate = $derived(
    [data.case.updated_at, lastComment?.commented_on].filter(Boolean).sort().at(-1)
  );

  /** Whose move it is, read off who spoke last. A case nobody has answered
   *  yet is waiting on the team, same as one where the customer spoke last. */
  let awaitingCustomer = $derived(isOpen && Boolean(lastComment?.is_support));

  /** A closed case outside the reopen window would swallow a reply nobody
   *  reads, so the form gives way to a pointer at a new request. */
  let canReply = $derived(isOpen || data.reopensOnReply);

  function authorLabel(entry) {
    if (entry.is_mine) return $_('portal.cases.you');
    if (entry.is_support) {
      return data.orgName
        ? $_('portal.cases.support_author', { values: { org: data.orgName } })
        : $_('portal.cases.support_author_generic');
    }
    return entry.author;
  }
</script>

<svelte:head>
  <title>{data.case.name}</title>
</svelte:head>

<PortalShell>
  <a class="back" href={resolve('/portal/cases')}>{$_('portal.cases.back_link')}</a>

  <header class="head">
    <div>
      <p class="ref">{$_('portal.cases.reference', { values: { ref: data.case.reference } })}</p>
      <h1>{data.case.name}</h1>
    </div>
    <span class="tag" class:open={isOpen}>{$_(caseStatusKey(data.case.status))}</span>
  </header>

  <dl class="facts">
    <div>
      <dt>{$_('portal.cases.fact_opened')}</dt>
      <dd>{formatWhen(data.case.created_at)}</dd>
    </div>
    {#if data.case.priority}
      <div>
        <dt>{$_('portal.cases.fact_priority')}</dt>
        <dd>{$_(casePriorityKey(data.case.priority))}</dd>
      </div>
    {/if}
    <div>
      <dt>{$_('portal.cases.fact_updated')}</dt>
      <dd>{formatWhen(lastUpdate)}</dd>
    </div>
    {#if data.case.closed_on}
      <div>
        <dt>{$_('portal.cases.fact_closed')}</dt>
        <dd>{formatDay(data.case.closed_on)}</dd>
      </div>
    {/if}
  </dl>

  {#if !isOpen}
    <p class="state closed">
      {data.reopensOnReply ? $_('portal.cases.closed_reopens') : $_('portal.cases.closed_final')}
      {#if !data.reopensOnReply}
        <a href={resolve('/portal/cases')}>{$_('portal.cases.new_request_link')}</a>
      {/if}
    </p>
  {:else if awaitingCustomer}
    <p class="state you">{$_('portal.cases.awaiting_customer')}</p>
  {:else}
    <p class="state team">
      {data.orgName
        ? $_('portal.cases.awaiting_support', { values: { org: data.orgName } })
        : $_('portal.cases.awaiting_support_generic')}
    </p>
  {/if}

  {#if data.case.description}
    <p class="desc">{data.case.description}</p>
  {/if}

  <section class="thread">
    {#if data.comments.length === 0}
      <p class="empty">{$_('portal.cases.thread_empty')}</p>
    {:else}
      {#each data.comments as entry (entry.id)}
        <article class="msg" class:mine={entry.is_mine} class:support={entry.is_support}>
          <div class="who">
            <strong>{authorLabel(entry)}</strong>
            <span class="when">{formatWhen(entry.commented_on)}</span>
          </div>
          <p>{entry.comment}</p>
        </article>
      {/each}
    {/if}
  </section>

  {#if canReply}
    <form method="POST" action="?/reply" use:enhance class="reply">
      <label for="comment">{$_('portal.cases.reply_label')}</label>
      <textarea
        id="comment"
        name="comment"
        rows="4"
        placeholder={$_('portal.cases.reply_placeholder')}
        required></textarea>
      {#if form?.error}<p class="err">{form.error}</p>{/if}
      <button type="submit">{$_('portal.cases.send_reply_button')}</button>
    </form>
  {/if}
</PortalShell>

<style>
  .back {
    /* The only way back on a phone, so it gets a real tap target rather than
       the 19px a bare text link would be. Measured at 390px, not assumed. */
    display: inline-flex;
    align-items: center;
    min-height: 44px;
    margin-bottom: 4px;
    font-size: 13px;
    color: var(--v2-slate, #6b7280);
  }
  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }
  .ref {
    margin: 0 0 2px;
    font-family: var(--v2-mono);
    font-size: 12px;
    color: var(--v2-slate, #6b7280);
  }
  h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    /* Long summaries must wrap rather than push the tag off a 390px screen. */
    overflow-wrap: anywhere;
  }
  .tag {
    flex: none;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--v2-rule, #f3f4f6);
    font-size: 12.5px;
  }
  .tag.open {
    background: var(--v2-moss-bg, #dcfce7);
  }
  .facts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px 16px;
    margin: 0 0 14px;
    padding: 12px 14px;
    border: 1px solid var(--v2-line, #e5e7eb);
    border-radius: 10px;
    background: var(--v2-card, #fff);
  }
  .facts dt {
    font-size: 11px;
    color: var(--v2-slate, #6b7280);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .facts dd {
    margin: 2px 0 0;
    font-size: 13.5px;
  }
  .state {
    margin: 0 0 18px;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 13.5px;
    border-left: 3px solid var(--v2-slate, #6b7280);
    background: var(--v2-line-soft, #f5f5f4);
  }
  .state.you {
    /* The one state that asks something of the customer gets the accent. */
    border-left-color: var(--v2-ember);
    background: var(--v2-ember-soft);
  }
  .state.closed a {
    margin-left: 4px;
    color: var(--v2-ember);
  }
  .desc {
    margin: 0 0 20px;
    color: var(--v2-slate, #4b5563);
    font-size: 14px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .thread {
    display: grid;
    gap: 12px;
    margin-bottom: 24px;
  }
  .msg {
    border: 1px solid var(--v2-rule, #e5e7eb);
    border-radius: 10px;
    padding: 12px 14px;
  }
  .msg.mine {
    background: var(--v2-paper-2, #f9fafb);
  }
  .msg.support {
    border-left: 3px solid var(--v2-ember-line);
  }
  .who {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 6px;
    font-size: 12.5px;
    color: var(--v2-slate, #6b7280);
  }
  .msg p {
    margin: 0;
    font-size: 14px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .reply label {
    display: block;
    margin-bottom: 6px;
    font-size: 13px;
    font-weight: 500;
  }
  textarea {
    width: 100%;
    box-sizing: border-box;
    /* 16px stops iOS Safari zooming the viewport on focus. */
    font-size: 16px;
    padding: 11px;
    border: 1px solid var(--v2-rule, #d1d5db);
    border-radius: 8px;
  }
  button {
    margin-top: 12px;
    width: 100%;
    min-height: 46px;
    font-size: 15px;
    border: 0;
    border-radius: 8px;
    background: var(--v2-ink, #111827);
    color: #fff;
    cursor: pointer;
  }
  .empty {
    color: var(--v2-slate, #6b7280);
    font-size: 14px;
  }
  .err {
    margin: 10px 0 0;
    color: var(--v2-rust, #b91c1c);
    font-size: 13px;
  }
</style>
