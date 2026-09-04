<script>
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import { money, count } from '$lib/v2/format.js';
  import { Target } from '@lucide/svelte';
  import { _ } from '$lib/i18n/index.js';

  /** @type {{ data: any }} */
  let { data } = $props();

  const TONE_VAR = {
    rust: 'var(--v2-rust)',
    clay: 'var(--v2-clay)',
    slate: 'var(--v2-slate)',
    moss: 'var(--v2-moss)'
  };

  let { queue, summary, later, goals } = $derived(data);

  /** Revenue goals are money; deals and activities goals are plain counts. */
  const goalValue = (g, n) => (g.goal_type === 'REVENUE' ? money(n, data.org.currency) : count(n));

  /**
   * Coloured on the server's pace judgement, not on the raw percentage, so the
   * strip agrees with the goals page rather than calling a goal green in week
   * two of a quarter for being 40% of the way there.
   */
  const goalColor = (g) =>
    g.status === 'completed'
      ? 'var(--v2-moss)'
      : g.status === 'behind'
        ? 'var(--v2-rust)'
        : g.status === 'at_risk'
          ? 'var(--v2-clay)'
          : 'var(--v2-slate)';

  // Built as one translated string rather than conditional markup: the "quiet
  // deals" clause only makes sense when there are any, and the numbers are
  // often zero in a real org, so the copy adapts instead of reading "0 deals
  // … have gone quiet." Pluralisation is delegated to the catalog (ICU plural
  // syntax) rather than assembled here, so each locale can inflect on its own
  // rules instead of inheriting English's singular/plural split.
  //
  // It used to close with "Those are first", which was generated from a count
  // rather than from the sort it described. Quiet deals rank below overdue
  // invoices, so on the seeded org all seven of them fell off the end of the
  // list the sentence had just promised to lead with.
  let subText = $derived(
    summary.count === 0
      ? $_('dashboard.today.all_clear')
      : summary.quiet_deals === 0
        ? $_('dashboard.today.summary_no_quiet', { values: { count: summary.count } })
        : $_('dashboard.today.summary_with_quiet', {
            values: {
              count: summary.count,
              quietDeals: summary.quiet_deals,
              quietValue: money(summary.quiet_value, data.org.currency)
            }
          })
  );

  // The queue shows the most urgent 8. Everything past that is real work with
  // nowhere on this page to go, so name it and link each source to its own
  // list. "That's everything" is only true when nothing was left out.
  let hidden = $derived(Math.max(0, summary.count - summary.shown));
</script>

