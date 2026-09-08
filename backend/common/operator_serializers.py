"""Serializers for the superuser operator console (`/api/operator/`)."""

from django.conf import settings
from rest_framework import serializers

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
