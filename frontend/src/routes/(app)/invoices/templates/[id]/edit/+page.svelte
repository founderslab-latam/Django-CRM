<script>
  import { resolve } from '$app/paths';
  /**
   * Editing an invoice template: the brand fields, the boilerplate text, and
   * the two markup fields no other page in this app is allowed to receive.
   *
   * THE MARKUP RULE. `template_html` and `template_css` are bound to
   * `<textarea>` values and nothing else. A textarea's value is text, never
   * parsed as markup, which is what makes showing them safe here. `{@html}`
   * appears nowhere in this app and must never appear on this page: these two
   * fields are org-authored HTML that WeasyPrint renders into a PDF
   * server-side, so putting either into the DOM turns a PDF setting into
   * stored XSS. Every other read path strips them for exactly that reason;
   * this page reads the dedicated admin-only editor route instead.
   *
   * `is_default` is absent on purpose. One template holds it at a time and the
   * list page owns the swap ("Use instead of ..."), so an unchecked box here
   * cannot ride along with an unrelated save and leave the org with no default.
   *
   * VALIDATION HERE IS A UX HINT. `PUT /api/invoices/templates/<id>/` is
   * admin-gated server-side and enforces that regardless of what this page
   * draws; curl and the mobile client never pass through here.
   */
  import { enhance } from '$app/forms';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import { ChevronRight, Lock, FileCode } from '@lucide/svelte';
  import { _ } from '$lib/i18n/index.js';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  // A failed save re-renders with what was typed; a fresh load uses the saved
  // record. Without the fallback an admin loses their edits on any 400.
  let values = $derived(form?.values ?? data.template ?? {});
</script>

<PageHeader
  title={data.template?.name ?? $_('invoices.templates.edit.title_fallback')}
  record
  center
  width="72ch"
