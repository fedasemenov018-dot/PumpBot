import logging
import os
import sqlite3
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# === ВИДЕО ИЗ TELEGRAM-КАНАЛА ===
TREN_VIDEOS = {
    "workout": "https://t.me/fpfpldf/10?embed=1",
    "food": "https://t.me/fpfpldf/11?embed=1",
    "challenge": "https://t.me/fpfpldf/12?embed=1"
}

async def send_tren_video(update, video_type, caption):
    video_link = TREN_VIDEOS.get(video_type)
    if video_link:
        await update.message.reply_video(
            video=video_link,
            caption=caption,
            supports_streaming=True
        )
    else:
        await update.message.reply_text(caption)

# === РАСШИРЕННАЯ БАЗА ПРОДУКТОВ ===
FOOD_DB = {
    "курица": 165, "куриная грудка": 165, "куриное филе": 110, "куриная ножка": 180,
    "куриная кожа": 450, "говядина": 250, "говяжий фарш": 270, "свинина": 320,
    "свиной фарш": 340, "баранина": 280, "индейка": 130, "утка": 350,
    "кролик": 156, "конина": 150, "оленина": 160, "перепел": 170,
    "печень": 130, "куриная печень": 140, "говяжья печень": 130, "сердце": 160,
    "лосось": 200, "семга": 200, "тунец": 130, "скумбрия": 180,
    "сельдь": 160, "треска": 75, "минтай": 70, "окунь": 120,
    "щука": 90, "судак": 85, "лещ": 110, "карась": 85,
    "карп": 100, "форель": 150, "горбуша": 140, "кижуч": 140,
    "креветки": 90, "кальмар": 100, "мидии": 80, "устрицы": 85,
    "осьминог": 85, "краб": 90, "раки": 80, "морской гребешок": 95,
    "яйцо": 155, "яйца": 155, "яичный белок": 45, "яичный желток": 320,
    "молоко": 60, "кефир": 50, "ряженка": 55, "йогурт": 60,
    "творог": 120, "творог обезжиренный": 80, "творог 5%": 130,
    "сметана": 200, "сметана 15%": 150, "сливки": 300, "сливки 10%": 120,
    "сыр": 350, "пармезан": 400, "моцарелла": 300, "фета": 260,
    "бри": 330, "камамбер": 340, "чеддер": 380, "гауда": 350,
    "масло сливочное": 750, "маргарин": 720, "спред": 500,
    "рис": 130, "рис бурый": 110, "рис дикий": 100, "гречка": 110,
    "овсянка": 80, "геркулес": 85, "манка": 120, "перловка": 130,
    "пшено": 140, "кукурузная крупа": 150, "ячневая": 130,
    "макароны": 130, "вермишель": 130, "спагетти": 130, "лапша": 140,
    "хлеб": 250, "хлеб черный": 200, "батон": 260, "сухари": 350,
    "багет": 280, "лаваш": 270, "лепешка": 250,
    "картофель": 80, "батат": 90, "морковь": 35, "свекла": 43,
    "лук": 40, "чеснок": 149, "помидор": 18, "огурец": 15,
    "перец": 26, "перец болгарский": 26, "кабачок": 17, "тыква": 26,
    "брокколи": 34, "цветная капуста": 25, "капуста": 28, "пекинская капуста": 16,
    "сельдерей": 16, "спаржа": 20, "горошек": 80, "кукуруза": 100,
    "редис": 16, "репа": 30, "брюква": 35, "редиска": 20,
    "кинза": 25, "петрушка": 45, "укроп": 40, "салат": 15,
    "шпинат": 23, "щавель": 22, "рукола": 25,
    "банан": 90, "яблоко": 52, "груша": 57, "апельсин": 47,
    "мандарин": 38, "лимон": 34, "грейпфрут": 35, "помело": 38,
    "виноград": 65, "арбуз": 30, "дыня": 35, "персик": 45,
    "абрикос": 48, "слива": 42, "вишня": 50, "черешня": 52,
    "клубника": 32, "малина": 42, "черника": 44, "клюква": 46,
    "ежевика": 43, "голубика": 40, "смородина": 45, "крыжовник": 44,
    "хурма": 65, "киви": 48, "манго": 60, "папайя": 45,
    "ананас": 50, "гранат": 70, "инжир": 75, "финики": 280,
    "орехи": 600, "грецкий орех": 650, "миндаль": 600,
    "арахис": 550, "кедровый орех": 650, "фундук": 650,
    "кешью": 570, "фисташки": 560, "семечки": 580,
    "изюм": 300, "курага": 250, "чернослив": 230,
    "кокос": 350, "кокосовая стружка": 400,
    "майонез": 600, "кетчуп": 100, "горчица": 66, "соевый соус": 60,
    "оливковое масло": 900, "подсолнечное масло": 900, "кунжутное масло": 890,
    "соус песто": 500, "соус тартар": 400, "соевый майонез": 600,
    "бальзамический уксус": 88, "яблочный уксус": 21,
    "грибы": 22, "белые": 30, "шампиньоны": 20, "вешенки": 33,
    "лисички": 20, "опята": 22, "подберезовики": 25,
    "фасоль": 90, "чечевица": 110, "горох": 80, "нут": 130,
    "соевые бобы": 140, "маш": 130, "адзуки": 130,
    "сахар": 400, "мед": 320, "варенье": 250, "джем": 280,
    "шоколад": 550, "молочный шоколад": 550, "горький шоколад": 500,
    "печенье": 450, "пряники": 350, "ватрушка": 300, "булочка": 320,
    "пирожок": 280, "чебурек": 350, "беляш": 350,
    "кофе": 2, "чай": 1, "компот": 40, "сок": 50,
    "морс": 35, "квас": 30, "лимонад": 40,
    "протеин": 120, "гейнер": 350, "бца": 100,
    "тофу": 76, "соевое молоко": 40, "вода": 0, "соль": 0,
    "специи": 0, "перец черный": 0, "лавровый лист": 0,
    "бульон": 30, "суп": 50, "борщ": 60,
    "пельмени": 250, "вареники": 200, "манты": 280, "хинкали": 260,
}

