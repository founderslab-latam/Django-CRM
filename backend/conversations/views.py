"""Authenticated read API for the CRM UI: which Chatwoot conversations belong
to a given Contact or Lead, so a panel on their detail page can list them and
link into Chatwoot's own agent dashboard.

No SSO between BottleCRM and Chatwoot exists yet -- an agent opening
`embed_url` (see `conversations/serializer.py`) needs to already be signed in
to Chatwoot in that browser. Wiring real single sign-on (Chatwoot's Platform
API can mint a one-time login link for an agent) is a follow-up, not
blocking: agents already have Chatwoot accounts during this phase, and a
second login once per browser session is a one-time cost, not a per-visit one.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import HasOrgContext

from .models import ChatwootConversation
from .serializer import ChatwootConversationSerializer


class ChatwootConversationListView(APIView):
    """`GET /api/conversations/chatwoot/?contact=<id>` or `?lead=<id>`.

    Exactly one of the two is required. Both resolve against the caller's
    own org only -- an id from another tenant answers the same empty list a
    nonexistent id would, rather than a 404 that would confirm whose id
    space it belongs to (consistent with `common.lookups.get_scoped_or_404`'s
    reasoning, applied here as a filter instead of a lookup since there is no
    single object to 404 against).
    """

    permission_classes = (IsAuthenticated, HasOrgContext)

    @extend_schema(
        tags=["conversations"],
        responses={200: ChatwootConversationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        org = request.profile.org
        contact_id = request.query_params.get("contact")
        lead_id = request.query_params.get("lead")

        if bool(contact_id) == bool(lead_id):
            return Response(
                {"detail": "Pass exactly one of ?contact= or ?lead=."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if contact_id:
            queryset = ChatwootConversation.objects.filter(
                org=org, contact_id=contact_id, contact__org=org
            )
        else:
            queryset = ChatwootConversation.objects.filter(
                org=org, lead_id=lead_id, lead__org=org
            )

        queryset = queryset.select_related("chatwoot_account").order_by("-created_at")
        return Response(ChatwootConversationSerializer(queryset, many=True).data)
