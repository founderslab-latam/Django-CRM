/**
 * The party tax ID is called different things by country. Chile's is the RUT
 * and it has a checkable format; everywhere else the generic label stands and
 * the field is free text. Only the label and the hint change here -- never the
 * field name or the value stored.
 *
 * Callers pass their component's `$_` translation function as `t`, since these
 * run outside a component where the store auto-subscription is not available.
 */

/** The `<label>` text for a tax-id field on a record in `country`. */
export function taxIdLabel(country, t) {
  return country === 'CL' ? t('common.tax_id.cl_label') : t('common.tax_id.generic_label');
}

/** The hint under the field, or `''` when there is nothing country-specific to say. */
export function taxIdHint(country, t) {
  return country === 'CL' ? t('common.tax_id.cl_hint') : '';
}
