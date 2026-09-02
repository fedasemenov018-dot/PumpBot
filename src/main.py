import logging
import os
import sqlite3
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Константы для состояний ConversationHandler
LOG_EXERCISE, LOG_WEIGHT, LOG_REPS, LOG_SETS, GOAL_INPUT = range(5)

# Мотивирующие цитаты известных спортсменов
MOTIVATION_QUOTES = [
    "Нет боли, нет отличных результатов. — Арнольд Шварценеггер",
    "Чемпион - это не тот, кто выигрывает один раз, а тот, кто продолжает пытаться. — Мухаммед Али",
    "Я отдаю все от себя каждый день. Это всё, что ты можешь делать. — Роджер Федерер",
    "Слабости не существует, существует лишь отсутствие воли. — Двейн Джонсон",
    "Успех - это результат подготовки, тяжёлой работы и изучения ошибок. — Колин Каперник",
    "Ты сильнее, чем кажешься. Продолжай тренироваться. — Крис Хемсворт",
    "Каждый чемпион когда-то был просто человеком, который отказался сдаваться. — Шайа Лабаф",
    "Не считай дни, делай дни в счёт. — Мухаммед Али",
    "Боль - это слабость, покидающая тело. — Грег Платон",
    "Если ты этого хочешь, ты найдёшь способ. Если нет, ты найдёшь причину. — Дуэйн Джонсон"
]

# Инициализация БД
def init_db():
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    
    # Таблица тренировок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise TEXT NOT NULL,
            weight REAL NOT NULL,
            reps INTEGER NOT NULL,
            sets INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица целей пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            goal TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    ''')
    
    # Таблица профилей пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Сохранение профиля пользователя
def save_user_profile(user_id, first_name, last_name=None):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_profiles (user_id, first_name, last_name)
        VALUES (?, ?, ?)
    ''', (user_id, first_name, last_name))
    conn.commit()
    conn.close()

# Сохранение тренировки
def save_workout(user_id, exercise, weight, reps, sets):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO workouts (user_id, exercise, weight, reps, sets)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, exercise, weight, reps, sets))
    conn.commit()
    conn.close()

# Получение последних 5 тренировок
def get_last_workouts(user_id, limit=5):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT exercise, weight, reps, sets, date
        FROM workouts
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT ?
    ''', (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results

# Получение прогресса по упражнениям
def get_exercise_progress(user_id):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT exercise, MAX(weight) as max_weight, COUNT(*) as total_times
        FROM workouts
        WHERE user_id = ?
        GROUP BY exercise
        ORDER BY max_weight DESC
    ''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results

# Сохранение цели
def save_goal(user_id, goal):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO goals (user_id, goal)
        VALUES (?, ?)
    ''', (user_id, goal))
    conn.commit()
    conn.close()

