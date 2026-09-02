import os
import logging
import requests
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import telegram

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    exit(1)

# WEBHOOK_URL: берём из окружения или используем предоставленный вами URL
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://pumpbot-2.onrender.com")
PORT = int(os.getenv("PORT", 10000))

logging.info("🚀 Запуск PumpBot (webhook mode if WEBHOOK_URL задан)...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏋️ Тренировка", callback_data="log")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("💪 План", callback_data="plan")],
    ]
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}! 👋\nЯ PumpBot — твой фитнес-помощник.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "log":
        await query.edit_message_text("🏋️ Запиши тренировку в формате: Приседания 100 10")
    elif query.data == "stats":
        await query.edit_message_text("📊 Статистика появится после первой тренировки.")
    elif query.data == "plan":
        await query.edit_message_text("💪 План на сегодня:\n1. Приседания 3x10\n2. Отжимания 3x15")


def delete_webhook():
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook",
            data={"drop_pending_updates": True},
            timeout=10,
        )
        logging.info("deleteWebhook status: %s, body: %s", resp.status_code, resp.text)
        return resp.status_code == 200
    except Exception:
        logging.exception("Ошибка при вызове deleteWebhook")
        return False


def set_webhook(full_url):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            data={"url": full_url},
            timeout=10,
        )
        logging.info("setWebhook status: %s, body: %s", resp.status_code, resp.text)
        return resp.status_code == 200
    except Exception:
        logging.exception("Ошибка при вызове setWebhook")
        return False


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Просто нажми /start")))

    if WEBHOOK_URL:
        # path без слеша, используем идентификатор бота в качестве пути, чтобы он был уникален
        url_path = os.getenv("WEBHOOK_PATH", BOT_TOKEN.split(":")[0])
        webhook_full_url = f"{WEBHOOK_URL.rstrip('/')}/{url_path}"

        logging.info("Подготовка webhook: %s", webhook_full_url)

        # Не устанавливаем/удаляем webhook вручную здесь, PTB попытается сделать это безопасно.
        # Вместо этого — запускаем app.run_webhook в loop с обработкой RetryAfter и backoff.
        max_attempts = 6
        for attempt in range(1, max_attempts + 1):
            try:
                logging.info("Запуск webhook (попытка %d/%d)", attempt, max_attempts)
                app.run_webhook(listen="0.0.0.0", port=PORT, url_path=f"/{url_path}", webhook_url=webhook_full_url)
                logging.info("app.run_webhook завершился нормально")
                break
            except telegram.error.RetryAfter as e:
                wait = getattr(e, 'retry_after', 5)
                logging.warning("RetryAfter при setWebhook: жду %s сек и пробую снова", wait)
                time.sleep(wait + 1)
            except Exception:
                logging.exception("Ошибка при запуске webhook")
                if attempt < max_attempts:
                    delay = 5 * attempt
                    logging.info("Ждём %s сек перед новой попыткой", delay)
                    time.sleep(delay)
                else:
                    logging.error("Превышено число попыток при запуске webhook. Выход.")
                    raise
    else:
        logging.info("WEBHOOK_URL не задан — запускаем polling (fallback)")
        # fallback: polling (на случай, если WEBHOOK_URL отсутствует)
        delete_webhook()
        app.run_polling()


if __name__ == "__main__":
    main()
