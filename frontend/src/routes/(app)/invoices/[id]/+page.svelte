<script>
  import { resolve } from '$app/paths';
  import { _ } from '$lib/i18n/index.js';
  import { invoiceStatusKey, paymentTermsKey } from '$lib/invoices/labels.js';
  import PageHeader from '$lib/v2/components/PageHeader.svelte';
  import NextAction from '$lib/v2/components/NextAction.svelte';
  import Pill from '$lib/v2/components/Pill.svelte';
  import { money, longDate, relativeDays, daysSince } from '$lib/v2/format.js';
  import { INVOICE_STATUS_TONE } from '$lib/v2/enums.js';
  import { enhance } from '$app/forms';
  import { ChevronRight } from '@lucide/svelte';

  /** @type {{ data: any, form: any }} */
  let { data, form } = $props();

  let { invoice, lineItems } = $derived(data);

  let daysLate = $derived(invoice.due_date ? daysSince(invoice.due_date) : null);
  let busy = $state(false);

  /** The real INVOICE_STATUS progression, up to whatever this invoice is. */
  const PATH = ['Draft', 'Sent', 'Viewed', 'Paid'];
  let reached = $derived(
    invoice.status === 'Overdue'
      ? ['Draft', 'Sent', 'Viewed']
      : PATH.slice(0, PATH.indexOf(invoice.status) + 1)
  );

  /** A form submit that flips `busy` so the buttons show they are working. */
  const working = () => {
    busy = true;
    return async (/** @type {any} */ { update }) => {
      await update();
      busy = false;
    };
  };
</script>

