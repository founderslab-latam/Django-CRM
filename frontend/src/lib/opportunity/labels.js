/**
 * Translates the raw Opportunity stage values behind `STAGE_LABEL`
 * (`$lib/v2/enums.js`) into i18n catalog keys, without editing that shared
 * file — `enums.js` is imported by every module and its maps are mirrored 1:1
 * from the Django model on purpose.
 *
 * The raw value is what the API sends and what the form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Currently consumed only by the `pipeline` filter descriptor in
 * `$lib/v2/filters.js`; the pipeline screens still read `STAGE_LABEL`
 * directly (outside the scope of the shared-component i18n stage).
 *
 * Catalog keys live under `opportunity.enums.stage.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const STAGE_KEYS = {
  PROSPECTING: 'prospecting',
  QUALIFICATION: 'qualification',
  PROPOSAL: 'proposal',
  NEGOTIATION: 'negotiation',
  CLOSED_WON: 'closed_won',
  CLOSED_LOST: 'closed_lost'
};

/** @param {string} raw */
export function opportunityStageKey(raw) {
  return `opportunity.enums.stage.${STAGE_KEYS[raw] ?? raw}`;
}
