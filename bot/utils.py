from aiogram import Bot

from bot.keyboards import memo_keyboard
from db.models import Memo


async def send_memo(bot: Bot, chat_id: int, memo: Memo, show_sender: bool = True) -> None:
    if memo.text.startswith("voice:") and memo.chat_id and memo.message_id:
        caption = f"(from {memo.sender_name})" if memo.sender_name and show_sender else None
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=memo.chat_id,
            message_id=memo.message_id,
            caption=caption,
            reply_markup=memo_keyboard(memo.id),
        )
    else:
        header = f"[{memo.id}]"
        if memo.sender_name and show_sender:
            header += f" (from {memo.sender_name})"
        await bot.send_message(chat_id, f"{header}\n{memo.text}", reply_markup=memo_keyboard(memo.id))
