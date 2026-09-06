/**
 * Chilean RUT (Rol Único Tributario) helpers.
 *
 * A straight port of `validate_rut` / `normalize_rut` / `rut_check_digit` /
 * `format_rut` in `backend/common/validators.py`, so an inline form check and
 * the serializer never disagree about what is valid. The serializer is still
 * the rule; this only spares a round-trip and lets a field show its own error.
 */

/** Strip dots, dash and spaces; upper-case the check digit. `""` stays `""`. */
export function normalizeRut(raw) {
  if (!raw) return '';
  return String(raw)
    .replace(/[^0-9kK]/g, '')
    .toUpperCase();
}

/**
 * The modulo-11 check digit ("DV") for a RUT body (the digits without it).
 * Weights cycle 2..7 from the rightmost digit; remainder 11 is `0`, 10 is `K`.
 */
export function rutCheckDigit(body) {
  let sum = 0;
  for (let i = 0; i < body.length; i++) {
    sum += Number(body[body.length - 1 - i]) * ((i % 6) + 2);
  }
  const remainder = 11 - (sum % 11);
  if (remainder === 11) return '0';
  if (remainder === 10) return 'K';
  return String(remainder);
}

/** Canonical presentation form, `"12.345.678-5"`. Assumes `value` is a valid RUT. */
export function formatRut(value) {
  const cleaned = normalizeRut(value);
  const body = cleaned.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${body}-${cleaned.slice(-1)}`;
}

/** True when `value` is shaped like a RUT and its check digit matches. */
export function isValidRut(value) {
  const cleaned = normalizeRut(value);
  if (!/^\d{7,8}[0-9K]$/.test(cleaned)) return false;
  return rutCheckDigit(cleaned.slice(0, -1)) === cleaned.slice(-1);
}
