/**
 * Translates the raw Solution enum values behind `SOLUTION_STATUS` /
 * `SOLUTION_STATUS_LABEL` (`$lib/v2/enums.js`) into i18n catalog keys, without
 * editing that shared file — `enums.js` is imported by every module, not just
 * the knowledge base, and its maps are mirrored 1:1 from
 * `cases.Solution.STATUS_CHOICES` on purpose.
 *
 * The raw value is what the API sends and what the form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `solutions.enums.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const STATUS_KEYS = {
  draft: 'draft',
  reviewed: 'reviewed',
  approved: 'approved'
};

/** @param {string} raw */
export function solutionStatusKey(raw) {
  return `solutions.enums.status.${STATUS_KEYS[raw] ?? raw}`;
}
