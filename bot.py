
import os
import html
import logging
import threading

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = {
    int(os.getenv("ADMIN_ID", "0")),
    int(os.getenv("ADMIN_ID_2", "0")),
}

web = Flask(__name__)


@web.get("/")
def home():
    return "FELIKS RUSSIA POST BOT is running", 200


drafts = {}


def is_admin(user_id):
    return user_id in ADMIN_IDS and user_id != 0


def post_text(topic):
    return (
        "🎮 <b>FELIKS RUSSIA | НОВОСТИ</b>\n\n"
        f"📢 <b>{html.escape(topic.strip())}</b>\n\n"
        "Следите за новостями проекта и не пропускайте "
        "важные обновления!\n\n"
        "❤️ <b>FELIKS RUSSIA — играй вместе с нами!</b>"
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
        "👑 FELIKS RUSSIA | POST BOT\n\n"
        "1. Отправь фотографию.\n"
        "2. Следующим сообщением отправь тему.\n"
        "3. Проверь пост и нажми «Опубликовать»."
    )


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    drafts[user_id] = {"photo": update.message.photo[-1].file_id}
    await update.message.reply_text(
        "✅ Фото получено! Теперь отправь тему новости."
    )


async def receive_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    draft = drafts.get(user_id)
    if not draft or "photo" not in draft:
        await update.message.reply_text("Сначала отправь фотографию.")
        return

    topic = update.message.text.strip()
    if not topic:
        await update.message.reply_text("Напиши тему новости.")
        return

    draft["caption"] = post_text(topic)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Опубликовать", callback_data="publish")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")],
    ])

    await context.bot.send_photo(
        chat_id=user_id,
        photo=draft["photo"],
        caption=draft["caption"],
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def handle_buttons(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
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

    if query.data != "publish":
        return

    draft = drafts.get(user_id)
    if not draft or "caption" not in draft:
        await query.edit_message_caption(
            caption="⚠️ Черновик не найден. Создай пост заново."
        )
        return

    if not CHANNEL_ID:
        await query.edit_message_caption(
            caption="⚠️ Не задан CHANNEL_ID."
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
            caption="✅ Пост опубликован в канале!"
        )
    except Exception:
        logging.exception("Ошибка публикации")
        await query.edit_message_caption(
            caption="❌ Ошибка публикации. Проверь CHANNEL_ID "
                    "и права бота в канале."
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

    port = int(os.environ.get("PORT", "10000"))
    threading.Thread(
        target=lambda: web.run(
            host="0.0.0.0", port=port, use_reloader=False
        ),
        daemon=True,
    ).start()

    app.run_polling()


if __name__ == "__main__":
    main()
    
        