def search_food(query):
    query = query.lower().strip()
    results = []
    for name, cal in FOOD_DB.items():
        if query in name:
            results.append((name, cal))
    return results[:10]

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
        cal_limit INTEGER DEFAULT 2500,
        created_at DATETIME
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exercise TEXT,
        weight REAL,
        reps INTEGER,
        sets INTEGER,
        status TEXT DEFAULT 'pending',
        date DATETIME
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        exercise TEXT,
        max_weight REAL,
        date DATETIME
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS food_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product TEXT,
        calories INTEGER,
        grams INTEGER,
        date DATETIME
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

def update_cal_limit(tg_id, limit):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("UPDATE users SET cal_limit = ? WHERE tg_id = ?", (limit, tg_id))
    conn.commit()
    conn.close()

def save_food(tg_id, product, calories, grams=100):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    user = c.fetchone()
    if user:
        c.execute("INSERT INTO food_log (user_id, product, calories, grams, date) VALUES (?, ?, ?, ?, ?)",
                  (user[0], product, calories * grams // 100, grams, datetime.now()))
        conn.commit()
    conn.close()

def get_food_today(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT SUM(calories) FROM food_log WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND date >= datetime('now', 'start of day')",
              (tg_id,))
    total = c.fetchone()[0]
    conn.close()
    return total or 0

def get_food_log(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT product, calories, grams FROM food_log WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND date >= datetime('now', 'start of day') ORDER BY date DESC",
              (tg_id,))
    foods = c.fetchall()
    conn.close()
    return foods

def save_workout(tg_id, exercise, weight, reps, sets, status='done'):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    user = c.fetchone()
    if user:
        c.execute("INSERT INTO workouts (user_id, exercise, weight, reps, sets, status, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (user[0], exercise, weight, reps, sets, status, datetime.now()))
        c.execute("SELECT max_weight FROM achievements WHERE user_id = ? AND exercise = ?", (user[0], exercise))
        ach = c.fetchone()
        if not ach or weight > ach[0]:
            c.execute("INSERT OR REPLACE INTO achievements (user_id, exercise, max_weight, date) VALUES (?, ?, ?, ?)",
                      (user[0], exercise, weight, datetime.now()))
        conn.commit()
    conn.close()

def get_today_workouts(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("""
        SELECT exercise, weight, reps, sets, status 
        FROM workouts 
        WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) 
        AND date >= datetime('now', 'start of day')
        ORDER BY date DESC
    """, (tg_id,))
    workouts = c.fetchall()
    conn.close()
    return workouts

def get_week_stats(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("""
        SELECT exercise, MAX(weight) 
        FROM workouts 
        WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) 
        AND date >= datetime('now', '-7 days')
        AND status = 'done'
        GROUP BY exercise
    """, (tg_id,))
    best = c.fetchall()
    conn.close()
    return best

def get_all_workouts(tg_id):
    conn = sqlite3.connect("pumpbot.db")
    c = conn.cursor()
    c.execute("""
        SELECT exercise, weight, reps, sets, status, date 
        FROM workouts 
        WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) 
        ORDER BY date DESC
        LIMIT 20
    """, (tg_id,))
    workouts = c.fetchall()
    conn.close()
    return workouts

# === МОТИВАЦИЯ ===
QUOTES = [
    "Ты не просто качаешь мышцы — ты качаешь характер. 💀",
    "Слабаки сдаются, а ты жмёшь до отказа. 👊",
    "Боль — это слабость, покидающая тело. 🔥",
    "Каждый день выбирай: боль дисциплины или боль сожаления. 💪",
    "Тренируйся как зверь, выгляди как кинозвезда. 🦍",
    "Если ты не прогрессируешь — ты регрессируешь. 🏆"
]

CHALLENGES = [
    "Сделай 100 отжиманий за день. 🥵",
    "Приседай 50 раз без перерыва. 💀",
    "Планка 3 минуты за день. 🫡",
    "10 берпи каждые 30 минут. 🔥",
    "Пробеги 3 километра. 😤",
    "100 выпадов на каждую ногу. 🦵"
]

# === БОТ ===
user_data = {}

async def start(update, context):
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    if user:
        await show_main_menu(update, context, user)
    else:
        user_data[tg_id] = {"step": "goal"}
        keyboard = [[InlineKeyboardButton("🏋️ Набрать массу", callback_data="goal_mass")],
                    [InlineKeyboardButton("🔥 Похудеть", callback_data="goal_lose")],
                    [InlineKeyboardButton("💪 Поддержать форму", callback_data="goal_keep")]]
        await update.message.reply_text(f"Йо, {update.effective_user.first_name}! 💪\nТреним? Выбери цель:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_main_menu(update, context, user=None):
    tg_id = update.effective_user.id
    if not user:
        user = get_user(tg_id)
    keyboard = [
        [InlineKeyboardButton("🏋️ Тренировка", callback_data="training")],
        [InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")],
        [InlineKeyboardButton("🍔 Питание", callback_data="calories")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    text = f"Чё качаем сегодня, {user[2] if user else 'бро'}? 💪"
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    tg_id = query.from_user.id
    data = query.data

    if data.startswith("goal_"):
        goal = data.replace("goal_", "")
        user_data[tg_id] = {"step": "level", "goal": goal}
        keyboard = [[InlineKeyboardButton("🟢 Новичок", callback_data="level_beginner")],
                    [InlineKeyboardButton("🟡 Средний", callback_data="level_intermediate")],
                    [InlineKeyboardButton("🔴 Продвинутый", callback_data="level_advanced")]]
        await query.edit_message_text("Теперь выбери уровень:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("level_"):
        level = data.replace("level_", "")
        goal = user_data[tg_id]["goal"]
        add_user(tg_id, query.from_user.first_name, goal, level)
        del user_data[tg_id]
        await show_main_menu(update, context, get_user(tg_id))
        return

    if data == "training":
        keyboard = [
            [InlineKeyboardButton("➕ Записать тренировку", callback_data="log")],
            [InlineKeyboardButton("💪 План на сегодня", callback_data="plan")],
            [InlineKeyboardButton("📋 Мои тренировки", callback_data="my_workouts")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        await query.edit_message_text("🏋️ **Тренировка:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    if data == "progress":
        await show_progress(query, tg_id)
        return

    if data == "log":
        user_data[tg_id] = {"step": "log_exercise"}
        await query.edit_message_text("Название упражнения:")
        return

    if data == "plan":
        await show_plan(query, tg_id)
        return

    if data == "my_workouts":
        await show_my_workouts(query, tg_id)
        return

    if data.startswith("plan_done_"):
        await handle_plan_action(query, tg_id, data, 'done')
        return

    if data.startswith("plan_fail_"):
        await handle_plan_action(query, tg_id, data, 'fail')
        return

    if data == "calories":
        await show_calories(query, tg_id)
        return

    if data == "log_food":
        user_data[tg_id] = {"step": "log_food"}
        await query.edit_message_text("Напиши продукт (например: курица, рис, яблоко):")
        return

    if data == "set_cal_limit":
        user_data[tg_id] = {"step": "set_cal_limit"}
        await query.edit_message_text("Введи дневной лимит калорий (например: 2500):")
        return

    if data.startswith("food_"):
        parts = data.split("_")
        if len(parts) >= 3:
            name = parts[1]
            cal = int(parts[2])
            user_data[tg_id] = {"step": "food_select", "product": name, "cal_per_100": cal}
            await query.edit_message_text(f"Введи вес в граммах (например: 150):")
        return

    if data == "help":
        keyboard = [
            [InlineKeyboardButton("📩 Написать в поддержку", url="https://t.me/Tehnoprofff")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
        ]
        await query.edit_message_text(
            "❓ **Помощь**\n\n"
            "🏋️ **Тренировка** — записать тренировку или посмотреть план.\n"
            "📊 **Мой прогресс** — статистика и рекорды.\n"
            "🍔 **Питание** — счетчик калорий.\n\n"
            "По всем вопросам пиши в поддержку:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return

    if data == "back_to_menu":
        await show_main_menu(update, context)

async def handle_plan_action(query, tg_id, data, action):
    parts = data.split("_")
    if len(parts) < 4:
        await query.edit_message_text("Ошибка. Попробуй снова.")
        return
    
    exercise = parts[2]
    weight = float(parts[3])
    reps = int(parts[4])
    
    save_workout(tg_id, exercise, weight, reps, 1, action)
    
    emoji = "✅" if action == 'done' else "❌"
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
    
    await query.edit_message_text(
        f"{emoji} {exercise}: {weight}кг × {reps} раз\n{'Выполнил!' if action == 'done' else 'Не выполнил!'}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    if action == 'done':
        await send_tren_video(query, "workout", "🔥 Тренируйся на максимум! 💀")

async def show_plan(query, tg_id):
    workouts = get_today_workouts(tg_id)
    
    if not workouts:
        await query.edit_message_text(
            "📋 Сегодня нет тренировок. Запиши первую, бро!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]])
        )
        return
    
    keyboard = []
    for i, (ex, weight, reps, sets, status) in enumerate(workouts):
        if status == 'pending':
            callback_done = f"plan_done_{ex}_{weight}_{reps}_{i}"
            callback_fail = f"plan_fail_{ex}_{weight}_{reps}_{i}"
            keyboard.append([
                InlineKeyboardButton(f"✅ {ex} — {weight}кг × {reps}", callback_data=callback_done),
                InlineKeyboardButton(f"❌ Пропустить", callback_data=callback_fail)
            ])
    
    if not keyboard:
        await query.edit_message_text(
            "✅ Ты уже отметил все упражнения на сегодня! Отдыхай, бро!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]])
        )
        return
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    
    await query.edit_message_text(
        "💪 **План на сегодня:**\n\n"
        "Нажми ✅ если выполнил, ❌ если не смог:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_my_workouts(query, tg_id):
    workouts = get_all_workouts(tg_id)
    if not workouts:
        await query.edit_message_text(
            "📋 Нет тренировок, бро!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]])
        )
        return
    
    text = "📋 **Твои тренировки:**\n\n"
    for i, (ex, weight, reps, sets, status, date) in enumerate(workouts, 1):
        status_text = "✅" if status == 'done' else "❌" if status == 'fail' else "⏳"
        date_str = date[:10] if date else ""
        text += f"{i}. {ex} — {weight}кг × {reps} × {sets} {status_text} [{date_str}]\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_progress(query, tg_id):
    today = get_today_workouts(tg_id)
    done = len([w for w in today if w[4] == 'done'])
    fail = len([w for w in today if w[4] == 'fail'])
    pending = len([w for w in today if w[4] == 'pending'])
    
    text = "📊 **Твой прогресс:**\n\n"
    text += f"✅ Выполнено: {done} упражнений\n"
    text += f"❌ Не выполнено: {fail} упражнений\n"
    text += f"⏳ Ожидают: {pending} упражнений\n\n"
    
    best = get_week_stats(tg_id)
    if best:
        text += "🏋️ **Лучшие результаты за неделю:**\n"
        for ex, weight in best:
            text += f"• {ex}: {weight} кг\n"
    else:
        text += "🏋️ Нет данных за неделю, бро."
    
    keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_calories(query, tg_id):
    user = get_user(tg_id)
    if not user:
        await query.edit_message_text("Сначала зарегистрируйся через /start")
        return
    
    limit = user[6] or 2500
    today = get_food_today(tg_id)
    remaining = limit - today
    
    progress = int((today / limit) * 100) if limit > 0 else 0
    bar = "▓" * (progress // 5) + "░" * (20 - progress // 5)
    
    text = f"🍔 **Калории:**\n\n"
    text += f"📊 {bar} {progress}%\n"
    text += f"🔥 Съедено: {today} ккал\n"
    text += f"💪 Лимит: {limit} ккал\n"
    text += f"⚡ Осталось: {remaining} ккал\n\n"
    
    foods = get_food_log(tg_id)
    if foods:
        text += "**Сегодня:**\n"
        for product, cal, grams in foods[:5]:
            text += f"• {product} — {cal} ккал ({grams}г)\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Записать еду", callback_data="log_food")],
        [InlineKeyboardButton("⚙️ Лимит", callback_data="set_cal_limit")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def handle_message(update, context):
    tg_id = update.effective_user.id
    text = update.message.text

    if tg_id not in user_data:
        await update.message.reply_text("Нажми /start, бро.")
        return

    step = user_data[tg_id].get("step")

    if step == "log_exercise":
        user_data[tg_id]["exercise"] = text
        user_data[tg_id]["step"] = "log_weight"
        await update.message.reply_text("Вес в кг:")
        return

    if step == "log_weight":
        try:
            user_data[tg_id]["weight"] = float(text.replace(",", "."))
            user_data[tg_id]["step"] = "log_reps"
            await update.message.reply_text("Повторения:")
        except:
            await update.message.reply_text("Введи число, бро.")
        return

    if step == "log_reps":
        try:
            user_data[tg_id]["reps"] = int(text)
            user_data[tg_id]["step"] = "log_sets"
            await update.message.reply_text("Подходы:")
        except:
            await update.message.reply_text("Целое число, бро.")
        return

    if step == "log_sets":
        try:
            sets = int(text)
            exercise = user_data[tg_id]["exercise"]
            weight = user_data[tg_id]["weight"]
            reps = user_data[tg_id]["reps"]
            save_workout(tg_id, exercise, weight, reps, sets, 'done')
            del user_data[tg_id]
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await update.message.reply_text(
                f"✅ {exercise}: {weight}кг × {reps} × {sets}\nКрасава, бро! 👊",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await send_tren_video(update, "workout", "🔥 Тренируйся на максимум! 💀")
        except Exception as e:
            logging.error(f"Error in log_sets: {e}")
            await update.message.reply_text("Ошибка, попробуй снова.")
        return

    if step == "log_food":
        results = search_food(text)
        if not results:
            await update.message.reply_text("❌ Продукт не найден. Попробуй ещё.")
            return
        keyboard = []
        for name, cal in results[:6]:
            keyboard.append([InlineKeyboardButton(f"{name} — {cal} ккал/100г", callback_data=f"food_{name}_{cal}")])
        keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")])
        user_data[tg_id] = {"step": "food_select"}
        await update.message.reply_text("Выбери продукт:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if step == "food_select":
        if "product" not in user_data[tg_id]:
            await update.message.reply_text("Сначала выбери продукт, бро.")
            return
        try:
            grams = int(text)
            product = user_data[tg_id]["product"]
            cal_per_100 = user_data[tg_id]["cal_per_100"]
            total_cal = cal_per_100 * grams // 100
            save_food(tg_id, product, total_cal, grams)
            del user_data[tg_id]
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await update.message.reply_text(
                f"✅ {product} — {total_cal} ккал ({grams}г)\nЖри, бро! 🍖",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await send_tren_video(update, "food", "🍖 Жри, бро! Это топливо для мышц!")
        except Exception as e:
            logging.error(f"Error in food_select: {e}")
            await update.message.reply_text("Введи число, бро.")
        return

    if step == "set_cal_limit":
        try:
            limit = int(text)
            update_cal_limit(tg_id, limit)
            del user_data[tg_id]
            keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]
            await update.message.reply_text(
                f"✅ Лимит: {limit} ккал/день",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            await update.message.reply_text("Введи число, бро.")
        return

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🚀 PumpBot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()