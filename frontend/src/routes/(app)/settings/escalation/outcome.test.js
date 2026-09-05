import { describe, it, expect } from 'vitest';
import {
  actionNotifies,
  teamSaysSo,
  halfFires,
  escalationOutcome,
  teamIgnoredNote,
  deadPolicyCount,
  breachesGoingNowhere,
  unconfiguredPriorities,
  joinWithAnd
} from './outcome.js';

const ALICE = { id: 'p1', name: 'Alice' };
const SUPPORT = { id: 't1', name: 'Support' };
const SUPPORT_TEAM = { id: 't2', name: 'Support Team' };

/** @param {any} over */
function policy(over = {}) {
  return {
    id: 'e1',
    priority: 'Urgent',
    is_active: true,
    first_response_action: 'notify',
    resolution_action: 'notify',
    first_response_target: ALICE,
    resolution_target: ALICE,
    notify_team: null,
    breaches_last_30d: { first_response: 0, resolution: 0 },
    ...over
  };
}

describe('actionNotifies', () => {
  it('is true for the two actions that build a recipient list', () => {
    expect(actionNotifies('notify')).toBe(true);
    expect(actionNotifies('notify_and_reassign')).toBe(true);
  });

  it('is false for reassign, which sends no mail at all', () => {
    expect(actionNotifies('reassign')).toBe(false);
  });
});

describe('halfFires', () => {
  it('is false for every half of an inactive policy', () => {
    const p = policy({ is_active: false });
    expect(halfFires(p, 'first_response')).toBe(false);
    expect(halfFires(p, 'resolution')).toBe(false);
  });

  // The three cases the inline version got wrong, one test each.
  it('is false for notify with a team but no target', () => {
    const p = policy({ first_response_target: null, notify_team: SUPPORT });
    expect(halfFires(p, 'first_response')).toBe(false);
  });

  it('is false for notify_and_reassign with no target and no team', () => {
    const p = policy({ first_response_action: 'notify_and_reassign', first_response_target: null });
    expect(halfFires(p, 'first_response')).toBe(false);
  });

  it('is false for notify_and_reassign with a team but no target', () => {
    const p = policy({
      first_response_action: 'notify_and_reassign',
      first_response_target: null,
      notify_team: SUPPORT
    });
    expect(halfFires(p, 'first_response')).toBe(false);
  });

  it('is false for reassign with no target', () => {
    const p = policy({ first_response_action: 'reassign', first_response_target: null });
    expect(halfFires(p, 'first_response')).toBe(false);
  });

  it('is true whenever an active policy has a target on that half', () => {
    for (const action of ['notify', 'reassign', 'notify_and_reassign']) {
      expect(halfFires(policy({ first_response_action: action }), 'first_response')).toBe(true);
    }
  });

  it('reads the half it was asked about, not the other one', () => {
    const p = policy({ first_response_target: null });
    expect(halfFires(p, 'first_response')).toBe(false);
    expect(halfFires(p, 'resolution')).toBe(true);
  });
});

// `escalationOutcome` and `teamIgnoredNote` return structured descriptors now
// rather than English; the page composes the sentence with `$_`. Same move as
// `tickets/[id]/close.js`.
describe('escalationOutcome', () => {
  it('names the policy being off before anything else', () => {
    const p = policy({ is_active: false, notify_team: SUPPORT });
    expect(escalationOutcome(p, 'first_response')).toEqual({ kind: 'off', dead: true });
  });

  it('says nothing happens when no target is set', () => {
    const p = policy({ first_response_target: null });
    expect(escalationOutcome(p, 'first_response')).toEqual({ kind: 'no_target', dead: true });
  });

  it('carries the team when one is set with no target, which is the trap', () => {
    const p = policy({ first_response_target: null, notify_team: SUPPORT });
    expect(escalationOutcome(p, 'first_response')).toEqual({
      kind: 'no_target_team',
      team: SUPPORT,
      dead: true
    });
  });

  it('carries the team on a notifying half', () => {
    const p = policy({ notify_team: SUPPORT });
    expect(escalationOutcome(p, 'first_response')).toEqual({
      kind: 'fires',
      action: 'notify',
      targetName: 'Alice',
      team: SUPPORT,
      dead: false
    });
  });

  it('still carries a team named Support Team; the page dedups the word', () => {
    const p = policy({ notify_team: SUPPORT_TEAM });
    expect(/** @type {any} */ (escalationOutcome(p, 'first_response')).team).toBe(SUPPORT_TEAM);
  });

  it('drops the team from a reassign half, which never emails', () => {
    const p = policy({ first_response_action: 'reassign', notify_team: SUPPORT });
    expect(escalationOutcome(p, 'first_response')).toEqual({
      kind: 'fires',
      action: 'reassign',
      targetName: 'Alice',
      team: null,
      dead: false
    });
  });

  it('always carries a target name on a firing half', () => {
    for (const action of ['notify', 'reassign', 'notify_and_reassign']) {
      for (const team of [null, SUPPORT]) {
        const p = policy({ first_response_action: action, notify_team: team });
        const out = /** @type {any} */ (escalationOutcome(p, 'first_response'));
        expect(out.kind).toBe('fires');
        expect(out.targetName).toBe('Alice');
      }
    }
  });
});

