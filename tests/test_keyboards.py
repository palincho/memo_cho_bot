from bot.keyboards import MemoAction, memo_keyboard, undo_keyboard


def test_memo_action_pack_unpack_roundtrip():
    for action in ("done", "snooze", "letgo", "undo"):
        packed = MemoAction(action=action, memo_id=42).pack()
        unpacked = MemoAction.unpack(packed)
        assert unpacked.action == action
        assert unpacked.memo_id == 42


def test_memo_keyboard_contains_all_three_actions():
    kb = memo_keyboard(7)
    buttons = kb.inline_keyboard[0]
    assert len(buttons) == 3
    actions = {MemoAction.unpack(b.callback_data).action for b in buttons}
    assert actions == {"done", "snooze", "letgo"}


def test_memo_keyboard_encodes_correct_memo_id():
    kb = memo_keyboard(99)
    for button in kb.inline_keyboard[0]:
        assert MemoAction.unpack(button.callback_data).memo_id == 99


def test_undo_keyboard_action_and_memo_id():
    kb = undo_keyboard(3)
    button = kb.inline_keyboard[0][0]
    data = MemoAction.unpack(button.callback_data)
    assert data.action == "undo"
    assert data.memo_id == 3
