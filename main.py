import os
import threading
import time
import logging
import requests
import telegram
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    exit(1)

logging.info("🚀 Запуск PumpBot...")

async def health_check(request):
    return web.Response(text="OK")


def _run_http_server_blocking():
    try:
        http_app = web.Application()
        http_app.router.add_get('/', health_check)
        # handle_signals=False нужен для запуска в не‑главном потоке
        web.run_app(http_app, host='0.0.0.0', port=int(os.getenv('PORT', 10000)), handle_signals=False)
    except Exception:
        logging.exception("❌ Не удалось запустить HTTP-сервер")


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


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Просто нажми /start")))

    # Запускаем HTTP-сервер в отдельном потоке — Render увидит открытый порт
    thread = threading.Thread(target=_run_http_server_blocking, daemon=True)
    thread.start()
    logging.info("✅ HTTP-сервер запущен в отдельном потоке")

    # Попытка удалить webhook перед polling
    delete_webhook()

    # Запуск polling с повторными попытками при Conflict
    max_retries = 10
    base_delay = 5  # seconds
    for attempt in range(1, max_retries + 1):
        try:
            logging.info("Запуск polling (попытка %d/%d)", attempt, max_retries)
            app.run_polling()
            logging.info("app.run_polling завершился нормально")
            break
        except telegram.error.Conflict as e:
            logging.warning("Conflict при polling: %s", e)
            delete_webhook()
            if attempt < max_retries:
                delay = base_delay * attempt
                logging.info("Ждём %s сек перед новой попыткой", delay)
                time.sleep(delay)
            else:
                logging.error("Превышено число попыток при Conflict. Выход.")
                raise
        except Exception as e:
            logging.exception("Неожиданная ошибка при run_polling: %s", e)
            if attempt < max_retries:
                delay = base_delay * attempt
                logging.info("Ждём %s сек перед новой попыткой", delay)
                time.sleep(delay)
            else:
                logging.error("Превышено число попыток при ошибках. Выход.")
                raise


if __name__ == "__main__":
    main()
