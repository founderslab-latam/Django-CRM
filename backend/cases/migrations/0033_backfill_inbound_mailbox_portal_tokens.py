"""Backfill the unscoped mailbox_id → org lookup from existing InboundMailbox
rows (see cases/inbound_views.py and cases/signals.py for why it must exist
at all).

Same chicken-and-egg as common/0031_backfill_portal_tokens.py, and the same
fix: an empty RLS context may or may not hide InboundMailbox, depending on
whether the DB role is a superuser, so probe first and only fall back to the
expensive per-org pass when the probe shows the org-scoped rows are actually
hidden.
"""

import hashlib

from django.db import migrations


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def backfill(apps, schema_editor):
    connection = schema_editor.connection
    is_postgres = connection.vendor == "postgresql"

    Org = apps.get_model("common", "Org")
    InboundMailbox = apps.get_model("cases", "InboundMailbox")
    PortalAccessToken = apps.get_model("common", "PortalAccessToken")

    def upsert(mailbox_id, org_id):
        PortalAccessToken.objects.update_or_create(
            token_hash=_sha256(str(mailbox_id)),
            defaults={
                "org_id": org_id,
                "resource_type": "inbound_mailbox",
                "resource_id": mailbox_id,
            },
        )

    def backfill_visible_rows():
        for mailbox_id, org_id in InboundMailbox.objects.values_list(
            "id", "org_id"
        ).iterator():
            upsert(mailbox_id, org_id)

    def set_context(value):
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_org', %s, false)", [value])

    if not is_postgres:
        backfill_visible_rows()
        return

    set_context("")
    rls_bypassed = InboundMailbox.objects.exists()

    if rls_bypassed:
        backfill_visible_rows()
        return

    for org_id in Org.objects.values_list("id", flat=True).iterator():
        set_context(str(org_id))
        backfill_visible_rows()
    set_context("")


def unregister(apps, schema_editor):
    """Reverse: drop the rows this migration created. Leaves any row a later
    save re-registered alone -- those aren't this migration's to take back."""
    PortalAccessToken = apps.get_model("common", "PortalAccessToken")
    PortalAccessToken.objects.filter(resource_type="inbound_mailbox").delete()


class Migration(migrations.Migration):
    # Also after 0032_backfill_...: founderslab-master shipped that same
    # backfill as 0032 (already applied in prod) while this branch had it as
    # 0033. Depending on both joins the two leaves; re-running is harmless
    # (update_or_create).
    dependencies = [
        ("cases", "0032_emailmessage_comment"),
        ("cases", "0032_backfill_inbound_mailbox_portal_tokens"),
        ("common", "0047_alter_portalaccesstoken_resource_type"),
    ]

    operations = [
        migrations.RunPython(backfill, unregister),
    ]
