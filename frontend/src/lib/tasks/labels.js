/**
 * Translates the raw Task enum values behind `TASK_STATUS` / `TASK_PRIORITY`
 * and the board's `BOARD_PRIORITY_LABEL` (`$lib/v2/enums.js`) into i18n catalog
 * keys, without editing that shared file — `enums.js` is imported by every
 * module, not just Tasks, and its maps are mirrored 1:1 from the Django models
 * on purpose (a Task priority is Low/Medium/High, a board card's is
 * low/medium/high/urgent — three different enums for one word, kept apart).
 *
 * The raw value is what the API sends and what the form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `tasks.enums.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

/** @type {Record<string, string>} */
const PRIORITY_KEYS = {
  Low: 'low',
  Medium: 'medium',
  High: 'high'
};

/** @type {Record<string, string>} */
const STATUS_KEYS = {
  New: 'new',
  'In Progress': 'in_progress',
  Completed: 'completed'
};

/** @type {Record<string, string>} */
const BOARD_PRIORITY_KEYS = {
  low: 'low',
  medium: 'medium',
  high: 'high',
  urgent: 'urgent'
};

/** @param {string} raw */
export function taskPriorityKey(raw) {
  return `tasks.enums.priority.${PRIORITY_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function taskStatusKey(raw) {
  return `tasks.enums.status.${STATUS_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function boardPriorityKey(raw) {
  return `tasks.enums.board_priority.${BOARD_PRIORITY_KEYS[raw] ?? raw}`;
}