<PageHeader title={$_('dashboard.today.title')}>
  {#snippet sub()}{subText}{/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:14px;padding-bottom:26px">
    <!--
      Only the top item gets the ember button. Five ember buttons down a page
      is v1's mistake in a new coat: if everything is the primary action then
      nothing is, and the colour stops carrying information.
    -->
    {#each queue as item, i (item.id)}
      <div class="v2-card" style="margin-bottom:8px">
        <div class="v2-queue-item">
          <span class="v2-queue-spine" style="background:{TONE_VAR[item.tone]}"></span>
          <div class="v2-queue-body">
            <a href={resolve(item.href)} style="color:inherit;text-decoration:none">
              <div style="font-weight:640;letter-spacing:-0.012em">{item.title}</div>
            </a>
            <div class="v2-sub" style="margin-top:2px">{item.detail}</div>
          </div>
          <!-- On a phone these drop to their own line rather than squeezing
               the title into three words per row. -->
          <div class="v2-queue-actions">
            <Pill tone={item.tone}>{item.due}</Pill>
            <a class="v2-btn" class:v2-btn-primary={i === 0} href={resolve(item.href)}
              >{item.action}</a
            >
          </div>
        </div>
      </div>
    {/each}

    {#if queue.length && hidden === 0}
      <p class="v2-sub" style="margin:15px 0 21px;font-size:12.5px">
        {$_('dashboard.today.everything_done')}
      </p>
    {:else if queue.length}
      <p class="v2-sub" style="margin:15px 0 21px;font-size:12.5px">
        <span class="v2-num">{hidden}</span>
        {$_('dashboard.today.more_waiting', { values: { count: hidden } })}
        {#each summary.sources as source, i (source.href)}<a
            href={resolve(source.href)}
            style="color:inherit">{source.count} {source.label}</a
          >{i < summary.sources.length - 1 ? ', ' : '.'}{/each}
      </p>
    {:else}
      <div class="v2-card" style="margin-bottom:8px">
        <div class="v2-pad" style="padding:20px;text-align:center">
          <div style="font-weight:640;letter-spacing:-0.012em">
            {$_('dashboard.today.inbox_zero_title')}
          </div>
          <div class="v2-sub" style="margin-top:3px">
            {$_('dashboard.today.inbox_zero_detail')}
          </div>
        </div>
      </div>
    {/if}

    <!--
      Where you stand, under what needs doing.

      The queue is about today and a quota is about the period, so this sits
      below the queue rather than above it: it is context for the work, not
      work. It shows only goals running right now, narrowed server-side to the
      ones the reader may see, and stays out of the way entirely when there are
      none.
    -->
    {#if goals.length}
      <div class="v2-label" style="margin:6px 0 9px">
        <Target size={12} style="vertical-align:-1px;margin-right:4px" />
        {$_('dashboard.today.goals_heading')}
      </div>
      <div class="goals">
        {#each goals as g (g.id)}
          <a class="v2-card goal" href={resolve('/goals')}>
            <div class="goal-head">
              <span class="goal-name">{g.name}</span>
              <span class="v2-num" style="font-weight:650;font-size:12.5px;color:{goalColor(g)}">
                {g.progress_percent}%
              </span>
            </div>
            <div class="v2-bar" style="margin-top:8px">
              <i style="width:{g.progress_percent}%;background:{goalColor(g)}"></i>
            </div>
            <div class="v2-sub" style="font-size:11.5px;margin-top:6px">
              {$_('dashboard.today.goal_progress', {
                values: {
                  progress: goalValue(g, g.progress_value),
                  target: goalValue(g, g.target_value)
                }
              })}
            </div>
          </a>
        {/each}
      </div>
    {/if}

    {#if later.length}
      <div class="v2-label" style="margin:6px 0 9px">{$_('dashboard.today.later_heading')}</div>
      {#each later as row (row.id)}
        <div
          style="display:flex;gap:13px;align-items:baseline;padding:9px 3px;border-bottom:1px solid var(--v2-line-soft)"
        >
          <!-- The day is a short word, not a label, sentence case, same as the mocks. -->
          <span class="v2-muted" style="font-size:11.5px;font-weight:650;width:26px;flex:none"
            >{row.day}</span
          >
          <span style="flex:1;font-size:13.5px">{row.title}</span>
          <span class="v2-sub" style="font-size:11.5px">{row.meta}</span>
        </div>
      {/each}
    {/if}

    {#if summary.cleared_yesterday > 0}
      <p class="v2-sub" style="margin-top:20px;font-size:12px">
        {$_('dashboard.today.cleared_yesterday_prefix')}
        <span class="v2-num">{summary.cleared_yesterday}</span>.
      </p>
    {/if}
  </div>
</div>

<style>
  /*
    Phone first: one goal per row at 390px, where three across would leave each
    bar too short to read. Widens from the 768px breakpoint v2.css already uses.
  */
  .goals {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    margin-bottom: 18px;
  }

  .goal {
    display: block;
    padding: 13px 15px;
    color: inherit;
    text-decoration: none;
  }

  .goal-head {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }

  .goal-name {
    flex: 1;
    min-width: 0;
    font-weight: 600;
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  @media (min-width: 768px) {
    .goals {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }
</style>
