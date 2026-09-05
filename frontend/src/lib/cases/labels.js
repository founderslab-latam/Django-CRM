/**
 * Translates the raw Case enum values behind `PRIORITY_TONE`,
 * `CASE_STATUS_TONE`, `CASE_PRIORITIES`, `CASE_TYPES` and `APPROVAL_STATE_LABEL`
 * (`$lib/v2/enums.js`) into i18n catalog keys, without editing that shared
 * file — `enums.js` is imported by every module, not just Cases, and its maps
 * are mirrored 1:1 from the Django models on purpose.
 *
 * The raw value is what the API sends and what the form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `cases.enums.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const PRIORITY_KEYS = {
  Low: 'low',
  Normal: 'normal',
  High: 'high',
  Urgent: 'urgent'
};

/** @type {Record<string, string>} */
const STATUS_KEYS = {
  New: 'new',
  Assigned: 'assigned',
  Pending: 'pending',
  Closed: 'closed',
  Rejected: 'rejected',
  Duplicate: 'duplicate'
};

/** @type {Record<string, string>} */
const TYPE_KEYS = {
  Question: 'question',
  Incident: 'incident',
  Problem: 'problem'
};

/** @type {Record<string, string>} */
const APPROVAL_STATE_KEYS = {
  pending: 'pending',
  approved: 'approved',
  rejected: 'rejected',
  cancelled: 'cancelled'
};

/** @param {string} raw */
export function casePriorityKey(raw) {
  return `cases.enums.priority.${PRIORITY_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function caseStatusKey(raw) {
  return `cases.enums.status.${STATUS_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function caseTypeKey(raw) {
  return `cases.enums.type.${TYPE_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function approvalStateKey(raw) {
  return `cases.enums.approval_state.${APPROVAL_STATE_KEYS[raw] ?? raw}`;
}
