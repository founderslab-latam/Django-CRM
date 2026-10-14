"""Backfill the unscoped webhook_token → org lookup from existing
ChatwootAccount rows (see conversations/webhook_views.py and
conversations/signals.py for why it must exist at all).

Same chicken-and-egg as common/0031_backfill_portal_tokens.py, and the same
fix: probe whether an empty RLS context already exposes ChatwootAccount
(superuser dev DB) before falling back to the expensive per-org pass.
"""

import hashlib

from django.db import migrations


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def backfill(apps, schema_editor):
    connection = schema_editor.connection
    is_postgres = connection.vendor == "postgresql"

    Org = apps.get_model("common", "Org")
    ChatwootAccount = apps.get_model("conversations", "ChatwootAccount")
    PortalAccessToken = apps.get_model("common", "PortalAccessToken")

    def upsert(account_id, org_id, webhook_token):
        PortalAccessToken.objects.update_or_create(
            token_hash=_sha256(webhook_token),
            defaults={
                "org_id": org_id,
                "resource_type": "chatwoot_webhook",
                "resource_id": account_id,
            },
        )

    def backfill_visible_rows():
        for account_id, org_id, webhook_token in ChatwootAccount.objects.values_list(
            "id", "org_id", "webhook_token"
        ).iterator():
            upsert(account_id, org_id, webhook_token)

    def set_context(value):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_org', %s, false)", [value])

    if not is_postgres:
        backfill_visible_rows()
        return

    set_context("")
    rls_bypassed = ChatwootAccount.objects.exists()

    if rls_bypassed:
        backfill_visible_rows()
        return

    for org_id in Org.objects.values_list("id", flat=True).iterator():
        set_context(str(org_id))
        backfill_visible_rows()
    set_context("")


def unregister(apps, schema_editor):
    PortalAccessToken = apps.get_model("common", "PortalAccessToken")
    PortalAccessToken.objects.filter(resource_type="chatwoot_webhook").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0002_enable_rls"),
        ("common", "0047_alter_portalaccesstoken_resource_type"),
    ]

    operations = [
        migrations.RunPython(backfill, unregister),
    ]
