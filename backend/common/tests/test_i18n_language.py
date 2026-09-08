"""Language resolution, the stored preference fields, and localised email.

Covers `common.i18n.resolve_language` (the fallback chain), the `language`
column on User and Org, its write paths (`/api/profile/`, org settings), and
that a Celery email task renders under the resolved language.
"""

from unittest.mock import patch

import pytest
from django.core import mail

from common.email_branding import brand_context, localized_email, logo_url_for_email
from common.i18n import (
    DEFAULT_LANGUAGE,
    normalize_language,
    parse_accept_language,
    resolve_language,
)
from common.models import User


class _Bag:
    """Minimal stand-in with a `.language` attribute."""

    def __init__(self, language=""):
        self.language = language


class TestNormalizeLanguage:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("es", "es"),
            ("ES", "es"),
            ("es-CL", "es"),
            ("es_CL", "es"),
            ("  en  ", "en"),
            ("en-US", "en"),
            ("", None),
            (None, None),
            ("fr", None),
            ("de-DE", None),
            ("xx", None),
        ],
    )
    def test_cases(self, value, expected):
        assert normalize_language(value) == expected


class TestParseAcceptLanguage:
    def test_orders_by_q_then_position(self):
        assert parse_accept_language("es-CL,es;q=0.9,en;q=0.8") == [
            "es-CL",
            "es",
            "en",
        ]

    def test_explicit_q_beats_earlier_default(self):
        assert parse_accept_language("en;q=0.5, es") == ["es", "en"]

    def test_blank_and_wildcard(self):
        assert parse_accept_language("") == []
        assert parse_accept_language("*") == []
        assert parse_accept_language(None) == []


class TestResolveLanguage:
    def test_user_wins(self):
        assert (
            resolve_language(
                user=_Bag("es"),
                org=_Bag("en"),
                accept_language="en-US",
            )
            == "es"
        )

    def test_org_is_next(self):
        assert (
            resolve_language(user=_Bag(""), org=_Bag("es"), accept_language="en")
            == "es"
        )

    def test_accept_language_is_third(self):
        assert (
            resolve_language(
                user=_Bag(""), org=_Bag(""), accept_language="es-CL,es;q=0.9"
            )
            == "es"
        )

    def test_default_when_nothing_usable(self):
        assert resolve_language() == DEFAULT_LANGUAGE
        assert (
            resolve_language(user=_Bag(""), org=_Bag(""), accept_language="fr,de")
            == "en"
        )

    def test_unknown_user_value_falls_through(self):
        assert resolve_language(user=_Bag("fr"), org=_Bag("es")) == "es"


@pytest.mark.django_db
class TestLanguageColumns:
    def test_defaults_blank(self, admin_user, org_a):
        assert admin_user.language == ""
        assert org_a.language == ""

    def test_profile_patch_writes_user_language(self, user_client, user_profile):
        resp = user_client.patch("/api/profile/", {"language": "es"}, format="json")
        assert resp.status_code == 200
        user_profile.user.refresh_from_db()
        assert user_profile.user.language == "es"

    def test_profile_patch_rejects_unsupported_language(self, user_client):
        resp = user_client.patch("/api/profile/", {"language": "fr"}, format="json")
        assert resp.status_code == 400

    def test_profile_patch_blank_clears_language(self, user_client, user_profile):
        user_profile.user.language = "es"
        user_profile.user.save(update_fields=["language"])
        resp = user_client.patch("/api/profile/", {"language": ""}, format="json")
        assert resp.status_code == 200
        user_profile.user.refresh_from_db()
        assert user_profile.user.language == ""

    def test_org_settings_patch_writes_org_language(self, admin_client, org_a):
        resp = admin_client.patch(
            "/api/org/settings/", {"language": "es"}, format="json"
        )
        assert resp.status_code == 200
        org_a.refresh_from_db()
        assert org_a.language == "es"


@pytest.mark.django_db
class TestJwtCarriesLanguage:
    def test_claims_include_user_and_org_language(self, admin_user, org_a):
        from common.serializer import OrgAwareRefreshToken

        admin_user.language = "es"
        admin_user.save(update_fields=["language"])
        org_a.language = "en"
        org_a.save(update_fields=["language"])

        token = OrgAwareRefreshToken.for_user_and_org(admin_user, org_a)
        assert token["language"] == "es"
        assert token["org_language"] == "en"


@pytest.mark.django_db
class TestLocalizedEmail:
    def test_context_manager_activates_language(self):
        from django.utils import translation

        with localized_email(recipient=_Bag("es")):
            assert translation.get_language() == "es"
        with localized_email(org=_Bag("es"), recipient=_Bag("")):
            assert translation.get_language() == "es"

    def test_welcome_email_renders_under_the_users_language(self):
        user = User.objects.create_user(email="es-user@example.com")
        user.language = "es"
        user.save(update_fields=["language"])

        from django.utils import translation

        seen = {}
        real = translation.get_language

        def _capture(template, context=None):
            seen["lang"] = real()
            return "<html></html>"

        from common import tasks as common_tasks

        with patch.object(common_tasks, "render_to_string", side_effect=_capture):
            common_tasks.send_welcome_email(str(user.id))
        assert seen["lang"] == "es"
        assert len(mail.outbox) == 1
        # The subject is built inside the same override; the es catalog ships a
        # translation, so it must not come out as the English source string.
        assert mail.outbox[0].subject != "Welcome to BottleCRM"

    def test_brand_context_without_org(self):
        ctx = brand_context(None)
        assert ctx["email_logo_url"] is None
        assert ctx["email_brand_name"] is None

    def test_logo_url_needs_public_media_url(self, settings, org_a):
        settings.PUBLIC_MEDIA_URL = ""
        org_a.logo = "org_logos/x.png"
        assert logo_url_for_email(org_a) is None
        settings.PUBLIC_MEDIA_URL = "https://media-crm.example.com"
        assert (
            logo_url_for_email(org_a)
            == "https://media-crm.example.com/media/org_logos/x.png"
        )
