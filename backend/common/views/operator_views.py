"""Superuser operator console: tenant (Org) administration.

Auth: `common.permissions.IsOperator` (a superuser, a superuser's PAT, or the
`X-Operator-Key` header). These endpoints are exempt from `RequireOrgContext`
in `common.middleware.rls_context` -- they operate across every org and carry
no tenant context of their own.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.audit_log import audit_log
from common.models import Org
from common.operator_invite import invite_org_admin
from common.operator_serializers import (
    OperatorOrgCreateSerializer,
    OperatorOrgSerializer,
)
from common.permissions import IsOperator

_VALID_STATUSES = {"ACTIVE", "SUSPENDED", "DELETED"}


class OperatorOrgListCreateView(APIView):
    permission_classes = (IsOperator,)

    def get(self, request):
        qs = Org.objects.all().order_by("-created_at")
        status_filter = (request.query_params.get("status") or "").upper()
        if status_filter in _VALID_STATUSES:
            qs = qs.filter(status=status_filter)
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(subdomain__icontains=search))
        return Response(
            {"organizations": OperatorOrgSerializer(qs, many=True).data}
        )

    def post(self, request):
        ser = OperatorOrgCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = dict(ser.validated_data)
        admin_email = (data.pop("admin_email", "") or "").strip()

        org = Org.objects.create(
            **{k: v for k, v in data.items() if v not in ("", None)}
        )
        audit_log.operator_org_provisioned(
            getattr(request, "user", None), org, request
        )

        invited = invite_org_admin(org, admin_email)
        return Response(
            {
                "organization": OperatorOrgSerializer(org).data,
                "admin_invited": invited,
            },
            status=status.HTTP_201_CREATED,
        )


class OperatorOrgDetailView(APIView):
    permission_classes = (IsOperator,)

    def get(self, request, pk):
        org = get_object_or_404(Org, pk=pk)
        return Response({"organization": OperatorOrgSerializer(org).data})

    def patch(self, request, pk):
        org = get_object_or_404(Org, pk=pk)
        ser = OperatorOrgSerializer(org, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"organization": OperatorOrgSerializer(org).data})


class _OrgStatusChangeView(APIView):
    """Shared body for suspend / delete / reactivate / restore."""

    permission_classes = (IsOperator,)
    target_status = "ACTIVE"

    def post(self, request, pk):
        org = get_object_or_404(Org, pk=pk)
        reason = (request.data.get("reason") or "").strip()[:255]

        org.status = self.target_status
        if self.target_status == "ACTIVE":
            org.status_reason = ""
            org.deleted_at = None
        else:
            org.status_reason = reason
            org.deleted_at = (
                timezone.now() if self.target_status == "DELETED" else org.deleted_at
            )
        org.save()

        audit_log.operator_org_status_changed(
            getattr(request, "user", None), org, self.target_status, reason, request
        )
        return Response({"organization": OperatorOrgSerializer(org).data})


class OperatorOrgSuspendView(_OrgStatusChangeView):
    target_status = "SUSPENDED"


class OperatorOrgDeleteView(_OrgStatusChangeView):
    target_status = "DELETED"


class OperatorOrgReactivateView(_OrgStatusChangeView):
    """Reactivate a suspended org, or restore a soft-deleted one -- both land
    on ACTIVE with the reason and deleted_at cleared."""

    target_status = "ACTIVE"
