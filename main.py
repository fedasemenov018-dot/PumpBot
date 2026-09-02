import os
import asyncio
import threading
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Ошибка: TELEGRAM_BOT_TOKEN не найден в переменных окружения")
    exit(1)

print("🚀 Запуск PumpBot...")

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Используй кнопки меню или команду /start")


def _run_http_server_blocking():
    # Создаём отдельный event loop в потоке и запускаем web.run_app
    http_app = web.Application()
    http_app.router.add_get('/', lambda request: web.Response(text="OK"))
    web.run_app(http_app, host='0.0.0.0', port=int(os.getenv('PORT', 10000)))


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("Просто нажми /start")))
    
    # Запускаем HTTP-сервер в отдельном потоке — это гарантирует, что Render увидит открытый порт
    try:
        thread = threading.Thread(target=_run_http_server_blocking, daemon=True)
        thread.start()
        print("✅ HTTP-сервер запущен в отдельном потоке")
    except Exception as e:
        print(f"❌ Не удалось запустить HTTP-сервер в потоке: {e}")

    print("✅ PumpBot успешно запущен и слушает запросы!")
    app.run_polling()


if __name__ == "__main__":
    main()
