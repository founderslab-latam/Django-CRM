from django.urls import path

from .webhook_views import ChatwootWebhookView

app_name = "public_conversations"

urlpatterns = [
    path(
        "chatwoot/<str:webhook_token>/",
        ChatwootWebhookView.as_view(),
        name="chatwoot_webhook",
    ),
]
