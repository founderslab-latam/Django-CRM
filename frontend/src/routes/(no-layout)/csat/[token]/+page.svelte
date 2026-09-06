<script>
  /**
   * The satisfaction survey: the shortest page in the product, and the only
   * one whose success is measured in whether people bother.
   *
   * ── ONE QUESTION, ANSWERED BEFORE THE PAGE LOADS ─────────────────────────
   * The link arrives in an email that already shows five stars, so the
   * customer's first click happens in their mail client and this page is where
   * they land afterwards. It is a CONFIRMATION, not a form: the rating they
   * picked is pre-selected, and the only remaining decision is whether to say
   * anything else. The comment box is optional and below the fold of the
   * decision. Asking for prose is how a one-click survey becomes a
   * zero-response survey.
   *
   * ── STATES ARE SERVER-DECIDED ────────────────────────────────────────────
   * Expired and unknown links come back from the API as `gone` (410); the page
   * never subtracts timestamps to work out whether a link is still live. The
   * edit window is the server's too: it stamps `editable_until`, and the POST
   * is what rejects a late change. This page only reports the window, it does
   * not enforce it.
   */
  import { enhance } from '$app/forms';
  import { untrack } from 'svelte';
  import PortalShell from '$lib/v2/components/PortalShell.svelte';
  import { longDate, relativeDays } from '$lib/v2/format.js';
  import { _ } from '$lib/i18n/index.js';
  import { Star, CheckCircle2, Clock } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let survey = $derived(data.survey);

  // Seeded once from the loader; after that it is theirs to change. A rating
  // already stored wins over the star clicked in the email: inside the edit
  // window this page is reached by someone revisiting their own answer, and
  // showing them the old email's star instead of what they submitted would
  // read as the answer having been lost.
  let rating = $state(untrack(() => data.survey?.rating ?? data.clickedRating ?? 0));
  let comment = $state(untrack(() => data.survey?.comment ?? ''));
  let hover = $state(0);
  let submitting = $state(false);

  let SCALE_ENDS = $derived({ 1: $_('csat.survey.scale_low'), 5: $_('csat.survey.scale_high') });
</script>

<svelte:head>
  <title>{$_('csat.survey.head_title', { values: { org: survey?.orgName ?? $_('csat.survey.head_title_fallback') } })}</title>
</svelte:head>

