from types import SimpleNamespace

from bot.handlers import _get_forward_sender


def _user(first_name, last_name=None):
    return SimpleNamespace(first_name=first_name, last_name=last_name)


def test_forward_sender_user_first_name_only():
    origin = SimpleNamespace(sender_user=_user("Alice"))
    assert _get_forward_sender(origin) == "Alice"


def test_forward_sender_user_full_name():
    origin = SimpleNamespace(sender_user=_user("Alice", "Smith"))
    assert _get_forward_sender(origin) == "Alice Smith"


def test_forward_sender_username_fallback():
    origin = SimpleNamespace(sender_user=None, sender_user_name="alice_bot")
    assert _get_forward_sender(origin) == "alice_bot"


def test_forward_sender_chat_title_fallback():
    origin = SimpleNamespace(
        sender_user=None,
        sender_user_name=None,
        chat=SimpleNamespace(title="My Channel"),
    )
    assert _get_forward_sender(origin) == "My Channel"


def test_forward_sender_no_match_returns_none():
    origin = SimpleNamespace(sender_user=None, sender_user_name=None, chat=None)
    assert _get_forward_sender(origin) is None


def test_forward_sender_user_takes_priority_over_username():
    origin = SimpleNamespace(
        sender_user=_user("Alice"),
        sender_user_name="alice_bot",
    )
    assert _get_forward_sender(origin) == "Alice"