<PageHeader title={invoice.invoice_number} record>
  {#snippet crumb()}
    <a href={resolve('/invoices')}>{$_('invoices.detail.crumb_invoices')}</a>
    <ChevronRight size={12} />
    <a href={resolve(`/accounts/${invoice.account.id}`)}>{invoice.account.name}</a>
  {/snippet}
  {#snippet actions()}
    <a class="v2-btn" href={resolve(`/invoices/${invoice.id}/pdf`)} target="_blank" rel="noopener">
      {$_('invoices.detail.download_pdf')}
    </a>
    <form method="POST" action="?/duplicate" use:enhance={working} style="display:inline">
      <button class="v2-btn" disabled={busy}>{$_('invoices.detail.duplicate')}</button>
    </form>
    {#if !invoice.is_settled}
      <!-- In the header, not the rail: the rail is hidden below 1180px, and a
           destructive action a phone cannot reach is worse than one it can.

           One condition is the whole rule. `is_settled` is Paid or Cancelled
           (SETTLED in $lib/server/v2/invoices.js), which is exactly what
           InvoiceCancelView refuses, so a second `status !== 'Cancelled'`
           test here could never change the answer. It used to be there. -->
      <form method="POST" action="?/cancel" use:enhance={working} style="display:inline">
        <button class="v2-btn" disabled={busy} style="color:var(--v2-rust)"
          >{$_('invoices.detail.cancel')}</button
        >
      </form>
    {/if}
  {/snippet}
</PageHeader>

<div style="display:flex;flex:1;min-height:0;overflow:hidden">
  <div class="v2-main">
    <div class="v2-scroll">
      <div class="v2-pad" style="padding-top:16px;padding-bottom:32px">
        {#if form?.error}
          <div style="margin-bottom:16px">
            <NextAction label={$_('invoices.detail.action_failed')} text={form.error} tone="rust" />
          </div>
        {:else if form?.sent}
          <!-- The re-send has no other visible effect: it updates sent_at and
               re-mails the client, but the reminder counters are the automated
               schedule's, not this button's. Say so, or the click looks inert. -->
          <p
            class="v2-sub"
            style="color:var(--v2-moss);font-size:12.5px;margin:0 0 16px;font-weight:550"
          >
            {$_('invoices.detail.sent_to_client')}
          </p>
        {/if}

        {#if invoice.is_overdue}
          <div style="margin-bottom:20px">
            <NextAction
              label={$_('invoices.detail.days_past_due', { values: { count: daysLate } })}
              text={invoice.reminder_count
                ? invoice.last_reminder_sent
                  ? $_('invoices.detail.reminders_sent_with_last', {
                      values: {
                        count: invoice.reminder_count,
                        when: relativeDays(invoice.last_reminder_sent)
                      }
                    })
                  : $_('invoices.detail.reminders_sent', {
                      values: { count: invoice.reminder_count }
                    })
                : $_('invoices.detail.no_reminder_yet')}
              tone="rust"
            />
            <form method="POST" action="?/send" use:enhance={working} style="margin-top:8px">
              <button class="v2-btn v2-btn-sm" disabled={busy}
                >{$_('invoices.detail.send_reminder')}</button
              >
            </form>
          </div>
        {:else if invoice.status === 'Draft'}
          <div style="margin-bottom:20px">
            <NextAction text={$_('invoices.detail.never_sent')} />
            <form method="POST" action="?/send" use:enhance={working} style="margin-top:8px">
              <button class="v2-btn v2-btn-sm" disabled={busy}
                >{$_('invoices.detail.send_it')}</button
              >
            </form>
          </div>
        {/if}

        <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:20px">
          {#each PATH as step, i (step)}
            {#if i > 0}<ChevronRight size={12} style="color:var(--v2-slate)" />{/if}
            <span
              class="v2-pill"
              style={reached.includes(step)
                ? `color:var(--v2-ink);background:color-mix(in srgb, var(--v2-ink) 9%, transparent)`
                : 'color:var(--v2-slate);background:var(--v2-line-soft)'}
            >
              {$_(invoiceStatusKey(step))}
            </span>
          {/each}
          {#if invoice.is_overdue}
            <ChevronRight size={12} style="color:var(--v2-slate)" />
            <Pill tone="rust">{$_(invoiceStatusKey('Overdue'))}</Pill>
          {:else if invoice.status === 'Cancelled'}
            <ChevronRight size={12} style="color:var(--v2-slate)" />
            <Pill tone="slate">{$_(invoiceStatusKey('Cancelled'))}</Pill>
          {/if}
          <span class="v2-sub" style="margin-left:10px">
            {$_('invoices.detail.issued_due', {
              values: {
                issued: longDate(invoice.issued_date),
                due: longDate(invoice.due_date)
              }
            })}
          </span>
        </div>

        <div class="v2-card" style="overflow:hidden;margin-bottom:18px">
          <table class="v2-table">
            <thead>
              <tr>
                <th>{$_('invoices.detail.col_item')}</th>
                <th class="v2-r">{$_('invoices.detail.col_qty')}</th>
                <th class="v2-r">{$_('invoices.detail.col_rate')}</th>
                <th class="v2-r">{$_('invoices.detail.col_tax')}</th>
                <th class="v2-r">{$_('invoices.detail.col_amount')}</th>
              </tr>
            </thead>
            <tbody>
              {#each lineItems as li (li.id)}
                <tr>
                  <td>
                    <div>{li.name}</div>
                    {#if li.detail}<div class="v2-table-secondary">{li.detail}</div>{/if}
                  </td>
                  <td class="v2-r v2-num">{li.quantity}</td>
                  <td class="v2-r v2-num">{money(li.rate, invoice.currency)}</td>
                  <td class="v2-r v2-num">{li.tax_rate}%</td>
                  <td class="v2-r v2-num">{money(li.amount, invoice.currency)}</td>
                </tr>
              {:else}
                <tr>
                  <td colspan="5" class="v2-sub" style="padding:14px 15px;font-size:12.5px">
                    {$_('invoices.detail.no_line_items')}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div style="display:flex;justify-content:flex-end">
          <dl class="v2-kv" style="grid-template-columns:160px 120px;width:280px">
            <dt>{$_('invoices.detail.subtotal')}</dt>
            <dd class="v2-num" style="text-align:right">
              {money(invoice.subtotal, invoice.currency)}
            </dd>
            {#if invoice.discount_amount > 0}
              <dt>{$_('invoices.detail.discount')}</dt>
              <dd class="v2-num" style="text-align:right">
                −{money(invoice.discount_amount, invoice.currency)}
              </dd>
            {/if}
            <dt>{$_('invoices.detail.tax')}</dt>
            <dd class="v2-num" style="text-align:right">
              {money(invoice.tax_amount, invoice.currency)}
            </dd>
            {#if invoice.shipping_amount > 0}
              <dt>{$_('invoices.detail.shipping')}</dt>
              <dd class="v2-num" style="text-align:right">
                {money(invoice.shipping_amount, invoice.currency)}
              </dd>
            {/if}
            <dt>{$_('invoices.detail.paid')}</dt>
            <dd class="v2-num" style="text-align:right">
              {money(invoice.amount_paid, invoice.currency)}
            </dd>
            <dt style="color:var(--v2-ink);font-weight:600">{$_('invoices.detail.outstanding')}</dt>
            <dd
              class="v2-num"
              style="text-align:right;font-weight:700;font-size:16px;color:{invoice.amount_due > 0
                ? 'var(--v2-rust)'
                : 'var(--v2-moss)'}"
            >
              {money(invoice.amount_due, invoice.currency)}
            </dd>
          </dl>
        </div>

        {#if !invoice.is_settled}
          <div style="display:flex;justify-content:flex-end;margin-top:18px">
            <form
              method="POST"
              action="?/markPaid"
              use:enhance={working}
              style="display:flex;gap:8px;align-items:flex-end"
            >
              <div>
                <label class="v2-label" for="amount" style="display:block;margin-bottom:4px">
                  {$_('invoices.detail.record_payment_label')}
                </label>
                <input
                  id="amount"
                  name="amount"
                  class="v2-input"
                  style="width:150px"
                  placeholder={money(invoice.amount_due, invoice.currency)}
                  inputmode="decimal"
                />
              </div>
              <button class="v2-btn v2-btn-primary" disabled={busy}
                >{$_('invoices.detail.record_button')}</button
              >
            </form>
          </div>
          <p class="v2-sub" style="text-align:right;font-size:11.5px;margin-top:6px">
            {$_('invoices.detail.record_hint', {
              values: { amount: money(invoice.amount_due, invoice.currency) }
            })}
          </p>
        {/if}
      </div>
    </div>
  </div>

  <aside class="v2-rail">
    <div class="v2-label v2-rail-head">{$_('invoices.detail.rail_invoice')}</div>
    <dl class="v2-kv">
      <dt>{$_('invoices.detail.rail_status')}</dt>
      <dd>
        <Pill tone={INVOICE_STATUS_TONE[invoice.status]}
          >{$_(invoiceStatusKey(invoice.status))}</Pill
        >
      </dd>
      <dt>{$_('invoices.detail.rail_number')}</dt>
      <dd class="v2-num">{invoice.invoice_number}</dd>
      <dt>{$_('invoices.detail.rail_issued')}</dt>
      <dd>{longDate(invoice.issued_date)}</dd>
      <dt>{$_('invoices.detail.rail_due')}</dt>
      <dd>{longDate(invoice.due_date)}</dd>
      <dt>{$_('invoices.detail.rail_terms')}</dt>
      <dd>{$_(paymentTermsKey(invoice.payment_terms))}</dd>
      <dt>{$_('invoices.detail.rail_currency')}</dt>
      <dd>{invoice.currency}</dd>
    </dl>

    <div class="v2-label v2-rail-head">{$_('invoices.detail.rail_bill_to')}</div>
    <a
      href={resolve(`/accounts/${invoice.account.id}`)}
      class="v2-sub"
      style="font-size:12.5px;line-height:1.65;text-decoration:none;display:block"
    >
      {invoice.account.name}
    </a>

    <div class="v2-label v2-rail-head">{$_('invoices.detail.rail_reminders')}</div>
    <dl class="v2-kv">
      <dt>{$_('invoices.detail.rail_automatic')}</dt>
      <dd>
        {invoice.reminder_enabled
          ? (invoice.reminder_frequency ?? $_('invoices.detail.reminders_on'))
          : $_('invoices.detail.reminders_off')}
      </dd>
      <dt>{$_('invoices.detail.rail_sent')}</dt>
      <dd class="v2-num">{invoice.reminder_count}</dd>
      {#if invoice.last_reminder_sent}
        <dt>{$_('invoices.detail.rail_last')}</dt>
        <dd>{relativeDays(invoice.last_reminder_sent)}</dd>
      {/if}
    </dl>
  </aside>
</div>
