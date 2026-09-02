import logging
import os
import sqlite3
import random
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_id INTEGER UNIQUE,
        name TEXT,
        goal TEXT,
        level TEXT,
        target TEXT,
        created_at DATETIME
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exercise TEXT,
        weight REAL,
        reps INTEGER,
        sets INTEGER,
        date DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exercise TEXT,
        max_weight REAL,
        date DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    conn.close()

def get_user(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(tg_id, name, goal, level):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (tg_id, name, goal, level, created_at) VALUES (?, ?, ?, ?, ?)",
              (tg_id, name, goal, level, datetime.now()))
    conn.commit()
    conn.close()

def update_target(tg_id, target):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET target = ? WHERE tg_id = ?", (target, tg_id))
    conn.commit()
    conn.close()

def save_workout(tg_id, exercise, weight, reps, sets):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    user = c.fetchone()
    if user:
        c.execute("INSERT INTO workouts (user_id, exercise, weight, reps, sets, date) VALUES (?, ?, ?, ?, ?, ?)",
                  (user[0], exercise, weight, reps, sets, datetime.now()))
        conn.commit()
        c.execute("SELECT max_weight FROM achievements WHERE user_id = ? AND exercise = ?", (user[0], exercise))
        ach = c.fetchone()
        if not ach or weight > ach[0]:
            c.execute("INSERT OR REPLACE INTO achievements (user_id, exercise, max_weight, date) VALUES (?, ?, ?, ?)",
                      (user[0], exercise, weight, datetime.now()))
            conn.commit()
    conn.close()

