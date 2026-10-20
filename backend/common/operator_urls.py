from django.urls import path

from common.views.operator_views import (
    OperatorOrgDeleteView,
    OperatorOrgDetailView,
    OperatorOrgListCreateView,
    OperatorOrgReactivateView,
    OperatorOrgSuspendView,
    OperatorOrgVerifyDomainView,
)

app_name = "api_operator"

urlpatterns = [
    path("orgs/", OperatorOrgListCreateView.as_view(), name="org_list"),
    path("orgs/<uid:pk>/", OperatorOrgDetailView.as_view(), name="org_detail"),
    path("orgs/<uid:pk>/suspend/", OperatorOrgSuspendView.as_view(), name="org_suspend"),
    path("orgs/<uid:pk>/delete/", OperatorOrgDeleteView.as_view(), name="org_delete"),
    path(
        "orgs/<uid:pk>/verify-domain/",
        OperatorOrgVerifyDomainView.as_view(),
        name="org_verify_domain",
    ),
    # Reactivate a suspended org OR restore a deleted one.
    path(
        "orgs/<uid:pk>/reactivate/",
        OperatorOrgReactivateView.as_view(),
        name="org_reactivate",
    ),
    path(
        "orgs/<uid:pk>/restore/",
        OperatorOrgReactivateView.as_view(),
        name="org_restore",
    ),
]
