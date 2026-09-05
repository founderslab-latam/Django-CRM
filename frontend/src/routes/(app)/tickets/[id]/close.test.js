import { describe, it, expect } from 'vitest';
import {
  findNode,
  openDescendants,
  subtreeTruncated,
  cascadeSummary,
  closeResultMessage,
  cascadedCount
} from './close.js';

/** @param {any} over */
function node(over = {}) {
  return {
    id: 'n',
    name: 'A ticket',
    status: 'New',
    is_active: true,
    children: [],
    ...over
  };
}

/**
 * A tree where the ticket being closed is itself a child, which is the shape
 * that broke the old dialog:
 *
 *   root (open)
 *   ├── sibling (open)
 *   └── focus (open)          <- the one being closed
 *       ├── kidOpen (open)
 *       └── kidClosed (Closed)
 *           └── grandchild (open)
 */
const TREE = node({
  id: 'root',
  name: 'Root',
  children: [
    node({ id: 'sibling', name: 'Sibling' }),
    node({
      id: 'focus',
      name: 'Focus',
      children: [
        node({ id: 'kidOpen', name: 'Kid open' }),
        node({
          id: 'kidClosed',
          name: 'Kid closed',
          status: 'Closed',
          children: [node({ id: 'grandchild', name: 'Grandchild' })]
        })
      ]
    })
  ]
});

describe('findNode', () => {
  it('finds the ticket being closed anywhere in the tree', () => {
    expect(findNode(TREE, 'grandchild')?.name).toBe('Grandchild');
  });

  it('is null for an id the tree does not carry', () => {
    expect(findNode(TREE, 'nope')).toBeNull();
    expect(findNode(null, 'focus')).toBeNull();
  });
});

describe('openDescendants', () => {
  it("is the focus ticket's own subtree, never its relatives", () => {
    // The bug in the version this replaces: it walked from `root` and
    // collected every open node but the focus, so a ticket that is itself a
    // child listed its parent and siblings as about to be closed.
    const ids = openDescendants(TREE, 'focus').map((d) => d.id);
    expect(ids).not.toContain('root');
    expect(ids).not.toContain('sibling');
  });

  it('recurses through a closed child to reach an open grandchild', () => {
    // `_open_descendants` skips a closed node but still walks into it, so the
    // grandchild does close. Listing only direct children would understate it.
    expect(openDescendants(TREE, 'focus').map((d) => d.id)).toEqual(['kidOpen', 'grandchild']);
  });

  it('leaves closed tickets out, because closing them changes nothing', () => {
    expect(openDescendants(TREE, 'focus').map((d) => d.id)).not.toContain('kidClosed');
  });

  it('leaves an inactive ticket out, matching the backend', () => {
    // An inactive row is a merged duplicate; the backend's `is_active` check
    // skips it.
    const tree = node({
      id: 'p',
      children: [node({ id: 'merged', is_active: false }), node({ id: 'real' })]
    });
    expect(openDescendants(tree, 'p').map((d) => d.id)).toEqual(['real']);
  });

  it('is empty for a leaf, and for a ticket not in the tree', () => {
    expect(openDescendants(TREE, 'kidOpen')).toEqual([]);
    expect(openDescendants(TREE, 'nope')).toEqual([]);
  });
});

describe('subtreeTruncated', () => {
  it('is true when the API stopped at its depth cap inside the subtree', () => {
    const tree = node({
      id: 'p',
      children: [node({ id: 'deep', truncated: true })]
    });
    expect(subtreeTruncated(tree, 'p')).toBe(true);
  });

  it('ignores a cap reached outside the subtree being closed', () => {
    const tree = node({
      id: 'root',
      children: [node({ id: 'elsewhere', truncated: true }), node({ id: 'focus' })]
    });
    expect(subtreeTruncated(tree, 'focus')).toBe(false);
  });

  it('is false for an ordinary tree', () => {
    expect(subtreeTruncated(TREE, 'focus')).toBe(false);
  });
});

describe('cascadeSummary', () => {
  // These functions now return an i18n descriptor `{ key, values? }` instead of
  // a finished English string; the copy itself lives in the `cases.detail.*`
  // catalog and is rendered by the caller. The branching and the plural
  // `count` argument are still this module's job, so that is what is asserted.
  it('says nothing else changes when nothing linked is open', () => {
    expect(cascadeSummary({ count: 0 })).toEqual({ key: 'cases.detail.cascade_summary_none' });
  });

  it('counts and passes the number through for the plural to resolve', () => {
    expect(cascadeSummary({ count: 1 })).toEqual({
      key: 'cases.detail.cascade_summary_some',
      values: { count: 1 }
    });
    expect(cascadeSummary({ count: 3 })).toEqual({
      key: 'cases.detail.cascade_summary_some',
      values: { count: 3 }
    });
  });

  it('admits the list is a floor when the tree was cut short', () => {
    // The close has no depth cap even though the tree endpoint does, so more
    // can close than the confirm step is able to name.
    expect(cascadeSummary({ count: 2, truncated: true })).toEqual({
      key: 'cases.detail.cascade_summary_some_truncated',
      values: { count: 2 }
    });
    expect(cascadeSummary({ count: 2 }).key).toBe('cases.detail.cascade_summary_some');
  });
});

describe('closeResultMessage', () => {
  it('reports what the server closed, not what was asked for', () => {
    expect(closeResultMessage({ cascade: true, cascaded: 2 })).toEqual({
      key: 'cases.detail.close_result_cascaded',
      values: { count: 2 }
    });
    expect(closeResultMessage({ cascade: true, cascaded: 1 })).toEqual({
      key: 'cases.detail.close_result_cascaded',
      values: { count: 1 }
    });
  });

  it('says nothing else changed when the cascade closed nothing', () => {
    expect(closeResultMessage({ cascade: true, cascaded: 0 })).toEqual({
      key: 'cases.detail.close_result_none'
    });
  });

  it('claims no cascade when the box was unticked', () => {
    expect(closeResultMessage({ cascade: false, cascaded: 0 })).toEqual({
      key: 'cases.detail.close_result_simple'
    });
  });
});

describe('cascadedCount', () => {
  it('counts the ids the endpoint returned', () => {
    expect(cascadedCount({ cascaded_case_ids: ['a', 'b'] })).toBe(2);
  });

  it('a body without the key means none, not unknown', () => {
    expect(cascadedCount({})).toBe(0);
    expect(cascadedCount(null)).toBe(0);
  });
});