# Получение цели пользователя
def get_goal(user_id):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT goal FROM goals WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Получение информации пользователя
def get_user_name(user_id):
    conn = sqlite3.connect('pumpbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT first_name FROM user_profiles WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Спортсмен"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_profile(user.id, user.first_name, user.last_name)
    
    keyboard = [
        [InlineKeyboardButton("🏋️ Записать тренировку", callback_data="log")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔥 Мотивация", callback_data="motivation")],
        [InlineKeyboardButton("🎯 Моя цель", callback_data="goal")],
        [InlineKeyboardButton("💪 План на сегодня", callback_data="plan")],
    ]
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\nЭто PumpBot — твой фитнес-коуч.\nДавай начнём тренировку!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_name = get_user_name(user_id)
    data = query.data
    
    if data == "log":
        await query.edit_message_text(f"🏋️ {user_name}, введи название упражнения:")
        return LOG_EXERCISE
    
    elif data == "stats":
        last_workouts = get_last_workouts(user_id)
        progress = get_exercise_progress(user_id)
        
        if not last_workouts:
            stats_text = "📊 Статистика пока пуста. Запиши первую тренировку!"
        else:
            stats_text = f"📊 Статистика {user_name}:\n\n🏋️ Последние 5 тренировок:\n"
            for exercise, weight, reps, sets, date in last_workouts:
                stats_text += f"• {exercise}: {weight}кг × {reps} × {sets} подходов ({date[:10]})\n"
            
            stats_text += f"\n📈 Прогресс по упражнениям:\n"
            for exercise, max_weight, total_times in progress:
                stats_text += f"• {exercise}: макс {max_weight}кг ({total_times} раз)\n"
        
        goal = get_goal(user_id)
        if goal:
            stats_text += f"\n🎯 Твоя цель: {goal}"
        
        await query.edit_message_text(stats_text)
    
    elif data == "motivation":
        quote = random.choice(MOTIVATION_QUOTES)
        await query.edit_message_text(f"🔥 {quote}\n\nТы можешь это сделать, {user_name}! 💪")
    
    elif data == "goal":
        await query.edit_message_text(f"🎯 {user_name}, введи свою цель (например: набрать 10кг мышц за 3 месяца):")
        return GOAL_INPUT
    
    elif data == "plan":
        await query.edit_message_text(f"💪 План на сегодня, {user_name}:\n1. Приседания 3x10\n2. Отжимания 3x15\n3. Выпады 3x12\n4. Жим лежа 4x8")

async def handle_exercise_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['exercise'] = update.message.text
    user_name = get_user_name(user_id)
    
    await update.message.reply_text(f"Введи вес (в кг), {user_name}:")
    return LOG_WEIGHT

async def handle_weight_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['weight'] = float(update.message.text)
        user_name = get_user_name(update.effective_user.id)
        await update.message.reply_text(f"Введи количество повторений, {user_name}:")
        return LOG_REPS
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи число (например: 80.5)")
        return LOG_WEIGHT

async def handle_reps_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['reps'] = int(update.message.text)
        user_name = get_user_name(update.effective_user.id)
        await update.message.reply_text(f"Введи количество подходов, {user_name}:")
        return LOG_SETS
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи целое число (например: 10)")
        return LOG_REPS

async def handle_sets_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['sets'] = int(update.message.text)
        user_id = update.effective_user.id
        user_name = get_user_name(user_id)
        
        # Сохраняем тренировку
        save_workout(
            user_id,
            context.user_data['exercise'],
            context.user_data['weight'],
            context.user_data['reps'],
            context.user_data['sets']
        )
        
        # Проверяем цель
        goal = get_goal(user_id)
        goal_text = f"\n🎯 Не забудь про цель: {goal}" if goal else ""
        
        message_text = f"✅ Записано, {user_name}!\n{context.user_data['exercise']}: {context.user_data['weight']}кг × {context.user_data['reps']} × {context.user_data['sets']} подходов{goal_text}\nПродолжай тренироваться! 💪"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Ещё одно упражнение", callback_data="log")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("🔥 Мотивация", callback_data="motivation")],
        ]
        
        await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введи целое число (например: 3)")
        return LOG_SETS

async def handle_goal_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    goal = update.message.text
    save_goal(user_id, goal)
    user_name = get_user_name(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🔄 Вернуться в меню", callback_data="plan")],
    ]
    
    await update.message.reply_text(
        f"✅ Отлично, {user_name}! Твоя цель: {goal}\n\nМы будем вспоминать о ней после каждой тренировки! 🎯",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена. Используй /start для меню.")
    return ConversationHandler.END

async def main():
    # Инициализируем базу данных
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ConversationHandler для логирования тренировок
    conv_handler_log = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^log$")],
        states={
            LOG_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_exercise_input)],
            LOG_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight_input)],
            LOG_REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reps_input)],
            LOG_SETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sets_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # ConversationHandler для ввода цели
    conv_handler_goal = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^goal$")],
        states={
            GOAL_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_goal_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler_log)
    app.add_handler(conv_handler_goal)
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 PumpBot запущен и работает!")
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(main())
