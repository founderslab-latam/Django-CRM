<script>
  import { resolve } from '$app/paths';
  import { enhance } from '$app/forms';
  import { _ } from '$lib/i18n/index.js';
  import { ChevronRight, TriangleAlert } from '@lucide/svelte';

  /** @type {{ data: { currencies: any[] }, form: any }} */
  let { data, form: result } = $props();

  const COUNTRIES = [
    { value: '', label: '—' },
    { value: 'CL', label: 'Chile' },
    { value: 'AR', label: 'Argentina' },
    { value: 'MX', label: 'Mexico' },
    { value: 'CO', label: 'Colombia' },
    { value: 'PE', label: 'Peru' },
    { value: 'US', label: 'United States' },
    { value: 'ES', label: 'Spain' },
    { value: 'BR', label: 'Brazil' }
  ];

  const v = (/** @type {string} */ k) => result?.values?.[k] ?? '';
</script>

<div class="v2-scroll v2-pad" style="padding-top:18px">
  <nav class="v2-crumbs" style="margin-bottom:10px">
    <a href={resolve('/operator')}>{$_('operator.list.title')}</a>
    <ChevronRight size={12} />
    <span>{$_('operator.new.title')}</span>
  </nav>
  <h1 style="font-size:19px;margin:0 0 14px">{$_('operator.new.title')}</h1>

  {#if result?.error}
    <div class="v2-next" role="alert" style="border-color:var(--v2-rust);margin-bottom:16px">
      <TriangleAlert size={16} style="color:var(--v2-rust);flex:none" />
      <div class="v2-next-body"><div class="v2-sub">{result.error}</div></div>
    </div>
  {/if}

  <form method="POST" action="?/create" class="v2-form" use:enhance style="max-width:520px">
    <div class="v2-field">
      <label for="f-name">{$_('operator.new.label_name')}</label>
      <input id="f-name" name="name" class="v2-input" maxlength="100" value={v('name')} required />
    </div>

    <div class="pair">
      <div class="v2-field">
        <label for="f-cur">{$_('operator.new.label_currency')}</label>
        <select id="f-cur" name="default_currency" class="v2-input">
          {#each data.currencies as c (c.value)}
            <option value={c.value} selected={v('default_currency') === c.value}>{c.label}</option>
          {/each}
        </select>
      </div>
      <div class="v2-field">
        <label for="f-country">{$_('operator.new.label_country')}</label>
        <select id="f-country" name="default_country" class="v2-input">
          {#each COUNTRIES as c (c.value)}
            <option value={c.value} selected={v('default_country') === c.value}>{c.label}</option>
          {/each}
        </select>
      </div>
    </div>

    <div class="v2-field">
      <label for="f-sub">{$_('operator.new.label_subdomain')}</label>
      <input
        id="f-sub"
        name="subdomain"
        class="v2-input"
        maxlength="63"
        placeholder="acme"
        value={v('subdomain')}
      />
      <p class="v2-hint">{$_('operator.new.hint_subdomain')}</p>
    </div>

    <div class="v2-field">
      <label for="f-admin">{$_('operator.new.label_admin_email')}</label>
      <input
        id="f-admin"
        name="admin_email"
        type="email"
        class="v2-input"
        value={v('admin_email')}
      />
      <p class="v2-hint">{$_('operator.new.hint_admin_email')}</p>
    </div>

    <div class="actions">
      <button class="v2-btn v2-btn-primary" type="submit">{$_('operator.new.submit')}</button>
      <a class="v2-btn" href={resolve('/operator')}>{$_('operator.new.cancel')}</a>
    </div>
  </form>
</div>

<style>
  .pair {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .actions {
    display: flex;
    gap: 9px;
    margin-top: 20px;
  }
  @media (max-width: 640px) {
    .pair {
      grid-template-columns: 1fr;
    }
  }
</style>
