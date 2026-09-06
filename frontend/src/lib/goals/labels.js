/**
 * Translates the raw SalesGoal enum values behind `GOAL_TYPE_LABEL`,
 * `PERIOD_TYPE_LABEL` and `GOAL_STATUS_LABEL` (`$lib/v2/enums.js`) into i18n
 * catalog keys, without editing that shared file — `enums.js` is imported by
 * every module, not just Goals, and its maps are mirrored 1:1 from the Django
 * models (GOAL_TYPES / PERIOD_TYPES in common/utils.py and the four
 * SalesGoal.status pace judgements) on purpose.
 *
 * The raw value is what the API sends and what the form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `goals.enums.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const TYPE_KEYS = {
  REVENUE: 'revenue',
  DEALS_CLOSED: 'deals_closed',
  ACTIVITIES: 'activities'
};

/** @type {Record<string, string>} */
const PERIOD_KEYS = {
  MONTHLY: 'monthly',
  QUARTERLY: 'quarterly',
  YEARLY: 'yearly',
  CUSTOM: 'custom'
};

/** @type {Record<string, string>} */
const STATUS_KEYS = {
  completed: 'completed',
  on_track: 'on_track',
  at_risk: 'at_risk',
  behind: 'behind'
};

/** @param {string} raw */
export function goalTypeKey(raw) {
  return `goals.enums.type.${TYPE_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function periodTypeKey(raw) {
  return `goals.enums.period.${PERIOD_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function goalStatusKey(raw) {
  return `goals.enums.status.${STATUS_KEYS[raw] ?? raw}`;
}
