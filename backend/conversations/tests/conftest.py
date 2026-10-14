import pytest

from conversations.models import ChatwootAccount


@pytest.fixture
def chatwoot_account(org_a):
    return ChatwootAccount.objects.create(
        org=org_a,
        base_url="https://chat.example.com",
        account_id=7,
        seat_limit=3,
    )


@pytest.fixture
def chatwoot_account_b(org_b):
    return ChatwootAccount.objects.create(
        org=org_b,
        base_url="https://chat.example.com",
        account_id=9,
        seat_limit=1,
    )
