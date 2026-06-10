from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class MemoAction(CallbackData, prefix="memo"):
    action: str  # "done" | "snooze" | "letgo" | "undo"
    memo_id: int


def memo_keyboard(memo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✓ Done", callback_data=MemoAction(action="done", memo_id=memo_id).pack()),
                InlineKeyboardButton(text="💤 Snooze", callback_data=MemoAction(action="snooze", memo_id=memo_id).pack()),
                InlineKeyboardButton(text="🗑 Let go", callback_data=MemoAction(action="letgo", memo_id=memo_id).pack()),
            ]
        ]
    )


def undo_keyboard(memo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Undo", callback_data=MemoAction(action="undo", memo_id=memo_id).pack())]
        ]
    )
