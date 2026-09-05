/**
 * Translates the raw enum values used by the Settings screens Dev1 owns
 * (custom fields, API tokens, web forms) into i18n catalog keys, without
 * editing the shared files those values come from.
 *
 * `$lib/v2/enums.js` (`FIELD_TYPE_LABEL`, `TARGET_MODEL_LABEL`), the coarse
 * expiry list in `$lib/v2/token-rules.js` and the lead-field whitelist in
 * `$lib/v2/webform-fields.js` are all imported by code outside Settings, and
 * their maps are mirrored 1:1 from the Django models / backend constants on
 * purpose. Mirror of `$lib/cases/labels.js` and `$lib/invoices/labels.js`.
 *
 * The raw value is what the API sends and what a form posts back, so it is
 * never rewritten here: only the label shown to a person is translated. A
 * value with no mapping falls through to itself, so an enum the backend grows
 * still renders (untranslated) rather than blanking out.
 *
 * Catalog keys live under `settings.*`
 * (see `frontend/src/lib/i18n/messages/{en,es}.json`).
 */

import { daysSince } from '$lib/v2/format.js';
import { lastActivityAt } from '$lib/v2/token-rules.js';

/** @type {Record<string, string>} */
const FIELD_TYPE_KEYS = {
  text: 'text',
  textarea: 'textarea',
  number: 'number',
  dropdown: 'dropdown',
  date: 'date',
  checkbox: 'checkbox'
};

/** @type {Record<string, string>} */
const TARGET_MODEL_KEYS = {
  Account: 'account',
  Case: 'case',
  Contact: 'contact',
  Estimate: 'estimate',
  Invoice: 'invoice',
  Lead: 'lead',
  Opportunity: 'opportunity',
  RecurringInvoice: 'recurring_invoice',
  Task: 'task'
};

/** @type {Record<string, string>} */
const EXPIRY_KEYS = {
  90: 'd90',
  30: 'd30',
  365: 'y1',
  never: 'never'
};

/** @type {Record<string, string>} */
const WEBFORM_LEAD_FIELD_KEYS = {
  salutation: 'salutation',
  first_name: 'first_name',
  last_name: 'last_name',
  email: 'email',
  phone: 'phone',
  company_name: 'company_name',
  job_title: 'job_title',
  website: 'website',
  title: 'title',
  description: 'description',
  city: 'city',
  state: 'state',
  country: 'country',
  postcode: 'postcode',
  industry: 'industry'
};

/** @type {Record<string, string>} */
const SUBMISSION_STATUS_KEYS = {
  accepted: 'accepted',
  accepted_duplicate: 'accepted_duplicate',
  rejected_spam: 'rejected_spam',
  rejected_invalid: 'rejected_invalid',
  rejected_captcha: 'rejected_captcha'
};

/** @param {string} raw */
export function fieldTypeKey(raw) {
  return `settings.custom_fields.enums.field_type.${FIELD_TYPE_KEYS[raw] ?? raw}`;
}

/** @param {string} raw */
export function targetModelKey(raw) {
  return `settings.custom_fields.enums.target_model.${TARGET_MODEL_KEYS[raw] ?? raw}`;
}

/** @param {string | undefined | null} value */
export function tokenExpiryKey(value) {
  return `settings.api_tokens.expiry.${EXPIRY_KEYS[value ?? ''] ?? value ?? 'never'}`;
}

/** @param {string} value */
export function webformLeadFieldKey(value) {
  return `settings.web_forms.detail.lead_field.${WEBFORM_LEAD_FIELD_KEYS[value] ?? value}`;
}

/** @param {string} status */
export function webformSubmissionStatusKey(status) {
  return `settings.web_forms.detail.activity.status.${SUBMISSION_STATUS_KEYS[status] ?? status}`;
}

/**
 * The catalog key for a token's coarse state, matching the branching in
 * `tokenStatus` (`$lib/v2/token-rules.js`). Only the label is re-derived here;
 * the pill tone still comes from `tokenStatus`, so the two cannot drift.
 *
 * @param {any} token
 */
export function tokenStateKey(token) {
  if (token?.revoked_at) return 'settings.api_tokens.state.revoked';
  if (!token?.is_live) return 'settings.api_tokens.state.expired';
  return 'settings.api_tokens.state.live';
}

/**
 * What a token may do, as a catalog key plus its interpolation values, mirroring
 * `scopeSummary` (`$lib/v2/token-rules.js`) without the English strings.
 *
 * @param {any} token
 * @returns {{ key: string, values: Record<string, string> }}
 */
export function tokenScopeDescriptor(token) {
  const scopes = token?.scopes ?? [];
  if (scopes.length === 0) {
    const first = (token?.owner?.name ?? '').split(' ')[0];
    return first
      ? { key: 'settings.api_tokens.scope.everything_named', values: { name: first } }
      : { key: 'settings.api_tokens.scope.everything_owner', values: {} };
  }
  if (scopes.every((/** @type {string} */ s) => s.endsWith(':read'))) {
    return { key: 'settings.api_tokens.scope.read_only', values: {} };
  }
  return { key: 'settings.api_tokens.scope.list', values: { scopes: scopes.join(', ') } };
}

