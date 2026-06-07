from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def memo_keyboard(memo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✓ Done", callback_data=f"done:{memo_id}"),
                InlineKeyboardButton(text="💤 Snooze", callback_data=f"snooze:{memo_id}"),
                InlineKeyboardButton(text="🗑 Let go", callback_data=f"letgo:{memo_id}"),
            ]
        ]
    )


def undo_keyboard(memo_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Undo", callback_data=f"undo:{memo_id}")]
        ]
    )
