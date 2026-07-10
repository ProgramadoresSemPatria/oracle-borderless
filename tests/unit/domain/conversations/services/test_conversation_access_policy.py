from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.services.conversation_access_policy import ConversationAccessPolicy
from src.support.core.exceptions import UnauthorizedDomainError


def _conv(user_email):
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    return Conversation(uuid4(), user_email, "T", now, now, None)


def test_denies_when_both_set_and_differ():
    with pytest.raises(UnauthorizedDomainError):
        ConversationAccessPolicy.assert_can_access(_conv("a@x.com"), "b@x.com")


@pytest.mark.parametrize("owner,requester", [("a@x.com", "a@x.com"), (None, "a@x.com"), ("a@x.com", None), (None, None)])
def test_allows_when_matching_or_any_null(owner, requester):
    ConversationAccessPolicy.assert_can_access(_conv(owner), requester)  # não levanta
