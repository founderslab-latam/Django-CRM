"""Serializers for the superuser operator console (`/api/operator/`)."""

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from common.custom_domains import normalize_host, validate_custom_domain
from common.models import Org
from common.validators import validate_org_subdomain


def _cname_target(org):
    base = getattr(settings, "TENANT_BASE_DOMAIN", "crm.founderslab.cloud")
    return f"{org.routing_key}.{base}"


class OperatorOrgSerializer(serializers.ModelSerializer):
    """Read + edit view of an org for the operator. Lifecycle is changed
    through the dedicated action endpoints, not here."""

    cname_target = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Org
        fields = (
            "id",
            "name",
            "status",
            "status_reason",
            "deleted_at",
            "subdomain",
            "routing_key",
            "cname_target",
            "custom_domain",
            "custom_domain_verified_at",
            "default_currency",
            "default_country",
            "member_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "status",
            "status_reason",
            "deleted_at",
            "routing_key",
            "cname_target",
            "custom_domain_verified_at",
            "member_count",
            "created_at",
        )

    def get_cname_target(self, obj):
        return _cname_target(obj)

    def get_member_count(self, obj):
        return obj.profiles.filter(is_active=True, is_operator_access=False).count()

    def validate_subdomain(self, value):
        value = (value or "").strip().lower()
        if not value:
            return ""
        validate_org_subdomain(value)
        clash = Org.objects.filter(subdomain__iexact=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("That subdomain is already taken.")
        return value

    def validate_custom_domain(self, value):
        value = normalize_host(value)
        if not value:
            return ""
        try:
            validate_custom_domain(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        clash = Org.objects.filter(custom_domain=value)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                "That domain is already assigned to another organization."
            )
        return value

    def update(self, instance, validated_data):
        # A new domain hasn't been shown to point here yet: drop the
        # verification so it isn't routed (or put in links) until checked.
        if (
            "custom_domain" in validated_data
            and validated_data["custom_domain"] != instance.custom_domain
        ):
            instance.custom_domain_verified_at = None
        return super().update(instance, validated_data)


class OperatorOrgCreateSerializer(serializers.ModelSerializer):
    """Create a tenant. `admin_email`, if given, is invited as the org's first
    ADMIN via a magic link; the operator does not become a member."""

    name = serializers.CharField(max_length=100)
    admin_email = serializers.EmailField(
        required=False, allow_blank=True, write_only=True
    )

    class Meta:
        model = Org
        fields = (
            "name",
            "default_currency",
            "default_country",
            "subdomain",
            "admin_email",
        )

    validate_subdomain = OperatorOrgSerializer.validate_subdomain
