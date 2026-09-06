<script>
  import { resolve } from '$app/paths';
  /**
   * An article, and where it is in the workflow.
   *
   * Two changes from the mock, both because the real model says so:
   *
   * 1. The crumb printed `solution.id`. That is a UUID, 36 characters of
   *    nothing, in the position where a reader looks for what they are
   *    reading. The status goes there instead.
   * 2. "Related articles" is gone. The mock listed three under that heading
   *    with no stated relation, and nothing in the schema computes one. What
   *    the database does hold is the **tickets this article is filed
   *    against**, which is the same rail pointing the other way: the ticket
   *    page already links here.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import { relativeDays, longDate } from '$lib/v2/format.js';
  import { SOLUTION_STATUS_TONE, PRIORITY_TONE, CASE_STATUS_TONE } from '$lib/v2/enums.js';
  import { _ } from '$lib/i18n/index.js';
  import { solutionStatusKey } from '$lib/solutions/labels.js';
  import { caseStatusKey, casePriorityKey } from '$lib/cases/labels.js';
  import { enhance } from '$app/forms';
  import { ChevronRight, Eye, EyeOff } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let { article, tickets, hidden_ticket_count, canRelease } = $derived(data);

  /**
   * What is standing between this article and being suggested on tickets,
   * said as the next single step rather than as a description of the state.
   *
   * The action is dropped for anyone who cannot take it. The API answers 403
   *, but the sentence stays, because "an admin has to approve this" is the
   * useful half and the half a writer needs to know.
   */
  let gate = $derived.by(() => {
    if (article.is_published) return null;
    if (article.status === 'approved') {
      return {
        // Without the button, "publishing is the last step" leaves a reader
        // hunting for a control that is not theirs. Naming who does it is the
        // whole value of the sentence for everybody else.
        text: canRelease
          ? $_('solutions.detail.gate_approved_can_release')
          : $_('solutions.detail.gate_approved_member'),
        action: canRelease ? $_('solutions.detail.action_publish') : null,
        form: 'setPublished',
        value: 'true'
      };
    }
    if (article.status === 'reviewed') {
      return {
        text: canRelease
          ? $_('solutions.detail.gate_reviewed_can_release')
          : $_('solutions.detail.gate_reviewed_member'),
        action: canRelease ? $_('solutions.detail.action_approve') : null,
        form: 'setStatus',
        value: 'approved'
      };
    }
    return {
      text: $_('solutions.detail.gate_draft'),
      action: $_('solutions.detail.action_send_review'),
      form: 'setStatus',
      value: 'reviewed'
    };
  });
</script>

