/** Formatting helpers for v2. Every number rendered goes through one of these. */

import { get } from 'svelte/store';

import { locale } from '$lib/i18n/index.js';

/**
 * The active locale, as a plain BCP-47 string these helpers can hand to
 * `Intl`. Read at call time (never at import time) so it tracks the value
 * `hooks.server.js` sets per request and the client store after that. When
 * i18n has not been initialised at all — the unit tests, a bare script —
 * `get(locale)` is `null`/`undefined` and every function below falls back to
 * exactly the English formatting it used before this file learned about
 * locales.
 *
 * Dates use `en-GB` for English (day before month, "8 Aug"), which is the
 * order this app has always rendered; only the language switches, not the
 * field order.
 */
function activeLocale() {
  const l = get(locale);
  return typeof l === 'string' && l.length ? l : null;
}

/** @returns {string} a locale tag for date/relative formatting */
function dateLocale() {
  const l = activeLocale();
  return l && l.startsWith('es') ? 'es' : 'en-GB';
}

/** @returns {string} a locale tag for plain number grouping */
function numberLocale() {
  const l = activeLocale();
  return l && l.startsWith('es') ? 'es' : 'en-US';
}

/**
 * @param {number|string|null|undefined} n
 *
 * Currency formatting stays pinned to `en-US` on purpose for now: switching
 * the locale here moves the currency symbol and the grouping/decimal marks
 * ("1.234,50 US$"), which is a larger visual change than the rest of this
 * file and wants its own decision. Tracked in the i18n plan's
 * shared-component notes.
 */
export function money(n, currency = 'USD') {
  const v = Number(n ?? 0);
  if (!Number.isFinite(v)) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: v % 1 === 0 ? 0 : 2
  }).format(v);
}

/** @param {number|string|null|undefined} n */
export function count(n) {
  const v = Number(n ?? 0);
  return Number.isFinite(v) ? v.toLocaleString(numberLocale()) : '—';
}

/** @param {string|null|undefined} name */
export function initials(name) {
  return String(name ?? '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase();
}

/**
 * ISO string → Date, or null when there is nothing to render.
 *
 * A date-only string ("2026-08-07") names a calendar day, not an instant, and
 * `new Date()` reads it as UTC midnight. A browser west of UTC then prints
 * that as the day before: a due date set for Friday reads as Thursday, and a
 * chart bucket the API labelled Friday sits under the wrong label. Appending a
 * time is what makes it parse as local midnight instead. Anything that carries
 * a time of day is a real instant and is left exactly as it was.
 */
function parseIso(value) {
  if (!value) return null;
  const d =
    typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? new Date(`${value}T00:00:00`)
      : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * ISO date → "8 Aug", or "8 Aug 2023" when it is not this year, otherwise a
 * deal closed three years ago reads as if it closed last week.
 * Returns an em dash for null so table cells never collapse.
 */
export function shortDate(iso, now = new Date()) {
  const d = parseIso(iso);
  if (!d) return '—';
  const sameYear = d.getFullYear() === now.getFullYear();
  return new Intl.DateTimeFormat(dateLocale(), {
    day: 'numeric',
    month: 'short',
    ...(sameYear ? {} : { year: 'numeric' })
  }).format(d);
}

/** ISO date → "8 August 2026". */
export function longDate(iso) {
  const d = parseIso(iso);
  if (!d) return '—';
  return new Intl.DateTimeFormat(dateLocale(), {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  }).format(d);
}

/** Whole days between an ISO date and today. Negative = in the future. */
export function daysSince(iso, now = new Date()) {
  const d = parseIso(iso);
  if (!d) return null;
  return Math.floor((now.getTime() - d.getTime()) / 86400000);
}

/**
 * "12 days ago" / "today" / "in 4 days", for a person, not a machine.
 *
 * `Intl.RelativeTimeFormat` with `numeric: 'auto'` gives exactly the English
 * this used to hand-roll ("today", "yesterday", "N days ago", "tomorrow",
 * "in N days") and the natural Spanish equivalent, plurals included, for free.
 */
export function relativeDays(iso, now = new Date()) {
  const n = daysSince(iso, now);
  if (n === null) return '—';
  return new Intl.RelativeTimeFormat(dateLocale(), { numeric: 'auto' }).format(-n, 'day');
}

/**
 * "just now" / "18 minutes ago" / "3 hours ago", then whole days.
 *
 * `relativeDays` is right for records, a lead touched at 09:00 and one
 * touched at 17:00 are both "today" and the difference does not change what
 * you do. A feed is the opposite: a mention from five minutes ago and one from
 * twenty hours ago are different events, and collapsing both to "today" is how
 * you end up re-reading the whole list to find what is new.
 */
export function relativeTime(iso, now = new Date()) {
  const d = parseIso(iso);
  if (!d) return '—';
  const mins = Math.floor((now.getTime() - d.getTime()) / 60000);
  if (mins < 0) return relativeDays(iso, now);
  // `Intl.RelativeTimeFormat` has no "just now"; its zero case is "this
  // minute" / "este minuto", which reads wrong in a feed. The two literals
  // are the only text this file states directly.
  if (mins < 1) return dateLocale() === 'es' ? 'ahora mismo' : 'just now';
  const rtf = new Intl.RelativeTimeFormat(dateLocale(), { numeric: 'always' });
  if (mins < 60) return rtf.format(-mins, 'minute');
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return rtf.format(-hrs, 'hour');
  return relativeDays(iso, now);
}

/**
 * A duration in minutes as "1h 48m".
 *
 * Logged time is read in hours: "108m" makes the reader do the division, and
 * two of them on the same screen makes them do it twice. Minutes below the
 * hour keep their own suffix so a short entry does not render as "0h 12m".
 * The h/m/d marks are unit symbols, not words, so they do not translate.
 *
 * @param {number|string|null|undefined} mins
 */
export function hoursMinutes(mins) {
  const v = Number(mins ?? 0);
  if (!Number.isFinite(v)) return '0m';
  const m = Math.max(0, Math.round(v));
  const h = Math.floor(m / 60);
  return h ? `${h}h ${m % 60}m` : `${m}m`;
}

/** Compact age for a table cell: "12d", "3h". Unit symbols, not words. */
export function shortAge(iso, now = new Date()) {
  const d = parseIso(iso);
  if (!d) return '—';
  const mins = Math.max(0, Math.floor((now.getTime() - d.getTime()) / 60000));
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}
