<script>
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import { shortDate } from '$lib/v2/format.js';
  import { ShieldCheck, Plus, TriangleAlert } from '@lucide/svelte';

  /** @type {{ data: { orgs: any[], filter: { status: string, search: string } }, form: any }} */
  let { data, form } = $props();

  const STATUS_TONE = /** @type {Record<string, string>} */ ({
    ACTIVE: 'moss',
    SUSPENDED: 'rust',
    DELETED: 'slate'
  });

  /** Ask for a reason, inject it into the request; cancel if dismissed. */
  const withReason =
    (promptKey) =>
    ({ formData, cancel }) => {
      const r = prompt($_(promptKey));
      if (r === null) {
        cancel();
        return;
      }
      formData.set('reason', r.trim());
    };

  /** Confirm a destructive action by org name; cancel if declined. */
  const confirmDelete =
    (name) =>
    ({ cancel }) => {
      if (!confirm($_('operator.list.delete_confirm', { values: { org: name } }))) cancel();
    };
</script>

<div class="v2-scroll v2-pad" style="padding-top:18px">
  <header class="op-head">
    <div>
      <h1>{$_('operator.list.title')}</h1>
      <p class="v2-sub">{$_('operator.list.subtitle')}</p>
    </div>
    <a class="v2-btn v2-btn-primary" href={resolve('/operator/new')}>
      <Plus size={15} />
      {$_('operator.list.new_button')}
    </a>
  </header>

  {#if form?.error}
    <div class="v2-next" role="alert" style="border-color:var(--v2-rust);margin-bottom:14px">
      <TriangleAlert size={16} style="color:var(--v2-rust);flex:none" />
      <div class="v2-next-body"><div class="v2-sub">{form.error}</div></div>
    </div>
  {/if}

  <form method="GET" class="op-filters">
    <input
      type="search"
      name="search"
      class="v2-input"
      placeholder={$_('operator.list.search_placeholder')}
      value={data.filter.search}
    />
    <select name="status" class="v2-input">
      <option value="">{$_('operator.list.filter_all')}</option>
      <option value="ACTIVE" selected={data.filter.status === 'ACTIVE'}
        >{$_('operator.status.active')}</option
      >
      <option value="SUSPENDED" selected={data.filter.status === 'SUSPENDED'}
        >{$_('operator.status.suspended')}</option
      >
      <option value="DELETED" selected={data.filter.status === 'DELETED'}
        >{$_('operator.status.deleted')}</option
      >
    </select>
    <button class="v2-btn" type="submit">{$_('operator.list.filter_apply')}</button>
  </form>

  <div class="op-table-wrap">
    <table class="op-table">
      <thead>
        <tr>
          <th>{$_('operator.list.col_org')}</th>
          <th>{$_('operator.list.col_status')}</th>
          <th>{$_('operator.list.col_subdomain')}</th>
          <th>{$_('operator.list.col_members')}</th>
          <th>{$_('operator.list.col_created')}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each data.orgs as org (org.id)}
          <tr>
            <td>
              <div style="font-weight:600">{org.name}</div>
              {#if org.status_reason}
                <div class="v2-sub" style="font-size:11.5px">{org.status_reason}</div>
              {/if}
            </td>
            <td>
              <span class="op-pill op-pill-{STATUS_TONE[org.status] ?? 'slate'}">
                {$_(`operator.status.${org.status.toLowerCase()}`)}
              </span>
            </td>
            <td>
              {#if org.subdomain}
                <div class="v2-num" style="font-size:12px">{org.subdomain}</div>
                <div class="v2-sub" style="font-size:11px" title={org.cname_target}>
                  CNAME → {org.cname_target}
                </div>
              {:else}
                <span class="v2-sub">—</span>
              {/if}
            </td>
            <td class="v2-num">{org.member_count}</td>
            <td class="v2-sub" style="font-size:12px">{shortDate(org.created_at)}</td>
            <td class="op-actions">
              <form method="POST" action="?/enter" use:enhance>
                <input type="hidden" name="id" value={org.id} />
                <button
                  class="v2-btn v2-btn-sm"
                  type="submit"
                  title={$_('operator.list.enter_hint')}
                >
                  <ShieldCheck size={13} />
                  {$_('operator.list.enter')}
                </button>
              </form>

              {#if org.status === 'ACTIVE'}
                <form
                  method="POST"
                  action="?/lifecycle"
                  use:enhance={withReason('operator.list.suspend_prompt')}
                >
                  <input type="hidden" name="id" value={org.id} />
                  <input type="hidden" name="action" value="suspend" />
                  <button class="v2-btn v2-btn-sm" type="submit"
                    >{$_('operator.list.suspend')}</button
                  >
                </form>
                <form method="POST" action="?/lifecycle" use:enhance={confirmDelete(org.name)}>
                  <input type="hidden" name="id" value={org.id} />
                  <input type="hidden" name="action" value="delete" />
                  <button class="v2-btn v2-btn-sm v2-btn-danger" type="submit"
                    >{$_('operator.list.delete')}</button
                  >
                </form>
              {:else if org.status === 'SUSPENDED'}
                <form method="POST" action="?/lifecycle" use:enhance>
                  <input type="hidden" name="id" value={org.id} />
                  <input type="hidden" name="action" value="reactivate" />
                  <button class="v2-btn v2-btn-sm" type="submit"
                    >{$_('operator.list.reactivate')}</button
                  >
                </form>
              {:else if org.status === 'DELETED'}
                <form method="POST" action="?/lifecycle" use:enhance>
                  <input type="hidden" name="id" value={org.id} />
                  <input type="hidden" name="action" value="restore" />
                  <button class="v2-btn v2-btn-sm" type="submit"
                    >{$_('operator.list.restore')}</button
                  >
                </form>
              {/if}
            </td>
          </tr>
        {:else}
          <tr
            ><td colspan="6" class="v2-sub" style="padding:16px">{$_('operator.list.empty')}</td
            ></tr
          >
        {/each}
      </tbody>
    </table>
  </div>
</div>

<style>
  .op-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;
  }
  .op-head h1 {
    font-size: 19px;
    margin: 0 0 2px;
  }
  .op-filters {
    display: flex;
    gap: 10px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }
  .op-filters input[type='search'] {
    flex: 1;
    min-width: 200px;
  }
  .op-filters select {
    width: auto;
  }
  .op-table-wrap {
    overflow-x: auto;
  }
  .op-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }
  .op-table th,
  .op-table td {
    text-align: left;
    padding: 9px 12px;
    border-bottom: 1px solid var(--v2-line-soft);
    vertical-align: top;
  }
  .op-table th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--v2-ink-3);
  }
  .op-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .op-actions form {
    margin: 0;
  }
  .op-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }
  .op-pill-moss {
    background: color-mix(in srgb, var(--v2-moss, #4a7) 18%, transparent);
    color: var(--v2-moss, #4a7);
  }
  .op-pill-rust {
    background: color-mix(in srgb, var(--v2-rust, #b4462e) 15%, transparent);
    color: var(--v2-rust, #b4462e);
  }
  .op-pill-slate {
    background: color-mix(in srgb, var(--v2-ink-3, #889) 15%, transparent);
    color: var(--v2-ink-3, #889);
  }
</style>
