from django.urls import path

from .views import ChatwootAccountView, ChatwootConversationListView

app_name = "conversations"

urlpatterns = [
    path(
        "chatwoot/",
        ChatwootConversationListView.as_view(),
        name="chatwoot_conversation_list",
    ),
    path(
        "account/",
        ChatwootAccountView.as_view(),
        name="chatwoot_account",
    ),
]
