# The client portal and RLS

The public endpoints: the invoice and estimate links emailed to customers,
and the CSAT survey link, are the only anonymous, org-less requests that need
to read org-scoped rows. That combination puts them at odds with RLS, and this
note records where that stands.

## What was wrong, and what is now fixed

`RequireOrgContext.EXEMPT_PATHS` listed `/api/public/csat/` but not
`/api/public/invoice/` or `/api/public/estimate/`. `_is_exempt` is a
`startswith` check, so the CSAT entry did not cover its siblings, and the
middleware returned

```
403 {"detail": "Organization context is required. Please login again."}
```

to every anonymous caller. That is, to every customer who clicked a link. The
middleware runs before the view, so token validity never entered into it.

**Fixed**: both prefixes are now exempt. Regression tests live in
`invoices/tests/test_invoices_api.py::TestPublicPortalIsReachableAnonymously`
and go through the full Django test client. That matters: the pre-existing
view tests use `APIRequestFactory` and call the view directly, bypassing
MIDDLEWARE, which is why they passed throughout the outage.

## What is still open

Reachability is not readability. `_set_org_context` returns early when
`request.org is None`, so a public request runs with `app.current_org` empty,
and the isolation policy built by `common.rls.get_enable_policy_sql` is

```sql
USING (org_id::text = (select NULLIF(current_setting('app.current_org', true), '')))
```

Empty context yields `NULL`, which matches nothing. `invoice`, `estimate` and
`csat_survey` are all in `ORG_SCOPED_TABLES`.

Measured directly as `crm_user` (non-superuser, no `BYPASSRLS`) with empty
context:

| table         | rows visible |
| ------------- | ------------ |
| `invoice`     | 0            |
| `estimate`    | 0            |
| `csat_survey` | 0            |

So on a correctly configured production database, these endpoints now return
**404 instead of 403**. The customer still cannot see their invoice.

This is masked in development, where `DBUSER=postgres`. A superuser, which
bypasses RLS entirely, so every public endpoint appears to work. Do not take a
green dev run as evidence.

**This applies to CSAT too.** `cases/csat_views.py::_load_survey` does its
initial `CsatSurvey.objects.filter(token_hash=...)` with no context set, and
only calls `set_rls_context(survey.org_id)` afterwards. The lookup itself is
subject to the same policy. CSAT should be re-tested against `crm_user` rather
than assumed healthy.

## The shape of the remaining fix

The problem is a chicken-and-egg: you cannot set `app.current_org` until you
know the org, and you cannot read the row that tells you the org until the
context is set. Three ways out, in the order they should be considered:

1. **An unscoped token→org lookup.** A small table (or an unscoped column on
   an existing unscoped table) mapping `token_hash` → `org_id`, deliberately
   *not* in `ORG_SCOPED_TABLES`. The view resolves the org, calls
   `set_rls_context(org_id)`, then queries normally under full RLS. This adds
   a surface rather than weakening one, and it leaks only the existence of a
   token to somebody who already holds it. Requires a migration.

2. **A dedicated lookup role.** A Postgres role permitted to select
   `public_token`/`token_hash` and `org_id` and nothing else. Narrower than
   option 3, but it still means a second connection path and another role to
   keep correct.

3. **A policy exception** allowing SELECT by token with empty context. Cheapest
   to write and the easiest to get wrong: it widens the isolation policy on
   the invoice and estimate tables themselves, which are exactly the tables
   whose isolation matters. Not to be done without an explicit decision.

Do not reach for `BYPASSRLS` here. That role exists for the superadmin
dashboard and every addition to its surface is a step toward the escalation
path the threat model is built around.

## Addendum: the same bug, in two webhooks (2026-10-14)

Option 1 from the list above shipped as `common.PortalAccessToken` /
`common.portal_tokens` (see that model's docstring for the final shape). It
closed the gap for invoice/estimate/CSAT, but two anonymous webhooks built
afterward hit the identical chicken-and-egg without going through it:

- `cases.inbound_views.InboundMailboxWebhookView` (AWS SNS, inbound email) --
  `InboundMailbox.objects.filter(pk=mailbox_id)` with no context, same as
  `CsatSurvey`'s original bug.
- `conversations.webhook_views.ChatwootWebhookView` (Chatwoot, Live Chat +
  WhatsApp) -- same shape, found live while wiring up a real Chatwoot
  instance to a real local backend: every delivery 404'd under the
  project's actual non-superuser `crm_user` role, despite the middleware
  being correctly exempt and the account genuinely existing and active.

**Fixed** the same way: `PortalAccessToken.RESOURCE_CHOICES` gained
`inbound_mailbox` and `chatwoot_webhook`; both webhooks now resolve their org
from the unscoped lookup before touching their own org-scoped table, same as
invoice/estimate/CSAT. Registration happens on every `post_save` of the
owning row (`cases.signals`, `conversations.signals` -- both keys are stable
after creation, so this fires once in practice and heals a pre-existing gap
on any later touch) plus a data migration backfilling rows that existed
before the fix. Regression tests:
`cases/tests/test_inbound_mailbox_portal_rls.py`,
`conversations/tests/test_account_portal_rls.py` (same `postgres_only`
pattern as `invoices/tests/test_portal_rls.py`).

The warning in "This is masked in development" above is the exact trap that
produced both bugs: every test and every manual check against this dev
stack's `DBUSER=postgres` superuser connection passed, including the webhook
view tests written at the time. Only a request against the real `crm_user`
role -- or, as it happened, a real external caller (Chatwoot) hitting a real
deployment configured correctly -- ever exercised the failure.

## What must not be done

- Do not make the app's DB user a superuser to "fix" the portal. That disables
  RLS for the entire application.
- Do not broaden the exemption to `/api/public/` or `/api/`. The two prefixes
  are specific so that anything mounted there later has to opt in.
- Do not test this with `APIRequestFactory`. The bug lived in middleware; a
  test that skips middleware cannot see it.