def get_stats(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return None
    c.execute("SELECT exercise, weight, reps, sets, date FROM workouts WHERE user_id = ? AND date >= datetime('now', '-7 days') ORDER BY date DESC",
              (user[0],))
    workouts = c.fetchall()
    conn.close()
    return workouts

def get_achievements(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    user = c.fetchone()
    if not user:
        conn.close()
        return None
    c.execute("SELECT exercise, max_weight FROM achievements WHERE user_id = ?", (user[0],))
    achievements = c.fetchall()
    conn.close()
    return achievements

# === КАРТИНКИ И GIF ===
GREETING_GIF = "https://media.giphy.com/media/3o7abKhOpu0N9HNGhO/giphy.gif"
MOTIVATION_GIFS = [
    "https://media.giphy.com/media/l0HlNQ3JjE1p1Qw5m/giphy.gif",
    "https://media.giphy.com/media/3o6Zt481isNVuQI1l6/giphy.gif",
    "https://media.giphy.com/media/l41lM3c3Q1yHr0fY4/giphy.gif",
    "https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif"
]
WORKOUT_IMAGES = {
    "приседания": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400",
    "жим": "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400",
    "планка": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400",
    "отжимания": "https://images.unsplash.com/photo-1526506118085-60ce8714f8c5?w=400",
    "тяга": "https://images.unsplash.com/photo-1581009146145-b5f8f3f0f0f0?w=400"
}
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1538805060514-97d9cc17730c?w=400"

# === МОТИВАЦИЯ ===
QUOTES = [
    "Ты не просто качаешь мышцы — ты качаешь характер. — Арнольд Шварценеггер",
    "Успех приходит к тем, кто не сдается. — Ронни Колман",
    "Лучшее время начать — сейчас. — Дориан Йейтс",
    "Боль — это слабость, покидающая тело. — Военная поговорка",
    "Каждый день выбирай: боль дисциплины или боль сожаления. — Эрик Томас",
    "Тренируйся как зверь, выгляди как кинозвезда. — Денис Синявский",
    "Если ты не прогрессируешь — ты регрессируешь. — Джей Катлер",
    "Путь в тысячу килограммов начинается с первого приседания. — Аноним",
    "Победа любит подготовку. — Александр Костин",
    "Ты способен на большее, чем думаешь. — Дэвид Гоггинс"
]

CHALLENGES = [
    "Сделай 100 отжиманий за день",
    "Приседай 50 раз без перерыва",
    "Планка 3 минуты за день",
    "10 берпи каждые 30 минут",
    "Пробеги 3 километра",
    "100 выпадов на каждую ногу",
    "Отжимания на кулаках 50 раз"
]

# === ИИ ПОМОЩНИК ===
def get_ai_response(prompt):
    if not OPENROUTER_API_KEY:
        return "Ключ OpenRouter не настроен. Обратитесь к администратору."
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dots-studio/dots-3-note-preview:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
        )
        data = response.json()
        if 'error' in data:
            return f"Ошибка API: {data['error'].get('message', 'Неизвестная ошибка')}"
        if 'choices' not in data or not data['choices']:
            return "ИИ вернул пустой ответ. Попробуйте позже."
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return f"Не удалось получить ответ от ИИ. Ошибка: {str(e)}"

# === БОТ ===
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    
    # Отправляем GIF-приветствие
    await update.message.reply_animation(GREETING_GIF, caption="🔥 Добро пожаловать в PumpBot!")
    
    if user:
        await show_main_menu(update, context, user)
    else:
        user_data[tg_id] = {"step": "goal"}
        keyboard = [
            [InlineKeyboardButton("🏋️ Набрать массу", callback_data="goal_mass")],
            [InlineKeyboardButton("🔥 Похудеть", callback_data="goal_lose")],
            [InlineKeyboardButton("💪 Поддержать форму", callback_data="goal_keep")]
        ]
        await update.message.reply_text(
            f"Привет, {update.effective_user.first_name}! 👋\nВыбери свою цель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_main_menu(update, context, user=None):
    tg_id = update.effective_user.id
    if not user:
        user = get_user(tg_id)
    keyboard = [
        [InlineKeyboardButton("🏋️ Записать тренировку", callback_data="log")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("💪 План на сегодня", callback_data="plan")],
        [InlineKeyboardButton("🤖 Совет", callback_data="tip")],
        [InlineKeyboardButton("🔥 Мотивация", callback_data="motivation")],
        [InlineKeyboardButton("🎯 Челлендж", callback_data="challenge")],
        [InlineKeyboardButton("🏆 Мои достижения", callback_data="achievements")],
        [InlineKeyboardButton("🎯 Поставить цель", callback_data="set_target")],
        [InlineKeyboardButton("📤 Поделиться прогрессом", callback_data="share_progress")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    text = f"🏋️ **Главное меню, {user[2] if user else 'друг'}!**\nЧто сегодня будем делать?"
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    data = query.data

    if data.startswith("goal_"):
        goal = data.replace("goal_", "")
        user_data[tg_id] = {"step": "level", "goal": goal}
        keyboard = [
            [InlineKeyboardButton("🟢 Новичок", callback_data="level_beginner")],
            [InlineKeyboardButton("🟡 Средний", callback_data="level_intermediate")],
            [InlineKeyboardButton("🔴 Продвинутый", callback_data="level_advanced")]
        ]
        await query.edit_message_text("Теперь выбери свой уровень:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("level_"):
        level = data.replace("level_", "")
        goal = user_data[tg_id]["goal"]
        add_user(tg_id, query.from_user.first_name, goal, level)
        del user_data[tg_id]
        user = get_user(tg_id)
        await show_main_menu(update, context, user)
        return

    if data == "log":
        user_data[tg_id] = {"step": "log_exercise"}
        await query.edit_message_text("🏋️ Введи название упражнения:")
        return

    if data == "stats":
        await show_stats(query, tg_id)
        return

    if data == "plan":
        await show_plan(query, tg_id)
        return

    if data == "tip":
        user_data[tg_id] = {"step": "tip"}
        await query.edit_message_text("🤖 Напиши упражнение, по которому нужен совет:")
        return

    if data == "motivation":
        await show_motivation(query)
        return

    if data == "challenge":
        challenge = random.choice(CHALLENGES)
        user_data[tg_id] = {"challenge": challenge}
        keyboard = [[InlineKeyboardButton("✅ Выполнил!", callback_data="challenge_done")]]
        await query.edit_message_text(f"🎯 Твой челлендж на сегодня:\n\n{challenge}",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "challenge_done":
        await query.edit_message_text("🔥 Круто! Ты выполнил челлендж! Продолжай в том же духе! 💪")
        return

    if data == "achievements":
        await show_achievements(query, tg_id)
        return

    if data == "set_target":
        user_data[tg_id] = {"step": "set_target"}
        await query.edit_message_text("🎯 Напиши свою цель (например: 'Присесть 150 кг за месяц'):")
        return

    if data == "share_progress":
        await share_progress(query, tg_id)
        return

    if data == "help":
        await query.edit_message_text(
            "❓ **Помощь**\n\n"
            "🏋️ Записать тренировку — сохрани упражнение, вес, повторения и подходы.\n"
            "📊 Статистика — показывает прогресс за неделю с графиком.\n"
            "💪 План на сегодня — ИИ составит тренировку под твою цель.\n"
            "🤖 Совет — спроси ИИ про технику упражнения (с картинкой).\n"
            "🔥 Мотивация — случайная цитата чемпиона + картинка.\n"
            "🎯 Челлендж — выполняй и становись сильнее.\n"
            "🏆 Мои достижения — все твои рекорды.\n"
            "🎯 Поставить цель — задай цель и бот будет напоминать.\n"
            "📤 Поделиться прогрессом — покажи друзьям свои успехи."
        )
        return

async def show_stats(query, tg_id):
    workouts = get_stats(tg_id)
    if not workouts:
        await query.edit_message_text("📊 У тебя пока нет тренировок. Запиши первую!")
        return
    
    text = "📊 **Твоя статистика за неделю:**\n\n"
    exercises = {}
    total_workouts = 0
    
    for w in workouts:
        name = w[0]
        if name not in exercises:
            exercises[name] = {"count": 0, "max_weight": 0, "total_weight": 0}
        exercises[name]["count"] += 1
        exercises[name]["total_weight"] += w[1]
        if w[1] > exercises[name]["max_weight"]:
            exercises[name]["max_weight"] = w[1]
        total_workouts += 1
    
    # Прогресс-бар
    if total_workouts > 0:
        progress = min(100, total_workouts * 10)
        bar = "▓" * (progress // 10) + "░" * (10 - progress // 10)
        text += f"🔥 **Прогресс:** {bar} {progress}%\n\n"
    
    for name, data in exercises.items():
        text += f"🏋️ **{name}:** {data['count']} тренировок, макс. вес {data['max_weight']} кг\n"
    
    await query.edit_message_text(text, parse_mode='Markdown')

async def show_achievements(query, tg_id):
    achievements = get_achievements(tg_id)
    if not achievements:
        await query.edit_message_text("🏆 У тебя пока нет достижений. Иди к рекордам! 💪")
        return
    
    text = "🏆 **Твои достижения:**\n\n"
    for ex, max_w in achievements:
        text += f"🏋️ **{ex}:** {max_w} кг (макс. вес)\n"
    
    await query.edit_message_text(text, parse_mode='Markdown')

async def show_plan(query, tg_id):
    user = get_user(tg_id)
    if not user:
        await query.edit_message_text("Сначала зарегистрируйся через /start")
        return
    
    goal = user[3]
    level = user[4]
    prompt = f"Составь план тренировки на сегодня для цели '{goal}', уровень '{level}'. Дай 5 упражнений с подходами и повторениями."
    plan = get_ai_response(prompt)
    await query.edit_message_text(f"💪 **Твой план на сегодня:**\n\n{plan}", parse_mode='Markdown')

async def show_motivation(query):
    quote = random.choice(QUOTES)
    gif = random.choice(MOTIVATION_GIFS)
    await query.edit_message_text(f"🔥 {quote}")
    await query.message.reply_animation(gif)

async def share_progress(query, tg_id):
    workouts = get_stats(tg_id)
    if not workouts:
        await query.edit_message_text("📤 У тебя пока нет тренировок, чтобы поделиться.")
        return
    
    text = "📤 **Мой прогресс за неделю:**\n\n"
    exercises = {}
    for w in workouts:
        name = w[0]
        if name not in exercises:
            exercises[name] = {"count": 0, "max_weight": 0}
        exercises[name]["count"] += 1
        if w[1] > exercises[name]["max_weight"]:
            exercises[name]["max_weight"] = w[1]
    
    for name, data in exercises.items():
        text += f"🏋️ **{name}:** {data['count']} тренировок, макс. вес {data['max_weight']} кг\n"
    
    text += "\n🔥 Продолжай качать железо! 💪"
    await query.edit_message_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_id = update.effective_user.id
    text = update.message.text.lower()

    if tg_id not in user_data:
        await update.message.reply_text("Нажми /start")
        return

    step = user_data[tg_id].get("step")

    if step == "log_exercise":
        user_data[tg_id]["exercise"] = text
        user_data[tg_id]["step"] = "log_weight"
        await update.message.reply_text("Введи вес (в кг):")
        return

    if step == "log_weight":
        try:
            user_data[tg_id]["weight"] = float(text.replace(",", "."))
            user_data[tg_id]["step"] = "log_reps"
            await update.message.reply_text("Введи количество повторений:")
        except:
            await update.message.reply_text("Введи число, например: 100")
        return

    if step == "log_reps":
        try:
            user_data[tg_id]["reps"] = int(text)
            user_data[tg_id]["step"] = "log_sets"
            await update.message.reply_text("Введи количество подходов:")
        except:
            await update.message.reply_text("Введи целое число")
        return

    if step == "log_sets":
        try:
            sets = int(text)
            exercise = user_data[tg_id]["exercise"]
            weight = user_data[tg_id]["weight"]
            reps = user_data[tg_id]["reps"]
            save_workout(tg_id, exercise, weight, reps, sets)
            del user_data[tg_id]
            
            # Отправляем мотивирующий GIF после тренировки
            gif = random.choice(MOTIVATION_GIFS)
            await update.message.reply_animation(
                gif,
                caption=f"✅ Записано: {exercise}, {weight}кг, {reps} раз, {sets} подходов\n\n🔥 Ты красавчик! Продолжай в том же духе! 💪"
            )
            user = get_user(tg_id)
            await show_main_menu(update, context, user)
        except:
            await update.message.reply_text("Ошибка. Попробуй снова.")

    if step == "tip":
        # Ищем картинку для упражнения
        image_url = DEFAULT_IMAGE
        for key in WORKOUT_IMAGES:
            if key in text:
                image_url = WORKOUT_IMAGES[key]
                break
        
        prompt = f"Дай совет по упражнению {text}. Как улучшить технику, безопасность, результат."
        tip = get_ai_response(prompt)
        await update.message.reply_photo(image_url, caption=f"🤖 **Совет по {text}:**\n\n{tip}", parse_mode='Markdown')
        del user_data[tg_id]

    if step == "set_target":
        update_target(tg_id, text)
        del user_data[tg_id]
        await update.message.reply_text(f"🎯 Цель установлена: {text}\n\nБот будет напоминать о ней каждый день! 💪")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 PumpBot ULTIMATE запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()