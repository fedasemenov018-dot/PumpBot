import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Загрузка переменных окружения из .env
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🏋️ Записать тренировку", callback_data="log")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("💪 План на сегодня", callback_data="plan")],
        [InlineKeyboardButton("🤖 Совет", callback_data="tip")]
    ]
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nЭто PumpBot — твой фитнес-коуч.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопок"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "log":
        await query.edit_message_text("🏋️ Введи упражнение, вес, повторения через пробел\nНапример: Приседания 100 10")
        user_data[query.from_user.id] = {"step": "log"}
    elif data == "stats":
        await query.edit_message_text("📊 Тут будет твоя статистика (в разработке)")
    elif data == "plan":
        await query.edit_message_text("💪 План на сегодня:\n1. Приседания 3x10\n2. Отжимания 3x15\n3. Выпады 3x12")
    elif data == "tip":
        await query.edit_message_text("🤖 Напиши упражнение, по которому нужен совет")
        user_data[query.from_user.id] = {"step": "tip"}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id in user_data and user_data[user_id].get("step") == "log":
        parts = text.split()
        if len(parts) >= 3:
            exercise = parts[0]
            weight = parts[1]
            reps = parts[2]
            await update.message.reply_text(
                f"✅ Записано: {exercise}, {weight}кг, {reps} раз\nПродолжай в том же духе! 💪"
            )
            del user_data[user_id]
        else:
            await update.message.reply_text("Введи в формате: Упражнение Вес Повторения")
    elif user_id in user_data and user_data[user_id].get("step") == "tip":
        await update.message.reply_text(
            f"🤖 Совет по {text}: держи спину прямо и дыши правильно! 💪"
        )
        del user_data[user_id]
    else:
        await update.message.reply_text("Нажми /start")

def main() -> None:
    """Главная функция для запуска бота"""
    try:
        # Создание приложения с токеном
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Добавление обработчиков
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🚀 PumpBot запущен и работает!")
        
        # Запуск бота с polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        raise

if __name__ == "__main__":
    main()
