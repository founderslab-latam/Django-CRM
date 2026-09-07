/**
 * Industry labels for the account forms.
 *
 * The backend sends industry as a raw ALL-CAPS string (`INDCHOICES` in
 * `common/utils.py`, where value === label), so the `<select>` showed English
 * even in a Spanish session. This maps a raw value to its catalog key without
 * editing `$lib/v2/enums.js`, per docs/contributing/internationalization.md.
 * A value with no catalog entry (e.g. a new one added server-side) falls back
 * to the raw string rather than rendering the key.
 *
 * @param {string} value  the stored industry value
 * @param {(key: string) => string} t  the `$_` translation function
 * @returns {string}
 */
export function industryLabel(value, t) {
  if (!value) return '';
  const slug = String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  const key = `accounts.enums.industry.${slug}`;
  const label = t(key);
  return label === key ? value : label;
}
