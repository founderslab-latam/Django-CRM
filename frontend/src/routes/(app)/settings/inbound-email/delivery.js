/**
 * What an inbound address actually does with mail, as opposed to what its
 * on/off switch says.
 *
 * `is_active` is one of three gates a delivery has to clear, and the page used
 * to draw it as the only one: an address was either "Creating tickets" or
 * "Creating nothing". Two states were drawn as the first and behave as the
 * second, both silently, because inbound mail has no user watching it fail:
 *
 * 1. **An unimplemented provider.** `InboundMailbox.PROVIDER_CHOICES` offers
 *    four, and `InboundMailboxWebhookView.post` answers 501 for every one that
 *    is not `ses`. A Mailgun address marked active accepts mail and opens
 *    nothing, forever, and the form offered the four as equals.
 * 2. **An unpinned SES address.** The webhook needs both a valid SNS signature
 *    and a `topic_arn` that matches this mailbox, because a signature alone
 *    only proves the message came from *some* topic in *some* AWS account. A
 *    mailbox acquires its pin from the first signature-verified
 *    SubscriptionConfirmation, so between "added here" and "subscribed in AWS"
 *    it rejects everything.
 *
 * The states are ordered as the webhook itself checks them, so `deliveryState`
 * answers "which gate does a delivery fail first", and an address that clears
 * all three is the only one called live. Nothing here is a security control:
 * every gate is enforced in `cases/inbound_views.py`, and this only decides
 * what the page says about it.
 *
 * `mobile/lib/data/models/mailbox.dart` carries the same rules.
 */

/** The providers the webhook actually handles. Everything else 501s. */
export const SUPPORTED_PROVIDERS = ['ses'];

/**
 * The first gate mail to this address would fail, or `'live'`.
 *
 * @param {{ is_active?: boolean, provider?: string, has_topic_arn?: boolean }} mailbox
 * @returns {'off' | 'unsupported' | 'unconfirmed' | 'live'}
 */
export function deliveryState(mailbox) {
  if (!mailbox?.is_active) return 'off';
  if (!SUPPORTED_PROVIDERS.includes(mailbox.provider)) return 'unsupported';
  if (!mailbox.has_topic_arn) return 'unconfirmed';
  return 'live';
}

/**
 * i18n catalog keys, not English. `deliveryLabel` returns the key for a state;
 * the page resolves it with `$_`. Kept as descriptors so this module stays
 * testable without the i18n store, matching `tickets/[id]/close.js`.
 */
const LABEL_KEY = {
  off: 'settings.inbound_email.delivery_label.off',
  unsupported: 'settings.inbound_email.delivery_label.unsupported',
  unconfirmed: 'settings.inbound_email.delivery_label.unconfirmed',
  live: 'settings.inbound_email.delivery_label.live'
};

const TONE = {
  off: 'clay',
  unsupported: 'rust',
  unconfirmed: 'clay',
  live: 'moss'
};

/** The catalog key for a state's pill label. @param {string} state */
export function deliveryLabel(state) {
  return LABEL_KEY[state] ?? LABEL_KEY.off;
}

/** @param {string} state */
export function deliveryTone(state) {
  return TONE[state] ?? TONE.off;
}

/**
 * Why nothing is arriving, as a catalog key plus its interpolation values, or
 * null when mail is getting through. `providerLabel` is passed in (already
 * translated) rather than imported so this module stays free of the enum map.
 *
 * @param {string} state
 * @param {string} providerLabel
 * @returns {{ key: string, values?: Record<string, string> } | null}
 */
export function deliveryExplanation(state, providerLabel) {
  if (state === 'off') {
    return { key: 'settings.inbound_email.delivery_why.off' };
  }
  if (state === 'unsupported') {
    return {
      key: 'settings.inbound_email.delivery_why.unsupported',
      values: { provider: providerLabel }
    };
  }
  if (state === 'unconfirmed') {
    return { key: 'settings.inbound_email.delivery_why.unconfirmed' };
  }
  return null;
}

/**
 * The addresses that would actually open a ticket right now.
 *
 * Derived from the rows rather than read off the server's `totals.active`,
 * which counts `is_active` and nothing else. `GET /cases/mailboxes/` returns
 * every mailbox in the org unfiltered and unpaginated, so this counts the same
 * set the total does, and answers the question the header asks.
 *
 * @param {any[]} mailboxes
 */
export function deliveringCount(mailboxes) {
  return (mailboxes ?? []).filter((m) => deliveryState(m) === 'live').length;
}

/**
 * The rows worth a banner: on, and creating nothing.
 *
 * An off address is left out on purpose. Somebody chose that, and it is the
 * one state of the three the row already reads correctly.
 *
 * @param {any[]} mailboxes
 */
export function silentMailboxes(mailboxes) {
  return (mailboxes ?? []).filter((m) => {
    const state = deliveryState(m);
    return state === 'unsupported' || state === 'unconfirmed';
  });
}

/**
 * The provider select's label for one choice.
 *
 * The unimplemented three stay selectable: the column accepts them, an admin
 * may be recording an address before the integration exists, and hiding them
 * would silently rewrite a mailbox already set to one. They say so instead.
 *
 * @param {string} value
 * @param {string} label the already-translated provider name
 * @returns {{ key: string, values: { label: string } }}
 */
export function providerChoiceLabel(value, label) {
  return SUPPORTED_PROVIDERS.includes(value)
    ? { key: 'settings.inbound_email.provider_choice_plain', values: { label } }
    : { key: 'settings.inbound_email.provider_choice_not_wired', values: { label } };
}
