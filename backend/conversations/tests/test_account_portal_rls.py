"""RLS-enforced proof that the Chatwoot webhook can resolve its own account
under an empty context (Option 1, same pattern as
invoices/tests/test_portal_rls.py and
cases/tests/test_inbound_mailbox_portal_rls.py).

Runs only under a non-superuser Postgres role (``RLS_ENFORCE=1
--ds=crm.test_settings_postgres``). Found live, by hand, against a real
local Chatwoot posting to a real local backend -- the webhook 404'd on
every delivery until this fix, because the account lookup ran before any
RLS context existed. See docs/PORTAL_RLS.md.
"""

import pytest
from django.db import connection

from common.models import Org, PortalAccessToken
from common.portal_tokens import portal_token_hash, resolve_portal_org_by_hash
from common.tasks import set_rls_context
from conversations.models import ChatwootAccount

pytestmark = [pytest.mark.postgres_only, pytest.mark.django_db]


def _set_ctx(value):
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.current_org', %s, false)", [value])


def test_resolution_reads_account_that_empty_context_hides():
    if connection.vendor != "postgresql":
        pytest.skip("RLS requires PostgreSQL")

    org = Org.objects.create(name="RLS Chatwoot Org")

    _set_ctx(str(org.id))
    try:
        account = ChatwootAccount.objects.create(
            org=org, base_url="https://chat.example.com", account_id=1
        )
    finally:
        _set_ctx("")

    # 1. The bug this fixes: the scoped query cannot see the row.
    assert (
        ChatwootAccount.objects.filter(
            webhook_token=account.webhook_token, is_active=True
        ).first()
        is None
    )

    # 2. The unscoped lookup resolves the org anyway (registered by the
    #    conversations.signals post_save receiver when created above).
    resolved = resolve_portal_org_by_hash(
        portal_token_hash(account.webhook_token), PortalAccessToken.CHATWOOT_WEBHOOK
    )
    assert resolved == str(org.id)

    # 3. With the resolved context set, the row is readable under full RLS.
    try:
        set_rls_context(resolved)
        assert (
            ChatwootAccount.objects.filter(
                webhook_token=account.webhook_token, is_active=True
            ).first()
            is not None
        )
    finally:
        _set_ctx("")

    # 4. A wrong resource type must not resolve.
    assert (
        resolve_portal_org_by_hash(
            portal_token_hash(account.webhook_token),
            PortalAccessToken.INBOUND_MAILBOX,
        )
        is None
    )
