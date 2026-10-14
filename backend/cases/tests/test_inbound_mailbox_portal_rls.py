"""RLS-enforced proof that the inbound-email webhook can resolve its own
mailbox under an empty context (Option 1, same pattern as
invoices/tests/test_portal_rls.py).

Runs only under a non-superuser Postgres role (``RLS_ENFORCE=1
--ds=crm.test_settings_postgres``): the whole point is the behaviour a
superuser dev DB hides. Found live, against this exact role, by hand --
`InboundMailbox.objects.filter(pk=mailbox_id)` returned `None` for a real,
active mailbox when `app.current_org` was empty, which is exactly the state
a genuine anonymous SNS POST starts in.

See docs/PORTAL_RLS.md.
"""

import pytest
from django.db import connection

from cases.models import InboundMailbox
from common.models import Org, PortalAccessToken
from common.portal_tokens import portal_token_hash, resolve_portal_org_by_hash
from common.tasks import set_rls_context

pytestmark = [pytest.mark.postgres_only, pytest.mark.django_db]


def _set_ctx(value):
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.current_org', %s, false)", [value])


def test_resolution_reads_mailbox_that_empty_context_hides():
    if connection.vendor != "postgresql":
        pytest.skip("RLS requires PostgreSQL")

    org = Org.objects.create(name="RLS Mailbox Org")

    _set_ctx(str(org.id))
    try:
        mailbox = InboundMailbox.objects.create(org=org, address="rls@example.com")
    finally:
        _set_ctx("")

    # 1. The bug this fixes: the scoped query cannot see the row.
    assert InboundMailbox.objects.filter(pk=mailbox.id, is_active=True).first() is None

    # 2. The unscoped lookup resolves the org anyway (registered by the
    #    cases.signals post_save receiver when the mailbox was created above).
    resolved = resolve_portal_org_by_hash(
        portal_token_hash(str(mailbox.id)), PortalAccessToken.INBOUND_MAILBOX
    )
    assert resolved == str(org.id)

    # 3. With the resolved context set, the row is readable under full RLS.
    try:
        set_rls_context(resolved)
        assert (
            InboundMailbox.objects.filter(pk=mailbox.id, is_active=True).first()
            is not None
        )
    finally:
        _set_ctx("")

    # 4. A wrong resource type must not resolve.
    assert (
        resolve_portal_org_by_hash(
            portal_token_hash(str(mailbox.id)), PortalAccessToken.CHATWOOT_WEBHOOK
        )
        is None
    )