/**
 * The clay "unused" line under Last used, as a catalog key plus values, or null
 * when there is nothing to say. Mirrors `staleness` (`$lib/v2/token-rules.js`).
 *
 * @param {any} token
 * @param {Date} [now]
 * @returns {{ key: string, values: Record<string, number> } | null}
 */
export function tokenStalenessDescriptor(token, now = new Date()) {
  if (!token?.is_live) return null;
  const days = daysSince(lastActivityAt(token), now);
  if (days === null || days <= 90) return null;
  return token.last_used_at
    ? { key: 'settings.api_tokens.staleness.unused_for', values: { days } }
    : { key: 'settings.api_tokens.staleness.never_used', values: { days } };
}

/* ── ticket-handling Settings screens (Dev2) ────────────────────────────────
 *
 * The same rule as above: `$lib/v2/enums.js` carries these maps mirrored from
 * the Django models, and code outside Settings imports them, so nothing there
 * is touched. Each helper turns a raw enum value into a `settings.*` catalog
 * key; an unmapped value falls through to itself so a value the backend grows
 * still renders. Case priority / status / type are NOT re-mapped here: those
 * reuse `$lib/cases/labels.js` (`casePriorityKey`, `caseStatusKey`,
 * `caseTypeKey`) so the helpdesk vocabulary stays in one place.
 */

/** @type {Record<string, string>} */
const ROUTING_STRATEGY_KEYS = {
  direct: 'direct',
  round_robin: 'round_robin',
  least_busy: 'least_busy',
  by_team: 'by_team'
};

/** @type {Record<string, string>} */
const CONDITION_FIELD_KEYS = {
  priority: 'priority',
  case_type: 'case_type',
  account: 'account',
  tags: 'tags',
  from_email_domain: 'from_email_domain',
  mailbox_id: 'mailbox_id'
};

/** @type {Record<string, string>} */
const CONDITION_OP_KEYS = {
  eq: 'eq',
  in: 'in',
  contains: 'contains',
  regex: 'regex'
};

/** @type {Record<string, string>} */
const ESCALATION_ACTION_KEYS = {
  notify: 'notify',
  reassign: 'reassign',
  notify_and_reassign: 'notify_and_reassign'
};

/** @type {Record<string, string>} */
const MAILBOX_PROVIDER_KEYS = {
  ses: 'ses',
  mailgun: 'mailgun',
  postmark: 'postmark',
  imap: 'imap'
};

/** @type {Record<string, string>} */
const MACRO_SCOPE_KEYS = {
  org: 'org',
  personal: 'personal'
};

/**
 * The verb phrase a routing rule performs (`ROUTING_STRATEGY_LABEL`), used on
 * the rule card where it runs straight into the target names.
 * @param {string} raw
 */
export function routingStrategyKey(raw) {
  return `settings.routing.enums.strategy.${ROUTING_STRATEGY_KEYS[raw] ?? raw}`;
}

/**
 * The standalone name for the strategy select (`ROUTING_STRATEGY_NAME`).
 * @param {string} raw
 */
export function routingStrategyNameKey(raw) {
  return `settings.routing.enums.strategy_name.${ROUTING_STRATEGY_KEYS[raw] ?? raw}`;
}

/** A field a routing condition can test (`CONDITION_FIELD_LABEL`). @param {string} raw */
export function conditionFieldKey(raw) {
  return `settings.routing.enums.condition_field.${CONDITION_FIELD_KEYS[raw] ?? raw}`;
}

/** A routing condition operator (`CONDITION_OP_LABEL`). @param {string} raw */
export function conditionOpKey(raw) {
  return `settings.routing.enums.condition_op.${CONDITION_OP_KEYS[raw] ?? raw}`;
}

/** What an escalation half does (`ESCALATION_ACTION_LABEL`). @param {string} raw */
export function escalationActionKey(raw) {
  return `settings.escalation.enums.action.${ESCALATION_ACTION_KEYS[raw] ?? raw}`;
}

/** An inbound-mail provider (`MAILBOX_PROVIDER_LABEL`). @param {string} raw */
export function mailboxProviderKey(raw) {
  return `settings.inbound_email.enums.provider.${MAILBOX_PROVIDER_KEYS[raw] ?? raw}`;
}

/** Who a macro is visible to (`MACRO_SCOPE_LABEL`). @param {string} raw */
export function macroScopeKey(raw) {
  return `settings.macros.enums.scope.${MACRO_SCOPE_KEYS[raw] ?? raw}`;
}

/**
 * The approver-role vocabulary the approval form offers (ADMIN / MANAGER).
 * MANAGER is not a real `Profile.role`, so `ROLE_LABEL` has no entry for it;
 * both are labelled here.
 * @param {string} raw
 */
export function approverRoleKey(raw) {
  return `settings.ticket_approvals.enums.approver_role.${raw === 'MANAGER' ? 'manager' : raw === 'ADMIN' ? 'admin' : raw}`;
}
