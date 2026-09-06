<script>
  import { enhance } from '$app/forms';
  import { resolve } from '$app/paths';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { _ } from '$lib/i18n/index.js';
  import { supportCategoryKey } from '$lib/help/labels.js';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();
  let submitting = $state(false);
</script>

<PageHeader title={$_('help.new.title')} center width="720px">
  {#snippet sub()}{$_('help.new.sub')}{/snippet}
</PageHeader>

<div class="v2-scroll">
  <div
    class="v2-pad"
    style="padding-top:18px;padding-bottom:32px;max-width:720px;margin-inline:auto"
  >
    {#if form?.error}
      <p class="v2-card error">{form.error}</p>
    {/if}

    <form
      method="POST"
      enctype="multipart/form-data"
      class="v2-card form"
      use:enhance={() => {
        submitting = true;
        return async ({ update }) => {
          await update();
          submitting = false;
        };
      }}
    >
      <div class="v2-field">
        <label for="subject">{$_('help.new.field_subject')}</label>
        <input
          id="subject"
          class="v2-input"
          name="subject"
          maxlength="200"
          required
          value={form?.subject ?? ''}
          placeholder={$_('help.new.placeholder_subject')}
        />
      </div>

      <div class="v2-field">
        <label for="category">{$_('help.new.field_category')}</label>
        <select id="category" class="v2-input" name="category" required>
          <option value="">{$_('help.new.category_placeholder')}</option>
          {#each data.categories as category (category.value)}
            <option value={category.value} selected={form?.category === category.value}
              >{$_(supportCategoryKey(category.value))}</option
            >
          {/each}
        </select>
      </div>

      <div class="v2-field">
        <label for="body">{$_('help.new.field_body')}</label>
        <textarea
          id="body"
          class="v2-input"
          name="body"
          rows="8"
          maxlength="10000"
          required
          placeholder={$_('help.new.placeholder_body')}>{form?.body ?? ''}</textarea
        >
      </div>

      <div class="v2-field">
        <label for="attachment">{$_('help.new.field_attachment')}</label>
        <input id="attachment" class="v2-input" type="file" name="attachment" />
        <span class="v2-sub" style="font-size:11.5px">{$_('help.new.attachment_hint')}</span>
      </div>

      <div class="actions">
        <button class="v2-btn v2-btn-primary" type="submit" disabled={submitting}
          >{submitting ? $_('help.new.submitting') : $_('help.new.submit')}</button
        >
        <a class="v2-btn" href={resolve('/help')}>{$_('help.new.cancel')}</a>
      </div>
    </form>
  </div>
</div>

<style>
  .form {
    padding: 18px;
    display: grid;
    gap: 18px;
  }
  .error {
    padding: 10px 13px;
    margin-bottom: 16px;
    color: var(--v2-rust);
    font-size: 13px;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
</style>
