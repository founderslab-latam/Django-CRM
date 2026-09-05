import { describe, it, expect } from 'vitest';
import {
  SUPPORTED_PROVIDERS,
  deliveryState,
  deliveryLabel,
  deliveryTone,
  deliveryExplanation,
  deliveringCount,
  silentMailboxes,
  providerChoiceLabel
} from './delivery.js';

/** @param {any} over */
function mailbox(over = {}) {
  return {
    id: 'm1',
    address: 'support@acme.com',
    provider: 'ses',
    is_active: true,
    has_topic_arn: true,
    ...over
  };
}

describe('deliveryState', () => {
  it('is live only when every gate the webhook checks is clear', () => {
    expect(deliveryState(mailbox())).toBe('live');
  });

  it('is off when the address is turned off', () => {
    expect(deliveryState(mailbox({ is_active: false }))).toBe('off');
  });

  it('is unsupported for a provider the webhook answers 501 for', () => {
    for (const provider of ['mailgun', 'postmark', 'imap']) {
      expect(deliveryState(mailbox({ provider }))).toBe('unsupported');
    }
  });

  it('is unconfirmed for an SES address with no topic pin', () => {
    // The state the page could not see at all before `has_topic_arn` existed:
    // active, supported, and rejecting every notification.
    expect(deliveryState(mailbox({ has_topic_arn: false }))).toBe('unconfirmed');
  });

  it('reports the gate the webhook hits first, not every gate', () => {
    // `is_active` is the mailbox lookup's own filter, so an off Mailgun row
    // fails there before the provider is ever consulted.
    expect(deliveryState(mailbox({ is_active: false, provider: 'mailgun' }))).toBe('off');
    expect(deliveryState(mailbox({ provider: 'mailgun', has_topic_arn: false }))).toBe(
      'unsupported'
    );
  });

  it('treats a row with no pin field as unconfirmed rather than live', () => {
    // Fail closed. An older payload, or a load that forgot the field, must not
    // read as a working address.
    const { has_topic_arn: _dropped, ...withoutPin } = mailbox();
    expect(deliveryState(withoutPin)).toBe('unconfirmed');
  });

  it('is off for a missing mailbox rather than throwing', () => {
    expect(deliveryState(null)).toBe('off');
  });
});

// `deliveryLabel` and `deliveryExplanation` return i18n descriptors now (a
// catalog key, plus values where interpolated) rather than English; the page
// resolves them with `$_`. Same move as `tickets/[id]/close.js`.
describe('deliveryLabel and deliveryTone', () => {
  it('never says creating tickets about an address that creates none', () => {
    for (const state of ['off', 'unsupported', 'unconfirmed']) {
      expect(deliveryLabel(state)).not.toBe('settings.inbound_email.delivery_label.live');
      expect(deliveryTone(state)).not.toBe('moss');
    }
    expect(deliveryLabel('live')).toBe('settings.inbound_email.delivery_label.live');
    expect(deliveryTone('live')).toBe('moss');
  });

  it('falls back to the off wording for an unknown state', () => {
    expect(deliveryLabel('nonsense')).toBe('settings.inbound_email.delivery_label.off');
    expect(deliveryTone('nonsense')).toBe('clay');
  });
});

describe('deliveryExplanation', () => {
  it('points at silence, not failure, for an address turned off', () => {
    expect(deliveryExplanation('off', 'AWS SES')).toEqual({
      key: 'settings.inbound_email.delivery_why.off'
    });
  });

  it('carries the provider name through for an unsupported one', () => {
    expect(deliveryExplanation('unsupported', 'Mailgun')).toEqual({
      key: 'settings.inbound_email.delivery_why.unsupported',
      values: { provider: 'Mailgun' }
    });
  });

  it('has its own key for an unconfirmed address', () => {
    expect(deliveryExplanation('unconfirmed', 'AWS SES')).toEqual({
      key: 'settings.inbound_email.delivery_why.unconfirmed'
    });
  });

  it('has nothing to explain about a live address', () => {
    expect(deliveryExplanation('live', 'AWS SES')).toBeNull();
  });
});

describe('deliveringCount', () => {
  it('counts what opens tickets, not what is switched on', () => {
    // The header used to read `totals.active` under the words "creating
    // tickets". Two of these three are on and open nothing.
    const rows = [
      mailbox({ id: 'a' }),
      mailbox({ id: 'b', provider: 'mailgun' }),
      mailbox({ id: 'c', has_topic_arn: false })
    ];
    expect(deliveringCount(rows)).toBe(1);
    expect(rows.filter((m) => m.is_active).length).toBe(3);
  });

  it('is zero for no rows', () => {
    expect(deliveringCount([])).toBe(0);
    expect(deliveringCount(undefined)).toBe(0);
  });
});

describe('silentMailboxes', () => {
  it('is the rows that are on and creating nothing', () => {
    const rows = [
      mailbox({ id: 'a' }),
      mailbox({ id: 'b', provider: 'imap' }),
      mailbox({ id: 'c', has_topic_arn: false }),
      mailbox({ id: 'd', is_active: false })
    ];
    expect(silentMailboxes(rows).map((m) => m.id)).toEqual(['b', 'c']);
  });

  it('leaves a turned-off address out, because somebody chose that', () => {
    expect(silentMailboxes([mailbox({ is_active: false })])).toEqual([]);
  });
});

describe('providerChoiceLabel', () => {
  it('leaves the one implemented provider unmarked', () => {
    expect(providerChoiceLabel('ses', 'AWS SES')).toEqual({
      key: 'settings.inbound_email.provider_choice_plain',
      values: { label: 'AWS SES' }
    });
  });

  it('marks the three that are not', () => {
    expect(providerChoiceLabel('mailgun', 'Mailgun')).toEqual({
      key: 'settings.inbound_email.provider_choice_not_wired',
      values: { label: 'Mailgun' }
    });
  });

  it('keeps every model choice selectable, marked rather than hidden', () => {
    // Hiding them would silently rewrite a mailbox already set to one.
    const values = ['ses', 'mailgun', 'postmark', 'imap'];
    expect(values.filter((v) => SUPPORTED_PROVIDERS.includes(v))).toEqual(['ses']);
    for (const value of values) {
      expect(providerChoiceLabel(value, value).values.label).toBe(value);
    }
  });
});
