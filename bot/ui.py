"""Чистый чат: на экране всегда один «экран» бота, старые сообщения убираются."""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

# chat_id -> id последнего сообщения бота (текущий экран)
_last_screen: dict[int, int] = {}


def remember(message: Message) -> None:
    """Запоминает сообщение как текущий экран чата."""
    _last_screen[message.chat.id] = message.message_id


async def safe_delete(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass  # уже удалено или слишком старое


async def replace_screen(
    message: Message, text: str, markup: InlineKeyboardMarkup | None = None
) -> Message:
    """Показывает экран на месте текущего сообщения (без нового в чате)."""
    if not message.photo:
        try:
            await message.edit_text(text, reply_markup=markup)
            remember(message)
            return message
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return message
    # Сообщение с картинкой нельзя превратить в текст: шлём новое, старое удаляем
    new = await message.answer(text, reply_markup=markup)
    await safe_delete(message)
    remember(new)
    return new


async def new_screen(
    message: Message,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    *,
    delete_user_message: bool = False,
) -> Message:
    """Новое сообщение-экран. Прошлый экран бота удаляется,
    при желании удаляется и команда пользователя (/start и т. п.)."""
    chat_id = message.chat.id
    old_id = _last_screen.get(chat_id)
    new = await message.answer(text, reply_markup=markup)
    if old_id and old_id != new.message_id:
        try:
            await message.bot.delete_message(chat_id, old_id)
        except TelegramBadRequest:
            pass
    if delete_user_message:
        await safe_delete(message)
    remember(new)
    return new