<PageHeader title={article.title} record>
  {#snippet crumb()}
    <a href={resolve('/solutions')}>{$_('solutions.form.crumb_kb')}</a>
    <ChevronRight size={12} />
    <span>{$_(solutionStatusKey(article.status))}</span>
  {/snippet}
  {#snippet sub()}
    {[
      article.author || $_('solutions.detail.unknown_author'),
      $_('solutions.detail.sub_edited', { values: { when: relativeDays(article.updated_at) } }),
      article.use_count
        ? $_('solutions.detail.sub_filed_on', { values: { count: article.use_count } })
        : $_('solutions.detail.sub_not_filed')
    ].join(' · ')}
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn" href={resolve(`/solutions/${article.id}/edit`)}
      >{$_('solutions.detail.edit_button')}</a
    >
    {#if article.is_published && canRelease}
      <form method="POST" action="?/setPublished" use:enhance>
        <input type="hidden" name="published" value="false" />
        <button class="v2-btn" type="submit">{$_('solutions.detail.unpublish_button')}</button>
      </form>
    {/if}
  {/snippet}
</PageHeader>

<div style="display:flex;flex:1;min-height:0;overflow:hidden">
  <div class="v2-main">
    <div class="v2-scroll">
      <div class="v2-pad" style="padding-top:16px;padding-bottom:32px">
        {#if form?.error}
          <p style="color:var(--v2-rust);font-size:12.5px;margin:0 0 14px">{form.error}</p>
        {/if}

        {#if gate}
          <div style="margin-bottom:20px">
            {#if gate.action}
              <!-- NextAction renders a plain `<button>` with no `type` when it
                   has no `href`, so inside a form it submits. That is the
                   whole mechanism: the component did not need a new prop, and
                   the one place it was a dead button is now the one place it
                   does something. -->
              <form method="POST" action="?/{gate.form}" use:enhance>
                <input
                  type="hidden"
                  name={gate.form === 'setPublished' ? 'published' : 'status'}
                  value={gate.value}
                />
                <NextAction
                  label={$_('solutions.detail.not_visible_label')}
                  text={gate.text}
                  action={gate.action}
                />
              </form>
            {:else}
              <NextAction label={$_('solutions.detail.not_visible_label')} text={gate.text} />
            {/if}
          </div>
        {/if}

        <article
          class="v2-card"
          style="padding:18px 20px;max-width:70ch;font-size:14px;line-height:1.65;white-space:pre-wrap"
        >
          {article.description}
        </article>

        <!-- The tickets this article was filed against. Real rows, and the
             other direction of the link the ticket page already draws. -->
        <div class="v2-label" style="margin:26px 0 10px">
          {tickets.length || hidden_ticket_count
            ? $_('solutions.detail.filed_against_label')
            : $_('solutions.detail.not_used_label')}
        </div>
        {#if tickets.length}
          <div class="v2-card" style="overflow:hidden;max-width:70ch">
            {#each tickets as t (t.id)}
              <a
                href={resolve(`/tickets/${t.id}`)}
                style="display:flex;gap:12px;align-items:center;padding:11px 15px;border-bottom:1px solid var(--v2-line-soft);color:inherit;text-decoration:none"
              >
                <span style="flex:1;font-size:13px;min-width:0">{t.name}</span>
                <Pill tone={CASE_STATUS_TONE[t.status]}>{$_(caseStatusKey(t.status))}</Pill>
                <Pill tone={PRIORITY_TONE[t.priority]}>{$_(casePriorityKey(t.priority))}</Pill>
              </a>
            {/each}
          </div>
        {:else if !hidden_ticket_count}
          <p class="v2-sub" style="font-size:12.5px;max-width:70ch">
            {$_('solutions.detail.no_tickets_body')}
          </p>
        {/if}

        {#if hidden_ticket_count}
          <!-- The API filters this rail to tickets the reader may open, while
               the count stays the article's real usage. Saying so is better
               than a number that quietly means something different per
               reader. -->
          <p class="v2-sub" style="font-size:12px;margin-top:10px;max-width:70ch">
            {$_('solutions.detail.hidden_tickets', { values: { count: hidden_ticket_count } })}
          </p>
        {/if}
      </div>
    </div>
  </div>

  <aside class="v2-rail">
    <div class="v2-label v2-rail-head">{$_('solutions.detail.rail_article')}</div>
    <dl class="v2-kv">
      <dt>{$_('solutions.detail.rail_status')}</dt>
      <dd>
        <Pill tone={SOLUTION_STATUS_TONE[article.status]}>
          {$_(solutionStatusKey(article.status))}
        </Pill>
      </dd>
      <dt>{$_('solutions.detail.rail_visibility')}</dt>
      <dd>
        {#if article.is_published}
          <span style="display:inline-flex;gap:5px;align-items:center">
            <Eye size={13} />{$_('solutions.detail.rail_published')}
          </span>
        {:else}
          <span
            style="display:inline-flex;gap:5px;align-items:center"
            style:color={article.awaiting_release ? 'var(--v2-clay)' : 'inherit'}
          >
            <EyeOff size={13} />{$_('solutions.detail.rail_internal')}
          </span>
        {/if}
      </dd>
      <dt>{$_('solutions.detail.rail_author')}</dt>
      <dd>{article.author || '—'}</dd>
      <dt>{$_('solutions.detail.rail_used_on')}</dt>
      <dd class="v2-num">
        {$_('solutions.detail.rail_used_on_value', { values: { count: article.use_count } })}
      </dd>
      <dt>{$_('solutions.detail.rail_written')}</dt>
      <dd>{longDate(article.created_at)}</dd>
      <dt>{$_('solutions.detail.rail_edited')}</dt>
      <dd>{longDate(article.updated_at)}</dd>
    </dl>

    <div class="v2-label v2-rail-head">{$_('solutions.detail.rail_how_used')}</div>
    <div class="v2-card" style="padding:11px 12px;font-size:12px;line-height:1.55">
      {$_('solutions.detail.rail_how_used_body')}
    </div>
  </aside>
</div>
