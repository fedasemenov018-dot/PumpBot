import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

user_data = {}

def start(update, context):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🏋️ Записать тренировку", callback_data="log")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("💪 План на сегодня", callback_data="plan")],
        [InlineKeyboardButton("🤖 Совет", callback_data="tip")]
    ]
    update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nЭто PumpBot — твой фитнес-коуч.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "log":
        query.edit_message_text("🏋️ Введи упражнение, вес, повторения через пробел\nНапример: Приседания 100 10")
        user_data[query.from_user.id] = {"step": "log"}
    elif data == "stats":
        query.edit_message_text("📊 Тут будет твоя статистика (в разработке)")
    elif data == "plan":
        query.edit_message_text("💪 План на сегодня:\n1. Приседания 3x10\n2. Отжимания 3x15\n3. Выпады 3x12")
    elif data == "tip":
        query.edit_message_text("🤖 Напиши упражнение, по которому нужен совет")
        user_data[query.from_user.id] = {"step": "tip"}

def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id in user_data and user_data[user_id].get("step") == "log":
        parts = text.split()
        if len(parts) == 3:
            exercise, weight, reps = parts
            update.message.reply_text(f"✅ Записано: {exercise}, {weight}кг, {reps} раз\nПродолжай в том же духе! 💪")
            del user_data[user_id]
        else:
            update.message.reply_text("Введи в формате: Упражнение Вес Повторения")
    elif user_id in user_data and user_data[user_id].get("step") == "tip":
        update.message.reply_text(f"🤖 Совет по {text}: держи спину прямо и дыши правильно! 💪")
        del user_data[user_id]
    else:
        update.message.reply_text("Нажми /start")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    print("🚀 PumpBot запущен и работает!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
