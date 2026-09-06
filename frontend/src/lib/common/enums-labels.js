/**
 * Translates the raw values behind `ROLE_LABEL` and `AGING_LABEL`
 * (`$lib/v2/enums.js`) into i18n catalog keys, without editing that shared
 * file — `enums.js` is mirrored 1:1 from the Django models on purpose.
 *
 * `ROLE_LABEL` labels `common.Profile.role` (`ADMIN` | `USER`); `AGING_LABEL`
 * labels `Opportunity.get_aging_status()` (`green` | `yellow` | `red`). Both
 * values are server-derived and never posted back from the call sites that
 * render them, so only the display label is translated. A value with no
 * mapping falls through to itself.
 *
 * Catalog keys live under `common.enums.role.*` / `common.enums.aging.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 *
 * Note: `AGING_LABEL`'s "On pace" is deliberately left untranslated inside the
 * sentence at `opportunity.edit.stage_change_outro` (and its paired
 * `stage_change_days` pill), so it matches that copy. Only the standalone
 * aging badges/pills route through `agingKey`.
 */

/** @type {Record<string, string>} */
const ROLE_KEYS = { ADMIN: 'admin', USER: 'user' };

/** @type {Record<string, string>} */
const AGING_KEYS = { green: 'green', yellow: 'yellow', red: 'red' };

/** @param {string} raw */
export function roleKey(raw) {
  return `common.enums.role.${ROLE_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function agingKey(raw) {
  return `common.enums.aging.${AGING_KEYS[raw] ?? raw}`;
}
