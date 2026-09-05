/**
 * Translates the raw Invoice enum values behind `INVOICE_STATUS_TONE`,
 * `invoiceStatusLabel`, `INVOICE_STATUSES`, `ESTIMATE_STATUS_TONE`,
 * `ESTIMATE_STATUSES`, `PAYMENT_TERMS_LABEL` and `RECURRING_FREQUENCY_LABEL`
 * (`$lib/v2/enums.js`) into i18n catalog keys, without editing that shared
 * file — `enums.js` is imported by every module, not just Invoices, and its
 * maps are mirrored 1:1 from the Django models on purpose.
 *
 * The raw value is what the API sends and what the form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `invoices.enums.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const STATUS_KEYS = {
  Draft: 'draft',
  Sent: 'sent',
  Viewed: 'viewed',
  Paid: 'paid',
  Partially_Paid: 'partially_paid',
  Overdue: 'overdue',
  Pending: 'pending',
  Cancelled: 'cancelled'
};

/** @type {Record<string, string>} */
const ESTIMATE_STATUS_KEYS = {
  Draft: 'draft',
  Sent: 'sent',
  Viewed: 'viewed',
  Accepted: 'accepted',
  Declined: 'declined',
  Expired: 'expired'
};

/** @type {Record<string, string>} */
const PAYMENT_TERMS_KEYS = {
  DUE_ON_RECEIPT: 'due_on_receipt',
  NET_15: 'net_15',
  NET_30: 'net_30',
  NET_45: 'net_45',
  NET_60: 'net_60',
  CUSTOM: 'custom'
};

/** @type {Record<string, string>} */
const FREQUENCY_KEYS = {
  WEEKLY: 'weekly',
  BIWEEKLY: 'biweekly',
  MONTHLY: 'monthly',
  QUARTERLY: 'quarterly',
  SEMI_ANNUALLY: 'semi_annually',
  YEARLY: 'yearly',
  CUSTOM: 'custom'
};

/** @param {string} raw */
export function invoiceStatusKey(raw) {
  return `invoices.enums.status.${STATUS_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function estimateStatusKey(raw) {
  return `invoices.enums.estimate_status.${ESTIMATE_STATUS_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function paymentTermsKey(raw) {
  return `invoices.enums.payment_terms.${PAYMENT_TERMS_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function recurringFrequencyKey(raw) {
  return `invoices.enums.frequency.${FREQUENCY_KEYS[raw] ?? raw}`;
}