>
  {#snippet crumb()}
    <a href={resolve('/invoices/templates')}>{$_('invoices.templates.edit.crumb_templates')}</a>
    <ChevronRight size={12} />
    <span>{$_('invoices.templates.edit.crumb_edit')}</span>
  {/snippet}
</PageHeader>

<div class="v2-scroll">
  {#if !data.can_edit}
    <div class="v2-pad" style="padding-top:24px;max-width:56ch;margin-left:auto;margin-right:auto">
      <div class="v2-next" role="note">
        <Lock size={17} style="flex:none" />
        <div class="v2-next-body">
          <div style="font-weight:600">{$_('invoices.templates.edit.admins_only_heading')}</div>
          <div class="v2-sub" style="margin-top:2px">
            {$_('invoices.templates.edit.admins_only_body')}
          </div>
        </div>
      </div>
      <a class="v2-btn" href={resolve('/invoices/templates')} style="margin-top:16px"
        >{$_('invoices.templates.edit.back_to_templates')}</a
      >
    </div>
  {:else}
    <form
      method="POST"
      action="?/save"
      enctype="multipart/form-data"
      use:enhance
      class="v2-pad"
      style="padding-top:18px;padding-bottom:36px;max-width:72ch;margin-left:auto;margin-right:auto"
    >
      {#if form?.error}
        <p style="color:var(--v2-rust);font-size:12.5px;margin:0 0 14px" role="alert">
          {form.error}
        </p>
      {/if}

      <label class="v2-field">
        <span class="v2-label">{$_('invoices.templates.edit.field_name')}</span>
        <input class="v2-input" name="name" required maxlength="100" value={values.name ?? ''} />
      </label>

      <div class="color-row">
        <label class="color-field">
          <span class="v2-label">{$_('invoices.templates.edit.field_primary_color')}</span>
          <input
            class="color-swatch"
            type="color"
            name="primary_color"
            value={values.primary_color || '#3B82F6'}
          />
        </label>
        <label class="color-field">
          <span class="v2-label">{$_('invoices.templates.edit.field_secondary_color')}</span>
          <input
            class="color-swatch"
            type="color"
            name="secondary_color"
            value={values.secondary_color || '#1E40AF'}
          />
        </label>
      </div>

      <label class="v2-field">
        <span class="v2-label">
          {$_('invoices.templates.edit.field_logo')}
          <span class="opt"
            >{data.template?.has_logo
              ? $_('invoices.templates.edit.logo_replaces')
              : $_('invoices.templates.edit.optional')}</span
          >
        </span>
        <input class="v2-input" type="file" name="logo" accept="image/*" />
      </label>

      <label class="v2-field">
        <span class="v2-label"
          >{$_('invoices.templates.edit.field_default_notes')}
          <span class="opt">{$_('invoices.templates.edit.optional')}</span></span
        >
        <textarea class="v2-input" name="default_notes" rows="3"
          >{values.default_notes ?? ''}</textarea
        >
      </label>

      <label class="v2-field">
        <span class="v2-label"
          >{$_('invoices.templates.edit.field_default_terms')}
          <span class="opt">{$_('invoices.templates.edit.optional')}</span></span
        >
        <textarea class="v2-input" name="default_terms" rows="3"
          >{values.default_terms ?? ''}</textarea
        >
      </label>

      <label class="v2-field">
        <span class="v2-label"
          >{$_('invoices.templates.edit.field_footer_text')}
          <span class="opt">{$_('invoices.templates.edit.optional')}</span></span
        >
        <textarea class="v2-input" name="footer_text" rows="2">{values.footer_text ?? ''}</textarea>
      </label>

      <div class="markup-note" role="note">
        <FileCode size={14} style="flex:none;margin-top:2px" />
        <div>
          <strong>{$_('invoices.templates.edit.custom_layout_heading')}</strong>
          <div class="v2-sub" style="margin-top:2px">
            {$_('invoices.templates.edit.custom_layout_body')}
          </div>
        </div>
      </div>

      <label class="v2-field">
        <span class="v2-label"
          >{$_('invoices.templates.edit.field_template_html')}
          <span class="opt">{$_('invoices.templates.edit.optional')}</span></span
        >
        <textarea class="v2-input mono" name="template_html" rows="10" spellcheck="false"
          >{values.template_html ?? ''}</textarea
        >
      </label>

      <label class="v2-field">
        <span class="v2-label"
          >{$_('invoices.templates.edit.field_template_css')}
          <span class="opt">{$_('invoices.templates.edit.optional')}</span></span
        >
        <textarea class="v2-input mono" name="template_css" rows="6" spellcheck="false"
          >{values.template_css ?? ''}</textarea
        >
      </label>

      {#if data.template?.is_default}
        <p class="v2-sub" style="font-size:11.5px;margin:0 0 16px">
          {$_('invoices.templates.edit.is_default_note')}
        </p>
      {/if}

      <div style="display:flex;gap:9px;margin-top:6px">
        <button class="v2-btn v2-btn-primary" type="submit"
          >{$_('invoices.templates.edit.save')}</button
        >
        <a class="v2-btn" href={resolve('/invoices/templates')}
          >{$_('invoices.templates.edit.cancel')}</a
        >
      </div>
    </form>
  {/if}
</div>

<style>
  .opt {
    text-transform: none;
    font-weight: 500;
    letter-spacing: 0;
    color: var(--v2-slate);
  }
  .color-row {
    display: flex;
    gap: 16px;
  }
  .color-field {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .color-swatch {
    width: 56px;
    height: 38px;
    padding: 3px;
    border: 1px solid var(--v2-line);
    border-radius: 8px;
    background: var(--v2-card);
    cursor: pointer;
  }
  .markup-note {
    display: flex;
    gap: 9px;
    align-items: flex-start;
    font-size: 12.5px;
    padding: 11px 12px;
    margin: 4px 0 16px;
    border: 1px solid var(--v2-line);
    border-radius: 9px;
    background: var(--v2-card);
  }
  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px;
    line-height: 1.55;
  }
</style>
