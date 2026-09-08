# Operator-console fields on Org: status / status_reason / deleted_at /
# subdomain / routing_key.

import django.db.models.functions.text
from django.db import migrations, models

import common.models
import common.validators


def populate_routing_keys(apps, schema_editor):
    Org = apps.get_model("common", "Org")
    for org in Org.objects.filter(routing_key__isnull=True):
        # Not `common.models.generate_routing_key` for correctness (it doesn't
        # touch the historical model), but the same shape.
        import secrets

        org.routing_key = secrets.token_hex(6)
        org.save(update_fields=["routing_key"])


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0042_alter_org_default_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="org",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="org",
            name="status",
            field=models.CharField(
                choices=[
                    ("ACTIVE", "Active"),
                    ("SUSPENDED", "Suspended"),
                    ("DELETED", "Deleted"),
                ],
                db_index=True,
                default="ACTIVE",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="org",
            name="status_reason",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Free-text note for a suspension or deletion, e.g. "
                    "'non-payment 2026-09'."
                ),
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="org",
            name="subdomain",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Subdomain label, e.g. 'acme'. Lowercase letters, digits "
                    "and hyphens."
                ),
                max_length=63,
                validators=[common.validators.validate_org_subdomain],
            ),
        ),
        # routing_key: add nullable, backfill per row, then make it unique.
        # A callable default on a unique field would evaluate once and collide
        # across existing rows.
        migrations.AddField(
            model_name="org",
            name="routing_key",
            field=models.CharField(editable=False, max_length=32, null=True),
        ),
        migrations.RunPython(populate_routing_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="org",
            name="routing_key",
            field=models.CharField(
                default=common.models.generate_routing_key,
                editable=False,
                max_length=32,
                unique=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="org",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("subdomain"),
                condition=models.Q(("subdomain", ""), _negated=True),
                name="unique_org_subdomain",
            ),
        ),
    ]
