/**
 * Closing a parent ticket, and what goes with it.
 *
 * `POST /cases/<id>/close-with-children/` closes the ticket and, when
 * `cascade` is true, every OPEN DESCENDANT of it. This module works out which
 * tickets those are, so the confirm step can name them before anything is
 * closed.
 *
 * **The tree endpoint does not return the ticket you are closing.** `GET
 * /cases/<id>/tree/` walks UP to the highest ancestor in the org and returns
 * that as `root`, with `focus_id` naming the ticket you asked about. So the
 * subtree that will actually be closed has to be found inside the response
 * first. A previous version of this feature (`CloseWithChildrenDialog.svelte`,
 * written, never wired to a button, deleted with this change) walked from
 * `root` and collected every open node except the focus. For a ticket that is
 * itself a child that listed its parent, its siblings and its cousins as
 * about to be closed, and none of them would have been. Overstating the blast
 * radius of a destructive action is worse than saying nothing.
 *
 * [openDescendants] mirrors `_open_descendants` in `cases/parent_views.py`
 * exactly, including the two things that are easy to get wrong:
 *
 * - a node counts only when it is open AND active, and
 * - recursion goes through closed nodes anyway, so an open grandchild under a
 *   closed child is still cascaded.
 */

/** A ticket closes to any status but this one. */
const CLOSED = 'Closed';

/**
 * The node for `id` inside the tree, or null.
 *
 * @param {any} root
 * @param {string} id
 */
export function findNode(root, id) {
  if (!root || !id) return null;
  if (root.id === id) return root;
  for (const child of root.children ?? []) {
    const hit = findNode(child, id);
    if (hit) return hit;
  }
  return null;
}

/**
 * The tickets a cascading close would actually close.
 *
 * @param {any} root the tree response's `root`
 * @param {string} id the ticket being closed
 * @returns {Array<{id: string, name: string, status: string}>}
 */
export function openDescendants(root, id) {
  const focus = findNode(root, id);
  if (!focus) return [];

  /** @type {Array<{id: string, name: string, status: string}>} */
  const out = [];
  /** @param {any} node */
  const walk = (node) => {
    for (const child of node.children ?? []) {
      // Open AND active, matching `_open_descendants`. An inactive row is a
      // merged duplicate and the backend skips it.
      if (child.status !== CLOSED && child.is_active !== false) {
        out.push({ id: child.id, name: child.name, status: child.status });
      }
      // Through closed children regardless: an open grandchild under a closed
      // child still cascades.
      walk(child);
    }
  };
  walk(focus);
  return out;
}

/**
 * True when the subtree hit the API's depth cap, so the list above is a floor
 * rather than the whole set.
 *
 * `_build_tree` stops at `Case.PARENT_MAX_DEPTH` and marks the node
 * `truncated`. The close itself has no such cap, so in that case more tickets
 * close than the confirm step can name, and it says so instead of implying a
 * complete list.
 *
 * @param {any} root
 * @param {string} id
 */
export function subtreeTruncated(root, id) {
  const focus = findNode(root, id);
  if (!focus) return false;
  /** @param {any} node @returns {boolean} */
  const walk = (node) =>
    Boolean(node.truncated) || (node.children ?? []).some((/** @type {any} */ c) => walk(c));
  return walk(focus);
}

/**
 * The line above the checkbox: what happens if it stays ticked.
 *
 * Returns an i18n descriptor `{ key, values? }` rather than a finished string,
 * so the plural/branching logic stays here and tested while the actual copy
 * lives in the `cases.detail.*` catalog. The caller renders it with svelte-i18n
 * (`$_(key, { values })`). Keeping svelte-i18n out of this module is deliberate:
 * `close.test.js` runs under the bare vitest config that resolves neither the
 * i18n runtime nor its catalogs.
 *
 * @param {{ count: number, truncated?: boolean }} args
 * @returns {{ key: string, values?: { count: number } }}
 */
export function cascadeSummary({ count, truncated = false }) {
  if (count === 0) {
    return { key: 'cases.detail.cascade_summary_none' };
  }
  return {
    key: truncated
      ? 'cases.detail.cascade_summary_some_truncated'
      : 'cases.detail.cascade_summary_some',
    values: { count }
  };
}

/**
 * What actually happened, from the response rather than from what was asked.
 *
 * The server returns `cascaded_case_ids`, the tickets it really closed. A
 * message built from the count on screen would claim a cascade that a
 * concurrent close had already made a no-op.
 *
 * Returns an i18n descriptor `{ key, values? }`; see `cascadeSummary` above.
 *
 * @param {{ cascade: boolean, cascaded: number }} args
 * @returns {{ key: string, values?: { count: number } }}
 */
export function closeResultMessage({ cascade, cascaded }) {
  if (!cascade) return { key: 'cases.detail.close_result_simple' };
  if (cascaded === 0) {
    return { key: 'cases.detail.close_result_none' };
  }
  return { key: 'cases.detail.close_result_cascaded', values: { count: cascaded } };
}

/**
 * How many tickets the response says were closed alongside.
 *
 * @param {any} body
 */
export function cascadedCount(body) {
  return (body?.cascaded_case_ids ?? []).length;
}
