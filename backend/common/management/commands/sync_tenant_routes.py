"""Rewrite the Traefik tenant-route file from the current set of active orgs.

Run it once after enabling ``TRAEFIK_DYNAMIC_FILE`` (nothing has fired the
signal yet), and any time the file might have drifted from the database. Prints
the rendered config with ``--dry-run`` instead of writing.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from common.tenant_routes import render_tenant_routes, write_tenant_routes


class Command(BaseCommand):
    help = "Regenerate the Traefik per-tenant subdomain router file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the config that would be written and exit.",
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write(render_tenant_routes())
            return

        path = getattr(settings, "TRAEFIK_DYNAMIC_FILE", "") or ""
        if not path:
            self.stderr.write(
                "TRAEFIK_DYNAMIC_FILE is not set; nothing to write. "
                "Set it (and mount the file into Traefik's file provider) first."
            )
            return

        written = write_tenant_routes()
        if written:
            self.stdout.write(self.style.SUCCESS(f"Wrote {written}"))
        else:
            self.stderr.write(f"Failed to write {path}; see the log.")
