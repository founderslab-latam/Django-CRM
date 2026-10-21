<script>
  /**
   * The QwidX CRM wordmark for the product's own screens (sign-in, workspace
   * picker). Not for the app sidebar: that shows the tenant's own name/logo.
   *
   * Two rasters rather than one SVG: the mark has 3D shading that does not
   * survive vectorising. The dark variant lifts the navy "Qwid" so it reads
   * on a dark canvas; `.dark` on <html> picks it.
   */
  import logoLight from '$lib/assets/images/qwidx-logo.png';
  import logoDark from '$lib/assets/images/qwidx-logo-dark.png';
</script>

<span class="v2-brand-logo">
  <img class="v2-brand-logo-light" src={logoLight} alt="QwidX CRM" />
  <img class="v2-brand-logo-dark" src={logoDark} alt="QwidX CRM" />
</span>

<style>
  .v2-brand-logo img {
    height: 30px;
    border-radius: 0;
    width: auto;
    display: block;
  }
  .v2-brand-logo-dark,
  :global(.dark) .v2-brand-logo-light {
    display: none !important;
  }
  :global(.dark) .v2-brand-logo-dark {
    display: block !important;
  }
</style>
