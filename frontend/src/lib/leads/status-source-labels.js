/**
 * Translates the raw values behind `LEAD_STATUS_LABEL` / `LEAD_SOURCE_LABEL`
 * (`$lib/v2/enums.js`) into i18n catalog keys, without editing that shared
 * file — `enums.js` is imported by every module, not just Leads, and its own
 * comment explains why the raw values (spaces, the "compaign" misspelling
 * included) can't change: they're what the database column actually stores.
 *
 * Catalog keys live under `leads.enums.status.*` / `leads.enums.source.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`). `compaign` maps to the
 * correctly-spelled key `campaign` — only the display label is corrected,
 * the value written back to the form (and the database) is untouched.
 */

/** @type {Record<string, string>} */
const STATUS_KEYS = {
  assigned: 'assigned',
  'in process': 'in_process',
  converted: 'converted',
  recycled: 'recycled',
  closed: 'closed'
};

/** @type {Record<string, string>} */
const SOURCE_KEYS = {
  call: 'call',
  email: 'email',
  'existing customer': 'existing_customer',
  partner: 'partner',
  'public relations': 'public_relations',
  compaign: 'campaign',
  other: 'other'
};

/** @param {string} raw */
export function leadStatusKey(raw) {
  return `leads.enums.status.${STATUS_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function leadSourceKey(raw) {
  return `leads.enums.source.${SOURCE_KEYS[raw] ?? raw}`;
}
