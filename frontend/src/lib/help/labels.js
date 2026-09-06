/**
 * Translates the `SUPPORT_CATEGORIES` values behind `$lib/server/v2/support.js`
 * into i18n catalog keys, without editing that shared module — its constant is
 * mirrored from the enterprise `platform_support` API's category choices, and
 * its `.value` is what the create form posts and the server validates.
 *
 * Only the label a person reads is translated here; the raw `.value` is never
 * rewritten. A value with no mapping falls through to itself, so a category the
 * backend grows still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `help.new.category_option.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const CATEGORY_KEYS = {
  technical: 'technical',
  billing: 'billing',
  account: 'account',
  feature_request: 'feature_request',
  other: 'other'
};

/** @param {string} value */
export function supportCategoryKey(value) {
  return `help.new.category_option.${CATEGORY_KEYS[value] ?? value}`;
}