describe('teamIgnoredNote', () => {
  it('flags the team set on a reassign half', () => {
    const p = policy({ first_response_action: 'reassign', notify_team: SUPPORT });
    expect(teamIgnoredNote(p, 'first_response')).toEqual({ team: SUPPORT });
  });

  it('is null when the half notifies', () => {
    const p = policy({ first_response_action: 'notify_and_reassign', notify_team: SUPPORT });
    expect(teamIgnoredNote(p, 'first_response')).toBeNull();
  });

  it('is null with no team', () => {
    expect(
      teamIgnoredNote(policy({ first_response_action: 'reassign' }), 'first_response')
    ).toBeNull();
  });

  it('is null on a half that does not fire, where the outcome line already says so', () => {
    const p = policy({
      first_response_action: 'reassign',
      first_response_target: null,
      notify_team: SUPPORT
    });
    expect(teamIgnoredNote(p, 'first_response')).toBeNull();
  });
});

describe('deadPolicyCount', () => {
  it('counts only policies dead on both halves', () => {
    const half = policy({ id: 'a', first_response_target: null });
    const both = policy({ id: 'b', first_response_target: null, resolution_target: null });
    const off = policy({ id: 'c', is_active: false });
    expect(deadPolicyCount([half, both, off])).toBe(2);
  });
});

describe('breachesGoingNowhere', () => {
  it('counts only the halves that cannot fire', () => {
    const p = policy({
      first_response_target: null,
      breaches_last_30d: { first_response: 11, resolution: 4 }
    });
    expect(breachesGoingNowhere([p])).toBe(11);
  });

  it('counts both halves of an off policy', () => {
    const p = policy({
      is_active: false,
      breaches_last_30d: { first_response: 11, resolution: 4 }
    });
    expect(breachesGoingNowhere([p])).toBe(15);
  });

  it('counts a team-but-no-target half, which the old rule reported as live', () => {
    const p = policy({
      first_response_target: null,
      notify_team: SUPPORT,
      breaches_last_30d: { first_response: 7, resolution: 0 }
    });
    expect(breachesGoingNowhere([p])).toBe(7);
  });

  it('is zero when every half fires', () => {
    expect(
      breachesGoingNowhere([policy({ breaches_last_30d: { first_response: 9, resolution: 9 } })])
    ).toBe(0);
  });
});

describe('unconfiguredPriorities', () => {
  it('returns the priorities with no policy, worst first', () => {
    expect(unconfiguredPriorities([policy({ priority: 'High' })])).toEqual([
      'Urgent',
      'Normal',
      'Low'
    ]);
  });

  it('is empty once all four are configured', () => {
    const all = ['Urgent', 'High', 'Normal', 'Low'].map((priority) => policy({ priority }));
    expect(unconfiguredPriorities(all)).toEqual([]);
  });
});

describe('teamSaysSo', () => {
  it('is false for a bare name that needs the word added', () => {
    expect(teamSaysSo('Support')).toBe(false);
  });

  it('is true when the name already ends in team/teams', () => {
    expect(teamSaysSo('Support Team')).toBe(true);
    expect(teamSaysSo('support teams')).toBe(true);
    expect(teamSaysSo('Team')).toBe(true);
  });

  it('does not fire on a name that merely ends in those letters', () => {
    expect(teamSaysSo('Downsteam')).toBe(false);
  });
});

describe('joinWithAnd', () => {
  it('joins one, two and three parts', () => {
    expect(joinWithAnd([])).toBe('');
    expect(joinWithAnd(['Urgent'])).toBe('Urgent');
    expect(joinWithAnd(['Urgent', 'High'])).toBe('Urgent and High');
    expect(joinWithAnd(['Urgent', 'High', 'Low'])).toBe('Urgent, High and Low');
  });

  it('uses the conjunction it is given', () => {
    expect(joinWithAnd(['Urgente', 'Alta', 'Baja'], 'y')).toBe('Urgente, Alta y Baja');
  });
});
