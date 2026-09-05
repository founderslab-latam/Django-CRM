<script>
  import { resolve } from '$app/paths';
  import { asInternalPath } from '$lib/utils/paths.js';
  /**
   * The settings hub.
   *
   * v1 has thirteen settings routes reachable only from a dropdown, so nobody
   * could tell what was configurable without opening each one. This lists them
   * with the current value beside each. A settings index that does not tell
   * you the current state is a table of contents, not a screen.
   *
   * Grouped by what a setting decides, not by which Django app owns it:
   * "who a ticket lands on" and "what closes it" belong together whether or
   * not they live in the same models file.
   *
   * `warn` is the second reason this page exists. Each destination reports
   * whether something there needs attention, so the hub is worth opening even
   * when you did not come to change anything. A warning here always has a
   * matching explanation on the page it points to, never a badge that leads
   * to a screen with nothing on it.
   *
   * Destinations v2 has not built are listed anyway and link to v1, marked as
   * such. An index that quietly omits settings is worse than one that admits
   * where they live: people go looking, find nothing, and conclude the feature
   * does not exist.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { count, shortDate } from '$lib/v2/format.js';
  import { ChevronRight, ShieldAlert } from '@lucide/svelte';

  /** @type {{ data: any }} */
  let { data } = $props();

  let org = $derived(data.org);

  /**
   * Weekday hours as one line. When the days do not all match it says so
   * rather than printing the first day's hours; "09:00-17:00" beside a
   * calendar where four days run to 17:30 is a summary that is simply wrong,
   * and this is the number an SLA is measured against.
   */
  let hoursSummary = $derived.by(() => {
    const open = data.calendar.days.filter((d) => d.open);
    if (!open.length) return $_('settings.home.hours_none');
    const first = open[0];
    const uniform = open.every((d) => d.open === first.open && d.close === first.close);
    return uniform
      ? $_('settings.home.hours_uniform', {
          values: { count: open.length, open: first.open, close: first.close }
        })
      : $_('settings.home.hours_vary', { values: { count: open.length } });
  });

  /** An approval rule set to MANAGER with no named approvers matches nobody. */
  let stuckApprovalRules = $derived(
    data.approvalRules.filter(
      (r) => r.is_active && r.approver_role === 'MANAGER' && !r.approvers.length
    ).length
  );

  let groups = $derived([
    {
      label: $_('settings.home.group_people'),
      items: [
        {
          href: '/team',
          title: $_('settings.home.item_team_title'),
          body: $_('settings.home.item_team_body'),
          // People counts are admin-only oversight; a member's fan-out gets no
          // totals (the endpoint 403s), so the row lists the destination with
          // no value rather than a misleading zero.
          value: data.peopleTotals
            ? $_('settings.home.value_people', {
                values: {
                  count: data.peopleTotals.count,
                  admins: data.peopleTotals.admins
                }
              })
            : null,
          warn: data.peopleTotals ? data.peopleTotals.tokens_on_deactivated > 0 : false
        },
        {
          href: '/settings/api-tokens',
          title: $_('settings.home.item_api_tokens_title'),
          body: $_('settings.home.item_api_tokens_body'),
          value: data.tokenTotals
            ? $_('settings.home.value_live', { values: { count: data.tokenTotals.live } })
            : null,
          warn: data.tokenTotals
            ? data.tokenTotals.orphaned > 0 || data.tokenTotals.unused_90d > 0
            : false
        },
        {
          // Filed with access rather than with the ticket channels, though a
          // form makes leads and not tickets. What a published web form grants
          // is the ability for a stranger with no account to write into this
          // org, which is an access question; that it happens to arrive as a
          // lead is the smaller half.
          href: '/settings/web-forms',
          title: $_('settings.home.item_web_forms_title'),
          body: $_('settings.home.item_web_forms_body'),
          value: $_('settings.home.value_published', {
            values: { count: data.webFormTotals.published }
          }),
          // Forms are live and nothing has arrived in a month. Usually the
          // snippet was taken off the site it was pasted onto, which nothing
          // else would ever tell you. The destination names the individual
          // forms; this only says that at least one is silent.
          warn: data.webFormTotals.published > 0 && data.webFormTotals.submissions_30d === 0
        },
        {
          href: '/settings/organization',
          title: $_('settings.home.item_organization_title'),
          body: $_('settings.home.item_organization_body'),
          value: org.company_name,
          warn: false
        }
      ]
    },
    {
      label: $_('settings.home.group_tickets'),
      items: [
        {
          href: '/settings/routing',
          title: $_('settings.home.item_routing_title'),
          body: $_('settings.home.item_routing_body'),
          value: $_('settings.home.value_rules', {
            values: { count: data.routingTotals.active }
          }),
          warn: data.routingTotals.unrouted_last_30d > 0
        },
        {
          href: '/settings/escalation',
          title: $_('settings.home.item_escalation_title'),
          body: $_('settings.home.item_escalation_body'),
          value: $_('settings.home.value_priorities', {
            values: {
              active: data.escalationTotals.active,
              count: data.escalationTotals.count
            }
          }),
          warn: data.escalationTotals.breaches_unhandled_30d > 0
        },
        {
          href: '/settings/business-hours',
          title: $_('settings.home.item_business_hours_title'),
          body: $_('settings.home.item_business_hours_body'),
          value: `${data.calendar.name} · ${hoursSummary}`,
          warn: false
        },
        {
          href: '/settings/ticket-approvals',
          title: $_('settings.home.item_approvals_title'),
          body: $_('settings.home.item_approvals_body'),
          value: $_('settings.home.value_active', {
            values: { count: data.approvalTotals.active }
          }),
          warn: stuckApprovalRules > 0
        },
        {
          href: '/settings/reopen',
          title: $_('settings.home.item_reopen_title'),
          body: $_('settings.home.item_reopen_body'),
          // Admin-only, like people and tokens above: a member's fan-out gets
          // null (the endpoint 403s), so the row lists the destination without
          // a value rather than guessing at the policy.
          value: !data.reopen
            ? null
            : data.reopen.is_enabled
              ? $_('settings.home.value_reopen_within', {
                  values: { days: data.reopen.reopen_window_days }
                })
              : $_('settings.home.value_reopen_off'),
          // Replies arriving outside the window are normal for any window, so
          // that number belongs on the page, not on a warning here. Off is the
          // state worth flagging: it makes every reply to a closed ticket
          // vanish, not just the late ones.
          warn: data.reopen ? !data.reopen.is_enabled : false
        },
        {
          href: '/settings/inbound-email',
          title: $_('settings.home.item_inbound_title'),
          body: $_('settings.home.item_inbound_body'),
          value: $_('settings.home.value_mailboxes', {
            values: {
              active: data.mailboxTotals.active,
              count: data.mailboxTotals.count
            }
          }),
          // Off AND still receiving, not merely off. An address switched off
          // and left alone is a decision; one still getting mail and creating
          // nothing is a customer being ignored.
          warn: data.mailboxTotals.silently_dropping > 0
        }
      ]
    },
    {
      label: $_('settings.home.group_shared'),
      items: [
        {
          href: '/settings/macros',
          title: $_('settings.home.item_macros_title'),
          body: $_('settings.home.item_macros_body'),
          value: $_('settings.home.value_shared', {
            values: { count: data.macroTotals.org }
          }),
          warn: data.macroTotals.with_unknown_placeholders > 0
        },
        {
          href: '/settings/tags',
          title: $_('settings.home.item_tags_title'),
          body: $_('settings.home.item_tags_body'),
          value: $_('settings.home.value_in_use', {
            values: { count: data.tagTotals.active }
          }),
          // Unused tags are housekeeping, not a fault, the tags page lists
          // them without needing the hub to raise an alarm about tidiness.
          warn: false
        },
        {
          href: '/settings/custom-fields',
          title: $_('settings.home.item_custom_fields_title'),
          body: $_('settings.home.item_custom_fields_body'),
          value: $_('settings.home.value_fields_across', {
            values: {
              count: data.fieldTotals.active,
              models: data.fieldTotals.models_extended
            }
          }),
          warn: data.fieldTotals.required_with_gaps > 0
        },
        {
          href: '/invoices/templates',
          title: $_('settings.home.item_templates_title'),
          body: $_('settings.home.item_templates_body'),
          value: $_('settings.home.value_under_invoices'),
          warn: false
        }
      ]
    }
  ]);

  let warnings = $derived(groups.flatMap((g) => g.items).filter((i) => i.warn).length);