<PortalShell>
  <div class="wrap">
    {#if data.gone}
      <!-- Expired or unknown links are the majority of late traffic here. The
           copy does not apologise; it gives the one route that still works. -->
      <section class="card center">
        <Clock size={22} />
        <h1>{$_('csat.survey.closed_heading')}</h1>
        <p>{$_('csat.survey.closed_detail')}</p>
      </section>
    {:else if data.invalid}
      <section class="card center">
        <Clock size={22} />
        <h1>{$_('csat.survey.invalid_heading')}</h1>
        <p>{$_('csat.survey.invalid_detail')}</p>
      </section>
    {:else if data.error}
      <section class="card center">
        <Clock size={22} />
        <h1>{$_('csat.survey.error_heading')}</h1>
        <p>{data.error}</p>
      </section>
    {:else if form?.success}
      <section class="card center">
        <div class="tick"><CheckCircle2 size={26} /></div>
        <h1>{$_('csat.survey.thanks_heading')}</h1>
        <p>
          {$_('csat.survey.thanks_detail', {
            values: {
              rating: form.rating,
              agent: survey?.agentName ?? $_('csat.survey.thanks_agent_fallback')
            }
          })}
        </p>
      </section>
    {:else if survey}
      <section class="card">
        <header>
          <div class="org">{survey.orgName}</div>
          <h1>{$_('csat.survey.heading')}</h1>
          <p class="ctx">
            {#if survey.closedAt}{$_('csat.survey.context_closed', {
                values: { agent: survey.agentName, when: relativeDays(survey.closedAt) }
              })}{:else}{$_('csat.survey.context_handled', {
                values: { agent: survey.agentName }
              })}{/if},
            <span class="subject">“{survey.ticketSubject}”</span>
          </p>
        </header>

        {#if survey.respondedAt && survey.editableUntil}
          <!-- Coming back to an answered survey. Say what is on file and by when
               it can change, rather than silently showing a pre-filled form. -->
          <div class="prior">
            {$_('csat.survey.prior_before')}<b
              >{$_('csat.survey.prior_score', { values: { rating: survey.rating } })}</b
            >{$_('csat.survey.prior_after', {
              values: {
                when: relativeDays(survey.respondedAt),
                until: longDate(survey.editableUntil)
              }
            })}
          </div>
        {/if}

        <form
          method="POST"
          action="?/submit"
          use:enhance={() => {
            submitting = true;
            return async ({ update }) => {
              submitting = false;
              await update();
            };
          }}
        >
          <input type="hidden" name="rating" value={rating} />

          <div class="stars" role="radiogroup" aria-label={$_('csat.survey.stars_aria')}>
            {#each [1, 2, 3, 4, 5] as n (n)}
              <button
                type="button"
                role="radio"
                aria-checked={rating === n}
                aria-label={SCALE_ENDS[n] ? `${n}. ${SCALE_ENDS[n]}` : `${n}`}
                class="star"
                class:on={(hover || rating) >= n}
                onclick={() => (rating = n)}
                onmouseenter={() => (hover = n)}
                onmouseleave={() => (hover = 0)}
                onfocus={() => (hover = n)}
                onblur={() => (hover = 0)}
              >
                <Star size={34} />
              </button>
            {/each}
          </div>
          <div class="scale">
            <span>{SCALE_ENDS[1]}</span>
            <span>{SCALE_ENDS[5]}</span>
          </div>

          <!-- The comment appears only once a rating exists. Before that it is a
               second thing to decide about, and the rating is the one that
               matters. -->
          {#if rating}
            <label class="comment">
              <span>{$_('csat.survey.comment_label')} <i>{$_('csat.survey.comment_optional')}</i></span>
              <textarea
                name="comment"
                rows="3"
                bind:value={comment}
                placeholder={rating <= 2
                  ? $_('csat.survey.comment_placeholder_low')
                  : $_('csat.survey.comment_placeholder_high')}></textarea>
            </label>

            {#if form?.error}
              <div class="err">{form.error}</div>
            {/if}

            <button class="v2-btn v2-btn-primary submit" type="submit" disabled={submitting}>
              {submitting
                ? $_('csat.survey.sending')
                : survey.respondedAt
                  ? $_('csat.survey.update_button')
                  : $_('csat.survey.send_button')}
            </button>
          {/if}
        </form>

        <p class="fine">
          {$_('csat.survey.fine_print', { values: { org: survey.orgName } })}
        </p>
      </section>
    {/if}
  </div>
</PortalShell>

<style>
  .wrap {
    max-width: 440px;
    margin: 0 auto;
    /* One question and nothing else, so it sits in the middle of the screen
       rather than clinging to the top of a 1000px viewport. */
    min-height: calc(100vh - 200px);
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .card {
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: var(--v2-radius);
    padding: 28px 28px 24px;
  }
  .card.center {
    text-align: center;
    color: var(--v2-slate);
  }
  .card.center :global(svg) {
    color: var(--v2-slate);
  }
  .tick :global(svg) {
    color: var(--v2-moss) !important;
  }
  .org {
    font-size: 12px;
    font-weight: 600;
    color: var(--v2-slate);
  }
  h1 {
    margin: 5px 0 0;
    font-size: 21.9px;
    font-weight: 640;
    line-height: 1.2;
    letter-spacing: -0.01em;
    color: var(--v2-ink);
  }
  .center h1 {
    margin-top: 10px;
  }
  .center p {
    margin: 8px 0 0;
    font-size: 13px;
    line-height: 1.55;
  }
  .ctx {
    margin: 7px 0 0;
    font-size: 12.5px;
    color: var(--v2-slate);
    line-height: 1.5;
  }
  .subject {
    color: var(--v2-ink);
  }

  .prior {
    margin-top: 16px;
    padding: 9px 12px;
    border: 1px solid var(--v2-line);
    border-radius: 6px;
    font-size: 12.5px;
    color: var(--v2-slate);
    line-height: 1.5;
  }
  .prior b {
    color: var(--v2-ink);
  }

  .stars {
    display: flex;
    justify-content: space-between;
    gap: 4px;
    margin: 22px 0 0;
  }
  .star {
    flex: 1;
    display: flex;
    justify-content: center;
    padding: 6px 0;
    background: none;
    border: 0;
    border-radius: 6px;
    cursor: pointer;
    /* Not `--v2-line`. At border-grey these read as a disabled control; the one
       thing this page must communicate is that the stars are the button. */
    color: var(--v2-slate);
    opacity: 0.55;
    transition:
      color 0.12s,
      opacity 0.12s,
      transform 0.12s;
  }
  .star:hover {
    opacity: 1;
    transform: translateY(-1px);
  }
  .star.on {
    color: var(--v2-ember);
    opacity: 1;
  }
  .star.on :global(svg) {
    fill: currentColor;
  }
  .star:focus-visible {
    outline: 2px solid var(--v2-ember);
    outline-offset: 1px;
  }
  .scale {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--v2-slate);
    padding: 0 4px;
  }

  .comment {
    display: block;
    margin-top: 20px;
  }
  .comment span {
    display: block;
    font-size: 12.5px;
    color: var(--v2-slate);
    margin-bottom: 5px;
  }
  .comment i {
    font-style: normal;
    font-size: 11px;
    opacity: 0.8;
  }
  .comment textarea {
    width: 100%;
    padding: 9px 11px;
    font: inherit;
    font-size: 13px;
    line-height: 1.5;
    color: var(--v2-ink);
    background: var(--v2-card);
    border: 1px solid var(--v2-line);
    border-radius: 6px;
    resize: vertical;
  }
  .comment textarea:focus {
    outline: 2px solid var(--v2-ember);
    outline-offset: -1px;
  }
  .err {
    margin-top: 12px;
    padding: 8px 11px;
    border: 1px solid var(--v2-ember-line);
    border-radius: 6px;
    background: var(--v2-ember-soft);
    color: var(--v2-rust);
    font-size: 12px;
    line-height: 1.5;
  }
  .submit {
    width: 100%;
    justify-content: center;
    margin-top: 14px;
  }
  .fine {
    margin: 16px 0 0;
    font-size: 11px;
    color: var(--v2-slate);
    line-height: 1.5;
  }
</style>
