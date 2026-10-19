"""`common.tasks.orgs_with_rls_context`: the sweep every periodic task uses.

What it exists for -- setting each org's RLS context *before* that org's rows
are queried -- can't be observed here: the test settings are SQLite, which has
no RLS. That was verified against PostgreSQL with the non-superuser role (see
the helper's docstring). These tests pin the parts SQLite can see.
"""

from unittest.mock import patch

import pytest

from common.models import Org
from common.tasks import orgs_with_rls_context


@pytest.mark.django_db
class TestOrgsWithRlsContext:
    def test_walks_active_orgs_only(self, org_a, org_b):
        org_b.status = "SUSPENDED"
        org_b.save()

        walked = [org.id for org in orgs_with_rls_context()]

        assert org_a.id in walked
        assert org_b.id not in walked

    def test_sets_each_orgs_context_before_yielding_it(self, org_a):
        seen = []
        with patch(
            "common.tasks.set_rls_context", side_effect=lambda oid: seen.append(oid)
        ):
            for org in orgs_with_rls_context():
                assert seen[-1] == org.id

    def test_clears_the_context_even_when_the_caller_stops_early(self, org_a, org_b):
        with patch("common.tasks.clear_rls_context") as cleared:
            sweep = orgs_with_rls_context()
            next(sweep)
            sweep.close()
        cleared.assert_called_once()

    def test_clears_the_context_when_the_caller_raises(self, org_a):
        with patch("common.tasks.clear_rls_context") as cleared:
            with pytest.raises(RuntimeError):
                for _org in orgs_with_rls_context():
                    raise RuntimeError("task failed mid-sweep")
        cleared.assert_called_once()
        assert Org.objects.filter(pk=org_a.pk).exists()