</script>

<PageHeader title={$_('settings.home.title')}>
  {#snippet sub()}
    {org.name} · <span class="v2-num">{count(org.member_count)}</span>
    {$_('settings.home.sub_members', { values: { count: org.member_count } })} ·
    {$_('settings.home.sub_since', { values: { date: shortDate(org.created_at) } })}
    {#if warnings}
      · <span class="v2-num">{count(warnings)}</span>
      {$_('settings.home.sub_needs_look', { values: { count: warnings } })}
    {/if}
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <div class="v2-pad" style="padding-top:18px;padding-bottom:32px">
    {#each groups as g (g.label)}
      <div class="v2-label" style="margin-bottom:10px">{g.label}</div>
      <div class="v2-card" style="overflow:hidden;margin-bottom:22px">
        {#each g.items as s (s.href)}
          <a class="v2-setting" href={resolve(asInternalPath(s.href))}>
            <div class="v2-setting-body">
              <b>{s.title}</b>
              <span class="v2-sub" style="font-size:11.5px">{s.body}</span>
            </div>
            {#if s.warn}
              <ShieldAlert size={15} style="color:var(--v2-clay);flex:none" />
            {/if}
            {#if s.value}
              <span class="v2-sub v2-setting-value">{s.value}</span>
            {/if}
            <ChevronRight size={15} style="color:var(--v2-slate);flex:none" />
          </a>
        {/each}
      </div>
    {/each}

    <!--
      The org API key is deliberately absent from this page. It is a
      credential, it was once exposed through nested serializers, and a
      settings screen that renders it is how the next leak happens. Rotating
      or revealing it belongs behind an explicit, audited action, not on an
      index anyone with the URL can load.
    -->
    <p class="v2-sub" style="font-size:11.5px;margin-top:18px;max-width:64ch">
      {$_('settings.home.apikey_note_before')}<a
        href={resolve('/settings/api-tokens')}
        style="color:inherit">{$_('settings.home.apikey_note_link')}</a
      >{$_('settings.home.apikey_note_after')}
    </p>
  </div>
</div>

<style>
  .v2-setting-value {
    font-size: 12px;
    text-align: right;
  }

  /* At 414px the value column squeezes the title to a couple of words per
     line. Drop it. The destination and what it does are what you navigate
     by, and every value is repeated on the page it points to. */
  @media (max-width: 640px) {
    .v2-setting-value {
      display: none;
    }
  }
</style>
