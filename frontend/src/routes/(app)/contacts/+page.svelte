<script>
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import FilterBar from '$lib/v2/components/FilterBar.svelte';
  import Avatar from '$lib/v2/components/Avatar.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import EmptyState from '$lib/v2/components/EmptyState.svelte';
  import { count, relativeDays } from '$lib/v2/format.js';
  import { Users, PhoneOff, Plus } from '@lucide/svelte';
  import { _ } from '$lib/i18n/index.js';

  /** @type {{ data: any }} */
  let { data } = $props();

  let contacts = $derived(data.contacts);
  let totals = $derived(data.totals);
</script>

<PageHeader title={$_('contacts.list.title')}>
  {#snippet sub()}
    <span class="v2-num">{count(totals.count)}</span>
    {$_('contacts.list.people_suffix')}
    {#if !data.includeInactive && totals.inactive}
      · <span class="v2-num">{count(totals.inactive)}</span>
      {$_('contacts.list.inactive_hidden_suffix')}
    {/if}
    {#if totals.do_not_call}
      · <span class="v2-num">{count(totals.do_not_call)}</span>
      {$_('contacts.list.do_not_call_suffix')}
    {/if}
  {/snippet}
  {#snippet actions()}
    {#if data.includeInactive}
      <a class="v2-btn" href={resolve('/contacts')}>{$_('contacts.list.hide_inactive_button')}</a>
    {:else}
      <a class="v2-btn" href={resolve('/contacts?inactive=1')}
        >{$_('contacts.list.show_inactive_button')}</a
      >
    {/if}
    <a class="v2-btn v2-btn-primary" href={resolve('/contacts/new')}
      ><Plus />{$_('contacts.list.new_contact_button')}</a
    >
  {/snippet}
</PageHeader>

<FilterBar
  page="contacts"
  url={page.url}
  people={data.people}
  tags={data.tags}
  meId={data.meId}
  meta={$_('contacts.list.filter_meta')}
/>

<div class="v2-scroll">
  {#if contacts.length === 0}
    <EmptyState title={$_('contacts.list.empty_title')} body={$_('contacts.list.empty_body')}>
      {#snippet icon()}<Users size={21} />{/snippet}
      {#snippet actions()}
        <a class="v2-btn v2-btn-primary" href={resolve('/contacts/new')}
          >{$_('contacts.list.new_contact_button')}</a
        >
        <a class="v2-btn" href={resolve('/leads')}>{$_('contacts.list.go_to_leads_button')}</a>
      {/snippet}
    </EmptyState>
  {:else}
    <div class="v2-table-wrap">
      <table class="v2-table">
        <thead>
          <tr>
            <th>{$_('contacts.list.col_name')}</th>
            <th>{$_('contacts.list.col_account')}</th>
            <th>{$_('contacts.list.col_reachable_on')}</th>
            <th>{$_('contacts.list.col_email')}</th>
            <th data-m="hide">{$_('contacts.list.col_owner')}</th>
            <th class="v2-r">{$_('contacts.list.col_updated')}</th>
          </tr>
        </thead>
        <tbody>
          {#each contacts as c (c.id)}
            <tr>
              <td>
                <a
                  class="v2-row-link"
                  href={resolve(`/contacts/${c.id}`)}
                  style="display:flex;align-items:center;gap:9px"
                >
                  <Avatar name={c.name} size={26} />
                  <span>
                    <span class="v2-table-primary">{c.name}</span>
                    <span class="v2-table-secondary" style="display:block">
                      {c.title || $_('contacts.list.no_title_recorded')}
                    </span>
                  </span>
                </a>
              </td>
              <td>
                <!--
                  The linked account, not the typed-in company name.
                  `organization` is free text and routinely names a different
                  company from the account this person is attached to, so it
                  appears only where there is no link to show, and says so.
                -->
                {#if c.account}
                  <a href={resolve(`/accounts/${c.account.id}`)} style="color:inherit"
                    >{c.account.name}</a
                  >
                  {#if c.other_accounts.length}
                    <span class="v2-sub" style="font-size:11px">+{c.other_accounts.length}</span>
                  {/if}
                {:else if c.organization}
                  <span class="v2-muted" title={$_('contacts.list.organization_typed_tooltip')}>
                    {c.organization}
                  </span>
                {:else}
                  <span class="v2-muted">—</span>
                {/if}
              </td>
              <td>
                <!--
                  Two different facts, so two different marks. "Do not call" is
                  a rule about how you may contact this person; inactive is a
                  fact about whether they still work there.
                -->
                <span style="display:inline-flex;gap:6px;align-items:center">
                  {#if c.do_not_call}
                    <Pill tone="rust"
                      ><PhoneOff size={11} />{$_('contacts.list.do_not_call_pill')}</Pill
                    >
                  {:else if c.phone}
                    <span class="v2-num" style="font-size:12px">{c.phone}</span>
                  {:else}
                    <span class="v2-muted">{$_('contacts.list.no_phone')}</span>
                  {/if}
                  {#if !c.is_active}
                    <Pill tone="slate">{$_('contacts.list.inactive_pill')}</Pill>
                  {/if}
                </span>
              </td>
              <td>
                {#if c.email}
                  <a href="mailto:{c.email}" style="color:inherit">{c.email}</a>
                {:else}
                  <span class="v2-muted">{$_('contacts.list.no_email')}</span>
                {/if}
              </td>
              <td data-m="hide">{c.owner ?? $_('contacts.list.unassigned')}</td>
              <td class="v2-r v2-muted">
                <!--
                  When the record was last edited, which is all the CRM knows.
                  The mock sorted and coloured this column by `last_activity_at`,
                  when somebody last spoke to this person. Nothing stores that.
                -->
                {c.updated_at ? relativeDays(c.updated_at) : '—'}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <p class="v2-sub v2-pad" style="font-size:12px;padding-bottom:24px">
      {$_('contacts.list.showing_prefix')} <span class="v2-num">{contacts.length}</span>
      {$_('contacts.list.showing_of')}
      <span class="v2-num">{count(totals.count)}</span>
    </p>
  {/if}
</div>
