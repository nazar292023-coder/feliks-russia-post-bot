
import os
import html
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Данные ожидающей публикации
drafts = {}


def is_admin(user_id):
    return user_id == ADMIN_ID and ADMIN_ID != 0


def post_text(topic):
    safe_topic = html.escape(topic.strip())

    return (
        f"🎮 <b>FELIKS RUSSIA | НОВОСТИ</b>\n\n"
        f"📢 <b>{safe_topic}</b>\n\n"
        f"Следите за новостями проекта и не пропускайте "
        f"важные обновления!\n\n"
        f"❤️ <b>FELIKS RUSSIA — играй вместе с нами!</b>"
    )


def post_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🎮 Скачать игру — ПЕРЕЙТИ",
            url="https://t.me/crmp_feliksrussia/322"
        )],
        [InlineKeyboardButton(
            "‼️ Форум — ПЕРЕЙТИ",
            url="https://t.me/crmp_forum_cc"
        )],
        [InlineKeyboardButton(
            "📣 Беседа игроков — ВСТУПИТЬ",
            url="https://t.me/obhenieigrokov"
        )],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    await update.message.reply_text(
        "👑 <b>FELIKS RUSSIA | POST BOT</b>\n\n"
        "1. Отправь фотографию.\n"
        "2. Следующим сообщением напиши тему новости.\n"
        "3. Проверь готовый пост и нажми «Опубликовать».\n\n"
        "Публикация появится в канале после подтверждения.",
        parse_mode="HTML"
    )


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    drafts[update.effective_user.id] = {
        "photo": update.message.photo[-1].file_id
    }
    await update.message.reply_text(
        "✅ Фото получено!\nТеперь отправь тему новости одним сообщением."
    )


async def receive_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    if user_id not in drafts or "photo" not in drafts[user_id]:
        await update.message.reply_text(
            "Сначала отправь фотографию новости."
        )
        return

    topic = update.message.text.strip()
    if not topic:
        await update.message.reply_text("Напиши тему новости текстом.")
        return

    drafts[user_id]["caption"] = post_text(topic)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Опубликовать", callback_data="publish")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")],
    ])

    await context.bot.send_photo(
        chat_id=user_id,
        photo=drafts[user_id]["photo"],
        caption=drafts[user_id]["caption"],
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("Доступ запрещён.", show_alert=True)
        return

    await query.answer()

    if query.data == "cancel":
        drafts.pop(user_id, None)
        await query.edit_message_caption(caption="❌ Публикация отменена.")
        return

    if query.data == "publish":
        draft = drafts.get(user_id)

        if not draft or "caption" not in draft:
            await query.edit_message_caption(
                caption="⚠️ Черновик не найден. Создай пост заново."
            )
            return

        if not CHANNEL_ID:
            await query.edit_message_caption(
                caption="⚠️ Не настроен CHANNEL_ID в переменных окружения."
            )
            return

        try:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=draft["photo"],
                caption=draft["caption"],
                parse_mode="HTML",
                reply_markup=post_buttons(),
            )
            drafts.pop(user_id, None)
            await query.edit_message_caption(
                caption="✅ Пост успешно опубликован в канале!"
            )
        except Exception:
            logging.exception("Ошибка публикации")
            await query.edit_message_caption(
                caption="❌ Не удалось опубликовать пост. "
                        "Проверь CHANNEL_ID и права бота в канале."
            )


def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic)
    )
    app.run_polling()


if __name__ == "__main__":
    main()
                        
