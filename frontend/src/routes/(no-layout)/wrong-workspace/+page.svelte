<script>
  import '../../../app.css';
  import '$lib/v2/styles/v2.css';
  import imgLogo from '$lib/assets/images/logo.png';
  import { TriangleAlert } from '@lucide/svelte';
  import { _ } from '$lib/i18n/index.js';

  // `locale` in the default only satisfies the type merged in from the root
  // layout's i18n load; it is never read before real `data` arrives.
  let { data = { orgName: '', mainAppUrl: '/', signedInAs: '', locale: 'en' } } = $props();
</script>

<svelte:head>
  <title>{$_('wrong_workspace.head_title')}</title>
</svelte:head>

<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <span class="v2-auth-brand">
      <img src={imgLogo} alt="" />
      <b>BottleCRM</b>
    </span>

    <div class="v2-auth-card">
      <div class="v2-auth-head">
        <TriangleAlert size={22} style="color:var(--v2-rust)" />
        <h1>{$_('wrong_workspace.heading')}</h1>
        <p>
          {data.orgName
            ? $_('wrong_workspace.body', { values: { org: data.orgName } })
            : $_('wrong_workspace.body_generic')}
        </p>
        {#if data.signedInAs}
          <p class="v2-sub">
            {$_('wrong_workspace.signed_in_as', { values: { email: data.signedInAs } })}
          </p>
        {/if}
      </div>

      <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- external origin (the bare base domain), not an app route -->
      <a class="v2-btn v2-btn-primary" href={data.mainAppUrl} data-sveltekit-reload>
        {$_('wrong_workspace.go_to_main_app')}
      </a>
    </div>
  </div>
</div>

<style>
  .v2-auth-head {
    text-align: center;
  }
  .v2-auth-card a.v2-btn {
    width: 100%;
    justify-content: center;
    margin-top: 6px;
  }
</style>
