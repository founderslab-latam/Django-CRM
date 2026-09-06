<script>
  import { resolve } from '$app/paths';
  import '../../../../app.css';
  import '$lib/v2/styles/v2.css';
  import imgLogo from '$lib/assets/images/logo.png';
  import { _ } from '$lib/i18n/index.js';

  let { data } = $props();
</script>

<svelte:head>
  <title>{$_('auth.verify.head_title')}</title>
  <meta name="referrer" content="no-referrer" />
</svelte:head>

<div class="v2-root v2-auth">
  <div class="v2-auth-box">
    <a href={resolve('/')} class="v2-auth-brand">
      <img src={imgLogo} alt="" />
      <b>BottleCRM</b>
    </a>

    <div class="v2-auth-card" style="text-align:center">
      {#if data.error}
        <div class="v2-auth-head" style="margin-bottom:16px">
          <h1>{$_('auth.verify.error_heading')}</h1>
          <p>{data.error}</p>
        </div>
        <a href={resolve('/login')} class="v2-btn v2-btn-block">{$_('auth.verify.back_to_sign_in')}</a>
      {:else}
        <div
          class="v2-spin"
          style="width:26px;height:26px;margin:4px auto 15px;color:var(--v2-ember)"
        ></div>
        <div class="v2-auth-head" style="margin-bottom:0">
          <h1>{$_('auth.verify.signing_in_heading')}</h1>
          <p>{$_('auth.verify.signing_in_detail')}</p>
        </div>
      {/if}
    </div>
  </div>
</div>
