<script>
  import { resolve } from '$app/paths';
  /**
   * A new task.
   *
   * "Attached to" is one question, not four. The model allows exactly one
   * parent and now enforces it on every path, so a form with four separate
   * pickers would let somebody fill two and learn about the rule from a 400.
   * Pick the kind, then pick the record.
   */
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { enhance } from '$app/forms';
  import { untrack } from 'svelte';
  import { ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  const KINDS = [
    { key: '', label: 'tasks.new.kind_nothing' },
    { key: 'account', label: 'tasks.new.kind_account' },
    { key: 'opportunity', label: 'tasks.new.kind_deal' },
    { key: 'case', label: 'tasks.new.kind_case' },
    { key: 'lead', label: 'tasks.new.kind_lead' }
  ];

  let values = $derived(form?.values ?? {});
  let kind = $state(untrack(() => form?.values?.parent_kind ?? ''));
  let options = $derived(kind ? (data.parents[kind] ?? []) : []);
</script>

<PageHeader title={$_('tasks.new.heading')} record center width="62ch">
  {#snippet crumb()}
    <a href={resolve('/tasks')}>{$_('tasks.new.breadcrumb_tasks')}</a>
    <ChevronRight size={12} />
    <span>{$_('tasks.new.breadcrumb_new')}</span>
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  <form
    method="POST"
    action="?/create"
    use:enhance
    class="v2-pad"
    style="padding-top:18px;padding-bottom:36px;max-width:62ch;margin-left:auto;margin-right:auto"
  >
    {#if form?.error}
      <p style="color:var(--v2-rust);font-size:12.5px;margin:0 0 14px" role="alert">{form.error}</p>
    {/if}

    <label class="v2-field">
      <span class="v2-label">{$_('tasks.new.label_title')}</span>
      <input
        class="v2-input"
        name="title"
        required
        maxlength="200"
        value={values.title ?? ''}
        placeholder={$_('tasks.new.placeholder_title')}
      />
    </label>

    <div style="display:flex;gap:12px;flex-wrap:wrap">
      <label class="v2-field" style="flex:1;min-width:150px">
        <span class="v2-label">{$_('tasks.new.label_priority')}</span>
        <select class="v2-input" name="priority" value={values.priority ?? 'Medium'}>
          <option value="Low">{$_('tasks.enums.priority.low')}</option>
          <option value="Medium">{$_('tasks.enums.priority.medium')}</option>
          <option value="High">{$_('tasks.enums.priority.high')}</option>
        </select>
      </label>
      <label class="v2-field" style="flex:1;min-width:150px">
        <span class="v2-label">{$_('tasks.new.label_status')}</span>
        <select class="v2-input" name="status" value={values.status ?? 'New'}>
          <option value="New">{$_('tasks.enums.status.new')}</option>
          <option value="In Progress">{$_('tasks.enums.status.in_progress')}</option>
          <option value="Completed">{$_('tasks.enums.status.completed')}</option>
        </select>
      </label>
      <label class="v2-field" style="flex:1;min-width:150px">
        <span class="v2-label">{$_('tasks.new.label_due')}</span>
        <input class="v2-input" type="date" name="due_date" value={values.due_date ?? ''} />
      </label>
    </div>
    <p class="v2-sub" style="font-size:11.5px;margin:-6px 0 16px">
      {$_('tasks.new.hint_due')}
    </p>

    <label class="v2-field">
      <span class="v2-label">{$_('tasks.new.label_attached')}</span>
      <select class="v2-input" name="parent_kind" bind:value={kind}>
        {#each KINDS as k (k.key)}
          <option value={k.key}>{$_(k.label)}</option>
        {/each}
      </select>
    </label>

    {#if kind}
      <label class="v2-field">
        <span class="v2-label">{$_('tasks.new.label_which')}</span>
        <select class="v2-input" name="parent_{kind}" required>
          <option value="">{$_('tasks.new.option_choose')}</option>
          {#each options as option (option.id)}
            <option value={option.id} selected={values[kind] === option.id}>{option.name}</option>
          {/each}
        </select>
        {#if options.length === 0}
          <span class="v2-sub" style="font-size:11.5px">{$_('tasks.new.which_empty')}</span>
        {/if}
      </label>
    {/if}

    <label class="v2-field">
      <span class="v2-label">{$_('tasks.new.label_assign')}</span>
      <select
        class="v2-input"
        name="assigned_to"
        multiple
        size={Math.min(data.owners.length || 1, 5)}
      >
        {#each data.owners as person (person.id)}
          <option value={person.id}>{person.name}</option>
        {/each}
      </select>
      <span class="v2-sub" style="font-size:11.5px">
        {$_('tasks.new.hint_assign')}
      </span>
    </label>

    <label class="v2-field">
      <span class="v2-label">{$_('tasks.new.label_note')}</span>
      <textarea
        class="v2-input"
        name="description"
        rows="4"
        placeholder={$_('tasks.new.placeholder_note')}>{values.description ?? ''}</textarea
      >
    </label>

    <div style="display:flex;gap:9px;margin-top:6px">
      <button class="v2-btn v2-btn-primary" type="submit">{$_('tasks.new.create_button')}</button>
      <a class="v2-btn" href={resolve('/tasks')}>{$_('tasks.new.cancel_button')}</a>
    </div>
  </form>
</div>
