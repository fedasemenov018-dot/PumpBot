import logging
import os
import sqlite3
import random
import asyncio
import datetime as dt
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

DATABASE_URL = os.getenv("DATABASE_URL")
USE_PG = DATABASE_URL is not None
if USE_PG:
    import psycopg2

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def get_conn():
    if USE_PG: return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect("pumpbot.db")

def adapt(q): return q.replace("?", "%s") if USE_PG else q
def today_clause(): return "date >= CURRENT_DATE" if USE_PG else "date >= datetime('now', 'start of day')"
def week_ago_clause(): return "date >= CURRENT_DATE - INTERVAL '7 days'" if USE_PG else "date >= datetime('now', '-7 days')"

# === МОТИВАЦИОННЫЕ ВИДЕО ===
MOTIVATION_VIDEOS = [
    "https://attachments-cdn-s.coub.com/coub_storage/coub/simple/cw_file/20d95255492/696ba9cdde3eeff69c1a7/muted_mp4_big_size_1597674723_muted_big.mp4",
    "https://attachments-cdn-s.coub.com/coub_storage/coub/simple/cw_file/0e5db8ec074/bb1e23c8fa43d455fc8f4/muted_mp4_big_size_1630863913_muted_big.mp4",
    "https://attachments-cdn-s.coub.com/coub_storage/coub/simple/cw_file/903d7ac0494/6809c40fd3b509bafa34b/muted_mp4_big_size_1568241904_muted_big.mp4",
    "https://attachments-cdn-s.coub.com/coub_storage/coub/simple/cw_file/103ca6f8f1b/1b559a5da852621e54897/muted_mp4_big_size_1574588619_muted_big.mp4",
    "https://attachments-cdn-s.coub.com/coub_storage/coub/simple/cw_file/7bf94fd9ac0/cab3ff33057ce0f0c7e70/muted_mp4_big_size_1568106551_muted_big.mp4",
    "https://attachments-cdn-s.coub.com/coub_storage/coub/simple/cw_file/f9f13f5779c/9196195a4e51d97adc5dc/muted_mp4_big_size_1637359430_muted_big.mp4",
]

async def send_motivation_video(update, caption="🔥 Мотивация!"):
    video_url = random.choice(MOTIVATION_VIDEOS)
    try:
        await update.message.reply_video(video=video_url, caption=caption, supports_streaming=True)
    except Exception as e:
        logging.error(f"Motivation video error: {e}")
        await update.message.reply_text(caption)

# === БАЗА ПРОДУКТОВ ===
FOOD_DB = {
    "курица": 165, "куриная грудка": 165, "куриное филе": 110, "куриная ножка": 180,
    "говядина": 250, "говяжий фарш": 270, "свинина": 320, "свиной фарш": 340,
    "баранина": 280, "индейка": 130, "утка": 350, "кролик": 156,
    "печень": 130, "куриная печень": 140, "говяжья печень": 130, "сердце": 160,
    "лосось": 200, "семга": 200, "тунец": 130, "скумбрия": 180,
    "сельдь": 160, "треска": 75, "минтай": 70, "окунь": 120,
    "щука": 90, "судак": 85, "карп": 100, "форель": 150, "горбуша": 140,
    "креветки": 90, "кальмар": 100, "мидии": 80,
    "яйцо": 155, "яйца": 155, "яичный белок": 45, "яичный желток": 320,
    "молоко": 60, "кефир": 50, "ряженка": 55, "йогурт": 60,
    "творог": 120, "творог обезжиренный": 80, "сметана": 200, "сливки": 300,
    "сыр": 350, "пармезан": 400, "моцарелла": 300, "фета": 260,
    "масло сливочное": 750, "маргарин": 720,
    "рис": 130, "гречка": 110, "овсянка": 80, "геркулес": 85,
    "манка": 120, "перловка": 130, "пшено": 140,
    "макароны": 130, "спагетти": 130, "лапша": 140,
    "хлеб": 250, "хлеб черный": 200, "батон": 260, "лаваш": 270,
    "картофель": 80, "батат": 90, "морковь": 35, "свекла": 43,
    "лук": 40, "чеснок": 149, "помидор": 18, "огурец": 15,
    "перец болгарский": 26, "кабачок": 17, "тыква": 26, "брокколи": 34,
    "капуста": 28, "сельдерей": 16, "горошек": 80, "кукуруза": 100,
    "салат": 15, "шпинат": 23,
    "банан": 90, "яблоко": 52, "груша": 57, "апельсин": 47, "мандарин": 38,
    "лимон": 34, "грейпфрут": 35, "виноград": 65, "арбуз": 30, "дыня": 35,
    "персик": 45, "абрикос": 48, "слива": 42, "вишня": 50, "черешня": 52,
    "клубника": 32, "малина": 42, "черника": 44, "голубика": 40,
    "хурма": 65, "киви": 48, "манго": 60, "ананас": 50, "гранат": 70,
    "финики": 280, "изюм": 300, "курага": 250, "чернослив": 230,
    "грецкий орех": 650, "миндаль": 600, "арахис": 550, "фундук": 650,
    "кешью": 570, "фисташки": 560, "семечки": 580,
    "майонез": 600, "кетчуп": 100, "горчица": 66, "соевый соус": 60,
    "оливковое масло": 900, "подсолнечное масло": 900,
    "грибы": 22, "шампиньоны": 20, "вешенки": 33,
    "фасоль": 90, "чечевица": 110, "горох": 80, "нут": 130,
    "сахар": 400, "мед": 320, "шоколад": 550, "печенье": 450,
    "кофе": 2, "чай": 1, "сок": 50, "протеин": 120, "гейнер": 350,
    "тофу": 76, "вода": 0,
    "пельмени": 250, "вареники": 200, "манты": 280,
}

def search_food(q):
    q = q.lower().strip()
    return [(n, c) for n, c in FOOD_DB.items() if q in n][:10]

# === БД ===
def init_db():
    conn = get_conn(); c = conn.cursor()
    if USE_PG:
        id_t, tg_t, dt_t = "BIGSERIAL PRIMARY KEY", "BIGINT", "TIMESTAMP"
    else:
        id_t, tg_t, dt_t = "INTEGER PRIMARY KEY AUTOINCREMENT", "INTEGER", "DATETIME"
    c.execute(f'''CREATE TABLE IF NOT EXISTS users (id {id_t}, tg_id {tg_t} UNIQUE,
        name TEXT, goal TEXT, level TEXT, cal_limit INTEGER DEFAULT 2500, created_at {dt_t})''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS workouts (id {id_t}, user_id {tg_t},
        exercise TEXT, weight REAL, reps INTEGER, sets INTEGER,
        status TEXT DEFAULT 'pending', date {dt_t})''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS achievements (id {id_t}, user_id {tg_t},
        exercise TEXT, max_weight REAL, date {dt_t})''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS food_log (id {id_t}, user_id {tg_t},
        product TEXT, calories INTEGER, grams INTEGER, date {dt_t})''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS streaks (user_id {tg_t} PRIMARY KEY,
        current_streak INTEGER DEFAULT 0, max_streak INTEGER DEFAULT 0,
        last_workout_date TEXT, total_workouts INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1, xp INTEGER DEFAULT 0)''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS user_stats (user_id {tg_t} PRIMARY KEY,
        bodyweight REAL, updated_at {dt_t})''')
    c.execute(f'''CREATE TABLE IF NOT EXISTS user_program (user_id {tg_t} PRIMARY KEY,
        program_name TEXT, current_day INTEGER DEFAULT 0, started_at {dt_t})''')
    conn.commit(); conn.close()

def get_user(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT * FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone(); conn.close(); return u

def add_user(tg_id, name, goal, level):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    if c.fetchone():
        c.execute(adapt("UPDATE users SET name = ?, goal = ?, level = ? WHERE tg_id = ?"), (name, goal, level, tg_id))
    else:
        c.execute(adapt("INSERT INTO users (tg_id, name, goal, level, created_at) VALUES (?, ?, ?, ?, ?)"),
                  (tg_id, name, goal, level, datetime.now()))
    conn.commit(); conn.close()

def update_cal_limit(tg_id, limit):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("UPDATE users SET cal_limit = ? WHERE tg_id = ?"), (limit, tg_id))
    conn.commit(); conn.close()

def save_food(tg_id, product, cal, grams):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if u:
        c.execute(adapt("INSERT INTO food_log (user_id, product, calories, grams, date) VALUES (?, ?, ?, ?, ?)"),
                  (u[0], product, cal, grams, datetime.now()))
        conn.commit()
    conn.close()

def get_food_today(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt(f"SELECT SUM(calories) FROM food_log WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND {today_clause()}"), (tg_id,))
    t = c.fetchone()[0]; conn.close(); return t or 0

def get_food_log(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt(f"SELECT product, calories, grams FROM food_log WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND {today_clause()} ORDER BY date DESC"), (tg_id,))
    f = c.fetchall(); conn.close(); return f

def update_streak_and_xp(tg_id, xp_gain=50):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if not u: conn.close(); return None
    uid = u[0]
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute(adapt("SELECT current_streak, max_streak, last_workout_date, xp, level, total_workouts FROM streaks WHERE user_id = ?"), (uid,))
    row = c.fetchone()
    if not row:
        c.execute(adapt("INSERT INTO streaks (user_id, current_streak, max_streak, last_workout_date, xp, level, total_workouts) VALUES (?, 1, 1, ?, ?, 1, 1)"),
                  (uid, today, xp_gain))
        conn.commit(); conn.close()
        return {"streak": 1, "max_streak": 1, "level": 1, "xp": xp_gain, "level_up": False, "total": 1}
    cur, mx, last, xp, lvl, tot = row
    if last == today:
        conn.close()
        return {"streak": cur, "max_streak": mx, "level": lvl, "xp": xp, "level_up": False, "total": tot, "already": True}
    yest = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    cur = cur + 1 if last == yest else 1
    mx = max(mx, cur); xp += xp_gain; tot += 1
    new_lvl = xp // 500 + 1
    lvl_up = new_lvl > lvl; lvl = new_lvl
    c.execute(adapt("UPDATE streaks SET current_streak = ?, max_streak = ?, last_workout_date = ?, xp = ?, level = ?, total_workouts = ? WHERE user_id = ?"),
              (cur, mx, today, xp, lvl, tot, uid))
    conn.commit(); conn.close()
    return {"streak": cur, "max_streak": mx, "level": lvl, "xp": xp, "level_up": lvl_up, "total": tot}

def get_streak_info(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT current_streak, max_streak, level, xp, total_workouts FROM streaks WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)"), (tg_id,))
    r = c.fetchone(); conn.close(); return r

def save_workout(tg_id, exercise, weight, reps, sets, status='done'):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if not u: conn.close(); return None
    uid = u[0]
    c.execute(adapt("INSERT INTO workouts (user_id, exercise, weight, reps, sets, status, date) VALUES (?, ?, ?, ?, ?, ?, ?)"),
              (uid, exercise, weight, reps, sets, status, datetime.now()))
    c.execute(adapt("SELECT max_weight FROM achievements WHERE user_id = ? AND exercise = ?"), (uid, exercise))
    a = c.fetchone()
    if not a:
        c.execute(adapt("INSERT INTO achievements (user_id, exercise, max_weight, date) VALUES (?, ?, ?, ?)"),
                  (uid, exercise, weight, datetime.now()))
    elif weight > a[0]:
        c.execute(adapt("UPDATE achievements SET max_weight = ?, date = ? WHERE user_id = ? AND exercise = ?"),
                  (weight, datetime.now(), uid, exercise))
    conn.commit(); conn.close()
    if status == 'done': return update_streak_and_xp(tg_id, 50)
    return None

def get_today_workouts(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt(f"SELECT exercise, weight, reps, sets, status FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND {today_clause()} ORDER BY date DESC"), (tg_id,))
    w = c.fetchall(); conn.close(); return w

def get_week_stats(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt(f"SELECT exercise, MAX(weight) FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND {week_ago_clause()} AND status = 'done' GROUP BY exercise"), (tg_id,))
    b = c.fetchall(); conn.close(); return b

def get_all_workouts(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT exercise, weight, reps, sets, status, date FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) ORDER BY date DESC LIMIT 20"), (tg_id,))
    w = c.fetchall(); conn.close(); return w

def get_bodyweight(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT bodyweight FROM user_stats WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)"), (tg_id,))
    r = c.fetchone(); conn.close(); return r[0] if r else None

def set_bodyweight(tg_id, bw):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if u:
        c.execute(adapt("SELECT user_id FROM user_stats WHERE user_id = ?"), (u[0],))
        if c.fetchone():
            c.execute(adapt("UPDATE user_stats SET bodyweight = ?, updated_at = ? WHERE user_id = ?"), (bw, datetime.now(), u[0]))
        else:
            c.execute(adapt("INSERT INTO user_stats (user_id, bodyweight, updated_at) VALUES (?, ?, ?)"), (u[0], bw, datetime.now()))
        conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT tg_id, name FROM users")
    users = c.fetchall(); conn.close(); return users

def get_user_program(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT program_name, current_day FROM user_program WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)"), (tg_id,))
    r = c.fetchone(); conn.close(); return r

def set_user_program(tg_id, program_name):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if u:
        c.execute(adapt("SELECT user_id FROM user_program WHERE user_id = ?"), (u[0],))
        if c.fetchone():
            c.execute(adapt("UPDATE user_program SET program_name = ?, current_day = 0, started_at = ? WHERE user_id = ?"), (program_name, datetime.now(), u[0]))
        else:
            c.execute(adapt("INSERT INTO user_program (user_id, program_name, current_day, started_at) VALUES (?, ?, 0, ?)"), (u[0], program_name, datetime.now()))
        conn.commit()
    conn.close()

def clear_user_program(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("DELETE FROM user_program WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)"), (tg_id,))
    conn.commit(); conn.close()

def advance_program_day(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("UPDATE user_program SET current_day = current_day + 1 WHERE user_id = (SELECT id FROM users WHERE tg_id = ?)"), (tg_id,))
    conn.commit(); conn.close()

def get_week_workout_count(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt(f"SELECT COUNT(*) FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND {week_ago_clause()} AND status = 'done'"), (tg_id,))
    n = c.fetchone()[0]; conn.close(); return n or 0

# === УРОВНИ ===
LEVEL_TITLES = {1: "🥚 Новичок", 2: "🏃 Бегун", 3: "💪 Качок", 4: "🔥 Зверь",
                5: "🦍 Горилла", 6: "👹 Монстр", 7: "🐉 Дракон", 8: "⚡ Легенда"}
def get_level_title(l): return LEVEL_TITLES.get(l, "⚡ Легенда")

# === ЗАМЕНА ===
EXERCISE_SUBS = {
    "присед": ["🦵 Болгарский выпад", "🦵 Гоблет-присед", "🦵 Жим ногами", "🦵 Фронтальный присед"],
    "жим": ["💪 Жим гантелей", "💪 Отжимания с весом", "💪 Жим в Смите", "💪 Отжимания на брусьях"],
    "становая": ["🔥 Румынская тяга", "🔥 Гиперэкстензия", "🔥 Тяга на прямых ногах", "🔥 Гуд-морнинг"],
    "подтягивания": ["🏋️ Тяга верхнего блока", "🏋️ Тяга в наклоне", "🏋️ Австралийские подтягивания"],
    "тяга": ["🏋️ Тяга гантели", "🏋️ Тяга блока", "🏋️ Тяга Т-грифа"],
    "отжимания": ["💪 Жим лежа", "💪 Жим гантелей", "💪 Отжимания на брусьях"],
    "выпады": ["🦵 Болгарский выпад", "🦵 Зашагивания на платформу", "🦵 Присед на одной ноге"],
    "планка": ["🎯 Скручивания", "🎯 Велосипед", "🎯 Подъём ног в висе", "🎯 Ролл-аут"],
    "бицепс": ["💪 Молотки", "💪 Подъём на скамье Скотта", "💪 Концентрированный подъём"],
    "трицепс": ["💪 Французский жим", "💪 Разгибания на блоке", "💪 Отжимания узким хватом"],
}
def get_subs(name):
    name = name.lower().strip()
    for key in EXERCISE_SUBS:
        if key in name: return EXERCISE_SUBS[key]
    return None

def get_progression(weight, reps):
    if reps <= 5: return f"📈 Попробуй **{weight + 5} кг × {reps}** или **{weight} кг × {reps + 1}**"
    elif reps <= 8: return f"📈 Попробуй **{weight + 2.5} кг × {reps}** или **{weight} кг × {reps + 1}**"
    elif reps <= 12: return f"📈 Попробуй **{weight + 1.25} кг × {reps}** или **{weight} кг × {reps + 2}**"
    else: return f"📈 Попробуй **{weight + 2.5} кг × 8** — ты уже сильный 💪"

def calc_1rm(weight, reps):
    if reps == 1: return weight
    return round(weight * (1 + reps / 30), 1)

def get_1rm_table(one_rm):
    return {
        "100% (1 раз)": round(one_rm), "95% (2 раза)": round(one_rm * 0.95, 1),
        "90% (4 раза)": round(one_rm * 0.90, 1), "85% (6 раз)": round(one_rm * 0.85, 1),
        "80% (8 раз)": round(one_rm * 0.80, 1), "75% (10 раз)": round(one_rm * 0.75, 1),
        "70% (12 раз)": round(one_rm * 0.70, 1),
    }

def calc_bju(weight, goal):
    if goal == "mass":
        cal = weight * 33; protein = weight * 2.0; fat = weight * 1.0
    elif goal == "lose":
        cal = weight * 25; protein = weight * 2.2; fat = weight * 0.8
    else:
        cal = weight * 28; protein = weight * 1.8; fat = weight * 1.0
    carbs = (cal - protein * 4 - fat * 9) / 4
    return round(cal), round(protein), round(fat), round(carbs)

# === ПРОГРАММЫ ===
PROGRAMS = {
    "beginner": {
        "name": "🌱 Новичок", "desc": "3 трен/нед, всё тело",
        "days": [
            {"day": "Всё тело", "exercises": ["Приседания 3×10", "Отжимания 3×8", "Планка 3×30 сек", "Тяга гантелей 3×10"]},
            {"day": "Отдых", "exercises": []},
            {"day": "Всё тело", "exercises": ["Выпады 3×10", "Жим гантелей 3×10", "Подтягивания 3×6", "Пресс 3×15"]},
            {"day": "Отдых", "exercises": []},
            {"day": "Всё тело", "exercises": ["Становая 3×8", "Жим стоя 3×10", "Гребля 3×10", "Планка 3×45 сек"]},
            {"day": "Отдых", "exercises": []},
            {"day": "Отдых", "exercises": []},
        ]
    },
    "mass": {
        "name": "💪 Масса", "desc": "4 трен/нед, сплит",
        "days": [
            {"day": "Грудь + Трицепс", "exercises": ["Жим лёжа 4×8", "Жим гантелей 3×10", "Разводка 3×12", "Французский жим 3×10"]},
            {"day": "Спина + Бицепс", "exercises": ["Становая 4×6", "Подтягивания 4×8", "Тяга штанги 3×10", "Подъём на бицепс 3×10"]},
            {"day": "Отдых", "exercises": []},
            {"day": "Ноги", "exercises": ["Приседания 4×8", "Жим ногами 3×12", "Румынская тяга 3×10", "Икры 4×15"]},
            {"day": "Плечи + Пресс", "exercises": ["Жим стоя 4×8", "Махи в стороны 3×12", "Тяга к подбородку 3×10", "Пресс 3×20"]},
            {"day": "Отдых", "exercises": []},
            {"day": "Отдых", "exercises": []},
        ]
    },
    "cut": {
        "name": "🔥 Похудение", "desc": "5 трен/нед, HIIT + силовая",
        "days": [
            {"day": "HIIT + Пресс", "exercises": ["Бёрпи 4×20 сек", "Скакалка 5 мин", "Планка 3×1 мин", "Скручивания 3×20"]},
            {"day": "Круговая", "exercises": ["Приседания 3×20", "Отжимания 3×15", "Выпады 3×15", "Прыжки 3×30 сек"]},
            {"day": "Кардио", "exercises": ["Бег 30 мин", "Растяжка 10 мин"]},
            {"day": "Круговая 2", "exercises": ["Бёрпи 3×15", "Бег на месте 3×1 мин", "Скакалка 3×100", "Велосипед 3×30"]},
            {"day": "Силовая + Кардио", "exercises": ["Приседания 3×15", "Жим 3×12", "Тяга 3×12", "Кардио 20 мин"]},
            {"day": "Активный отдых", "exercises": ["Прогулка 1 час"]},
            {"day": "Отдых", "exercises": []},
        ]
    }
}

# === ТРЕНИРОВКИ ЛЕГЕНД ===
LEGENDS = {
    "ronnie": {
        "name": "🏆 Ронни Коулмэн",
        "desc": "8x Мистер Олимпия. Эра масс и тяжестей.",
        "chest": {
            "title": "Грудь и трицепс",
            "exercises": [
                "Жим гантелей лежа — 4×12",
                "Жим гантелей на наклонной — 4×10",
                "Жим в тренажере — 3×12",
                "Отжимания на брусьях (с весом) — 3×10",
                "Французский жим — 3×12"
            ]
        },
        "back": {
            "title": "Спина (толщина)",
            "exercises": [
                "Становая тяга — 4×8",
                "Тяга штанги в наклоне — 4×10",
                "Тяга Т-грифа — 3×12",
                "Тяга гантели одной рукой — 3×10"
            ]
        },
        "legs": {
            "title": "Ноги (квадрицепс)",
            "exercises": [
                "Приседания — 5×10",
                "Жим ногами — 4×12",
                "Выпады с гантелями — 3×20 шагов",
                "Разгибания ног — 4×15"
            ]
        }
    },
    "dorian": {
        "name": "🏆 Дориан Йейтс",
        "desc": "6x Мистер Олимпия. Эра интенсивности и отказов.",
        "chest": {
            "title": "Грудь (низкий объем, высокий отказ)",
            "exercises": [
                "Жим лежа на наклонной — 1×8-10 (до отказа)",
                "Жим в тренажере Hammer — 1×8-10 (до отказа)",
                "Разводка гантелей на наклонной — 1×10 (до отказа)",
                "Кроссовер — 1×12 (до отказа)"
            ]
        },
        "back": {
            "title": "Спина (кровь и кишки)",
            "exercises": [
                "Тяга штанги в наклоне — 2×12-15 (разминка)",
                "Тяга блока к груди — 1×8-10 (до отказа)",
                "Тяга гантели одной рукой — 1×8-10 (до отказа)",
                "Тяга нижнего блока — 1×10 (до отказа)",
                "Шраги со штангой — 1×10 (до отказа)"
            ]
        },
        "legs": {
            "title": "Ноги (база + отказ)",
            "exercises": [
                "Приседания — 1×8-10 (до отказа)",
                "Жим ногами — 1×10 (до отказа)",
                "Разгибания ног — 1×12 (до отказа)",
                "Сгибания ног — 1×12 (до отказа)"
            ]
        }
    },
    "jay": {
        "name": "🏆 Джей Катлер",
        "desc": "4x Мистер Олимпия. Эра пирамид и объема.",
        "chest": {
            "title": "Грудь (пирамида)",
            "exercises": [
                "Жим в тренажере Hammer — 2×15 (разминка), 3×10-12 (пирамида)",
                "Жим гантелей лежа — 3×10-12",
                "Разводка гантелей на наклонной — 3×12",
                "Кроссовер — 3×15"
            ]
        },
        "back": {
            "title": "Спина (ширина и толщина)",
            "exercises": [
                "Тяга верхнего блока — 4×10-12",
                "Тяга штанги в наклоне — 3×10",
                "Тяга нижнего блока — 3×12",
                "Шраги — 3×12"
            ]
        },
        "legs": {
            "title": "Ноги (объем)",
            "exercises": [
                "Приседания — 4×10-12",
                "Жим ногами — 4×12",
                "Разгибания ног — 4×15",
                "Сгибания ног — 4×12"
            ]
        }
    }
}

# === НОРМЫ ===
STRENGTH_STANDARDS = {
    "жим":     {"name": "Жим лёжа", "ratios": [0.50, 0.75, 1.00, 1.25, 1.50, 2.00]},
    "присед":  {"name": "Присед",   "ratios": [0.75, 1.00, 1.50, 2.00, 2.50, 3.00]},
    "становая":{"name": "Становая", "ratios": [1.00, 1.25, 1.75, 2.25, 2.75, 3.50]},
}
LEVELS_STD = ["🥚 Новичок", "🏃 Начальный", "💪 Средний", "🔥 Хороший", "🦍 Продвинутый", "⚡ Элита"]

def check_standard(lift_key, one_rm, bodyweight):
    if lift_key not in STRENGTH_STANDARDS: return None
    ratios = STRENGTH_STANDARDS[lift_key]["ratios"]
    user_ratio = one_rm / bodyweight
    level_idx = 0
    for i, r in enumerate(ratios):
        if user_ratio >= r: level_idx = i + 1
        else: break
    level_idx = min(level_idx, len(LEVELS_STD) - 1)
    return {"level": LEVELS_STD[level_idx], "ratio": round(user_ratio, 2),
            "next_ratio": ratios[level_idx] if level_idx < len(ratios) else None,
            "next_weight": round(ratios[level_idx] * bodyweight, 1) if level_idx < len(ratios) else None}

DAILY_TIPS = [
    "💧 Пей 30 мл воды на кг веса", "😴 Спи 7-9 часов — мышцы растут во сне",
    "🥩 Ешь 1.6-2 г белка на кг веса", "🔥 Разминка 5-10 мин перед тренировкой",
    "📈 Прогрессия важнее идеальной техники", "💪 Не качай одну группу чаще 2-3 раз в неделю",
    "🏃 Кардио после силовой — жиросжигание +20%", "🍔 80% результата — питание",
]
def get_tip_of_day(): return DAILY_TIPS[datetime.now().day % len(DAILY_TIPS)]

# ============ КЛАВИАТУРЫ ============
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("☀️ Сегодня", callback_data="today")],
        [InlineKeyboardButton("🏋️ Тренировка", callback_data="train_menu")],
        [InlineKeyboardButton("🍔 Питание", callback_data="food_menu")],
        [InlineKeyboardButton("👤 Профиль", callback_data="profile_menu")]
    ])

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]])

user_data = {}

# ============ КОМАНДЫ ============
async def start(update, context):
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    if user:
        await show_main(update, context)
    else:
        user_data[tg_id] = {"step": "goal"}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏋️ Набрать массу", callback_data="goal_mass")],
            [InlineKeyboardButton("🔥 Похудеть", callback_data="goal_lose")],
            [InlineKeyboardButton("💪 Поддерживать форму", callback_data="goal_keep")]
        ])
        await update.message.reply_text(
            f"Йо, {update.effective_user.first_name}! 💪\n\nЯ твой персональный тренер. Выбери цель — и погнали:",
            reply_markup=kb
        )

async def show_main(update, context):
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    name = user[2] if user else "бро"
    text = f"👋 Привет, {name}!\n\nЧто делаем сегодня?"
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=main_kb())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_kb())

# ============ ОБРАБОТЧИК КНОПОК ============
async def button_handler(update, context):
    q = update.callback_query
    await q.answer()
    tg_id = q.from_user.id
    data = q.data

    if data.startswith("goal_"):
        goal = data.replace("goal_", "")
        user_data[tg_id] = {"step": "level", "goal": goal}
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Новичок", callback_data="level_beginner")],
            [InlineKeyboardButton("🟡 Средний", callback_data="level_intermediate")],
            [InlineKeyboardButton("🔴 Продвинутый", callback_data="level_advanced")]
        ])
        await q.edit_message_text("Твой уровень?", reply_markup=kb)
        return

    if data.startswith("level_"):
        level = data.replace("level_", "")
        goal = user_data[tg_id]["goal"]
        add_user(tg_id, q.from_user.first_name, goal, level)
        del user_data[tg_id]
        await q.edit_message_text("🎉 Отлично! Ты в системе.", reply_markup=main_kb())
        return

    if data == "back_to_menu":
        await show_main(update, context); return

    if data == "today":
        await show_today(q, tg_id); return

    if data == "train_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Записать тренировку", callback_data="log")],
            [InlineKeyboardButton("📅 Программа", callback_data="program"),
             InlineKeyboardButton("🏛️ Легенды", callback_data="legends_menu")],
            [InlineKeyboardButton("🎯 Нормы", callback_data="standards"),
             InlineKeyboardButton("📐 1RM", callback_data="onerm")],
            [InlineKeyboardButton("📈 Прогрессия", callback_data="progression"),
             InlineKeyboardButton("🔄 Замена", callback_data="subs")],
            [InlineKeyboardButton("⏱️ Таймер", callback_data="timer"),
             InlineKeyboardButton("📋 История", callback_data="my_workouts")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
        ])
        await q.edit_message_text("🏋️ **Тренировка**", reply_markup=kb, parse_mode='Markdown')
        return

    if data == "food_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🍔 Калории", callback_data="calories")],
            [InlineKeyboardButton("➕ Записать еду", callback_data="log_food")],
            [InlineKeyboardButton("🥗 Рассчитать БЖУ", callback_data="bju")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
        ])
        await q.edit_message_text("🍔 **Питание**", reply_markup=kb, parse_mode='Markdown')
        return

    if data == "profile_menu":
        info = get_streak_info(tg_id)
        level_str = f"🏆 Уровень {info[2]} | ⭐ {info[3]} XP | 🔥 {info[0]} дней" if info else "🏆 Пока нет данных"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 Уровень", callback_data="my_level")],
            [InlineKeyboardButton("⚖️ Мой вес", callback_data="my_bw")],
            [InlineKeyboardButton("💡 Совет дня", callback_data="tip_of_day")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
        ])
        await q.edit_message_text(f"👤 **Профиль**\n\n{level_str}", reply_markup=kb, parse_mode='Markdown')
        return

    if data == "log":
        user_data[tg_id] = {"step": "log_exercise"}
        await q.edit_message_text("Упражнение?", reply_markup=back_kb()); return
    if data == "my_workouts": await show_my_workouts(q, tg_id); return
    if data == "my_level": await show_level(q, tg_id); return
    if data == "tip_of_day":
        await q.edit_message_text(f"💡 {get_tip_of_day()}", reply_markup=back_kb()); return
    if data == "help":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📩 Поддержка", url="https://t.me/Tehnoprofff")],
            [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
        ])
        await q.edit_message_text(
            "❓ **Как пользоваться:**\n\n"
            "☀️ **Сегодня** — дашборд дня\n"
            "🏋️ **Тренировка** — запись, программа, легенды, нормы, 1RM\n"
            "🍔 **Питание** — калории и БЖУ\n"
            "👤 **Профиль** — уровень, вес, советы\n\n"
            "После тренировки и еды прилетит мотивационное видео 🔥",
            reply_markup=kb, parse_mode='Markdown')
        return

    if data == "timer":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("60 сек", callback_data="timer_60"),
             InlineKeyboardButton("90 сек", callback_data="timer_90")],
            [InlineKeyboardButton("120 сек", callback_data="timer_120"),
             InlineKeyboardButton("180 сек", callback_data="timer_180")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ])
        await q.edit_message_text("⏱️ Сколько отдых?", reply_markup=kb); return
    if data.startswith("timer_"):
        sec = int(data.replace("timer_", ""))
        await q.edit_message_text(f"⏱️ Таймер на {sec} сек запущен!\nОтдыхай 💪", reply_markup=back_kb())
        asyncio.create_task(rest_timer_task(context.bot, q.message.chat_id, sec))
        return

    if data == "onerm":
        user_data[tg_id] = {"step": "onerm_input"}
        await q.edit_message_text("📐 Введи: **вес × повторения**\n\nНапример: `80 5`", reply_markup=back_kb(), parse_mode='Markdown'); return
    if data == "progression":
        user_data[tg_id] = {"step": "progression_input"}
        await q.edit_message_text("📈 Введи последний подход: **вес × повторения**\n\nНапример: `80 8`", reply_markup=back_kb(), parse_mode='Markdown'); return
    if data == "subs":
        user_data[tg_id] = {"step": "subs_input"}
        await q.edit_message_text("🔄 Какое упражнение заменить?\n\nНапример: `присед`, `жим`, `подтягивания`", reply_markup=back_kb()); return

    if data == "program":
        prog = get_user_program(tg_id)
        if prog:
            name, day = prog
            p = PROGRAMS.get(name)
            today = p["days"][day % 7] if p else None
            txt = f"📅 **{p['name'] if p else name}**\nДень {day % 7 + 1}/7\n\n"
            if today:
                txt += f"**Сегодня — {today['day']}**\n"
                if today['exercises']:
                    for e in today['exercises']: txt += f"• {e}\n"
                else: txt += "Отдых 😴"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Следующий день", callback_data="program_next")],
                [InlineKeyboardButton("🔄 Сменить программу", callback_data="program_change")],
                [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
            ])
            await q.edit_message_text(txt, reply_markup=kb, parse_mode='Markdown')
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🌱 Новичок (3/нед)", callback_data="setprog_beginner")],
                [InlineKeyboardButton("💪 Масса (4/нед)", callback_data="setprog_mass")],
                [InlineKeyboardButton("🔥 Похудение (5/нед)", callback_data="setprog_cut")],
                [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
            ])
            await q.edit_message_text("📅 **Выбери программу:**", reply_markup=kb, parse_mode='Markdown')
        return

    if data.startswith("setprog_"):
        key = data.replace("setprog_", "")
        set_user_program(tg_id, key)
        p = PROGRAMS[key]
        await q.edit_message_text(
            f"✅ **{p['name']}** активирована!\n\n{p['desc']}\n\nОткрывай «Сегодня» — там будет план.",
            reply_markup=back_kb(), parse_mode='Markdown')
        return

    if data == "program_next":
        advance_program_day(tg_id)
        await q.edit_message_text("✅ День продвинут!", reply_markup=back_kb()); return

    if data == "program_change":
        clear_user_program(tg_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌱 Новичок", callback_data="setprog_beginner")],
            [InlineKeyboardButton("💪 Масса", callback_data="setprog_mass")],
            [InlineKeyboardButton("🔥 Похудение", callback_data="setprog_cut")]
        ])
        await q.edit_message_text("Выбери новую программу:", reply_markup=kb); return

    if data == "standards":
        bw = get_bodyweight(tg_id)
        if not bw:
            user_data[tg_id] = {"step": "ask_bw_for_std"}
            await q.edit_message_text("⚖️ Введи свой вес (кг) для расчёта норм:", reply_markup=back_kb()); return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Жим лёжа", callback_data="std_жим")],
            [InlineKeyboardButton("Присед", callback_data="std_присед")],
            [InlineKeyboardButton("Становая", callback_data="std_становая")],
            [InlineKeyboardButton("🔙 Назад", callback_data="train_menu")]
        ])
        await q.edit_message_text(f"🎯 **Нормы силы** (твой вес: {bw} кг)\n\nВыбери упражнение:", reply_markup=kb, parse_mode='Markdown'); return

    if data.startswith("std_"):
        lift = data.replace("std_", "")
        user_data[tg_id] = {"step": "std_input", "lift": lift}
        await q.edit_message_text(f"Введи рекорд для **{STRENGTH_STANDARDS[lift]['name']}**:\n\nНапример: `80 5`", reply_markup=back_kb(), parse_mode='Markdown'); return

    if data == "my_bw":
        bw = get_bodyweight(tg_id)
        user_data[tg_id] = {"step": "set_bw"}
        txt = f"⚖️ Текущий вес: **{bw} кг**\n\nВведи новый:" if bw else "⚖️ Введи свой вес (кг):"
        await q.edit_message_text(txt, reply_markup=back_kb(), parse_mode='Markdown'); return

    if data == "bju":
        user_data[tg_id] = {"step": "bju_weight"}
        await q.edit_message_text("🥗 Введи свой вес (кг):", reply_markup=back_kb()); return

    if data == "calories": await show_calories(q, tg_id); return

    if data == "log_food":
        user_data[tg_id] = {"step": "log_food"}
        await q.edit_message_text("Что съел? (например: курица, рис, яблоко)", reply_markup=back_kb()); return

    if data == "set_cal_limit":
        user_data[tg_id] = {"step": "set_cal_limit"}
        await q.edit_message_text("Дневной лимит калорий (например: 2500):", reply_markup=back_kb()); return

    if data.startswith("food_"):
        parts = data.split("_")
        if len(parts) >= 3:
            name = parts[1]; cal = int(parts[2])
            user_data[tg_id] = {"step": "food_select", "product": name, "cal_per_100": cal}
            await q.edit_message_text("Сколько грамм?", reply_markup=back_kb())
        return

    # === ЛЕГЕНДЫ ===
    if data == "legends_menu":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏆 Ронни Коулмэн", callback_data="legend_ronnie")],
            [InlineKeyboardButton("🏆 Дориан Йейтс", callback_data="legend_dorian")],
            [InlineKeyboardButton("🏆 Джей Катлер", callback_data="legend_jay")],
            [InlineKeyboardButton("🔙 Назад", callback_data="train_menu")]
        ])
        await q.edit_message_text(
            "🏛️ **Тренировки легенд**\n\nВыбери атлета — и бот выдаст его реальную программу:",
            reply_markup=kb, parse_mode='Markdown')
        return

    if data.startswith("legend_") and not data.startswith("legendwork_") and not data.startswith("legendvideo_"):
        legend_key = data.replace("legend_", "")
        legend = LEGENDS.get(legend_key)
        if not legend:
            await q.edit_message_text("Не найдено.", reply_markup=back_kb()); return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Грудь", callback_data=f"legendwork_{legend_key}_chest")],
            [InlineKeyboardButton("Спина", callback_data=f"legendwork_{legend_key}_back")],
            [InlineKeyboardButton("Ноги", callback_data=f"legendwork_{legend_key}_legs")],
            [InlineKeyboardButton("🔙 Назад", callback_data="legends_menu")]
        ])
        await q.edit_message_text(
            f"{legend['name']}\n_{legend['desc']}_\n\nВыбери группу мышц:",
            reply_markup=kb, parse_mode='Markdown')
        return

    if data.startswith("legendwork_"):
        parts = data.replace("legendwork_", "").split("_")
        legend_key = parts[0]
        muscle = parts[1]
        legend = LEGENDS.get(legend_key)
        workout = legend.get(muscle) if legend else None
        if not workout:
            await q.edit_message_text("Тренировка не найдена.", reply_markup=back_kb()); return
        txt = f"{legend['name']} — **{workout['title']}**\n\n"
        for ex in workout['exercises']:
            txt += f"• {ex}\n"
        txt += "\n🔥 Вперёд, брат!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Мотивация", callback_data=f"legendvideo_{legend_key}")],
            [InlineKeyboardButton("🔙 К группам", callback_data=f"legend_{legend_key}")]
        ])
        await q.edit_message_text(txt, reply_markup=kb, parse_mode='Markdown')
        return

    if data.startswith("legendvideo_"):
        legend_key = data.replace("legendvideo_", "")
        legend = LEGENDS.get(legend_key)
        await q.edit_message_text(
            f"🔥 **{legend['name']}** — тренируйся как легенда!",
            reply_markup=back_kb(), parse_mode='Markdown')
        try:
            await context.bot.send_video(
                chat_id=q.message.chat_id,
                video=random.choice(MOTIVATION_VIDEOS),
                caption=f"🔥 {legend['name']} — тренируйся как легенда!",
                supports_streaming=True
            )
        except Exception as e:
            logging.error(f"Legend video error: {e}")
        return

async def rest_timer_task(bot, chat_id, seconds):
    await asyncio.sleep(seconds)
    try: await bot.send_message(chat_id=chat_id, text=f"⏰ {seconds} сек прошло! Следующий подход 💪")
    except Exception as e: logging.error(f"Timer: {e}")

# ============ ЭКРАН «СЕГОДНЯ» ============
async def show_today(q, tg_id):
    user = get_user(tg_id)
    if not user:
        await q.edit_message_text("Нажми /start"); return
    name = user[2] or "бро"
    workouts = get_today_workouts(tg_id)
    done_today = len([w for w in workouts if w[4] == 'done'])
    info = get_streak_info(tg_id)
    streak, lvl, xp = 0, 1, 0
    if info:
        streak, _, lvl, xp, _ = info
    limit = user[5] or 2500
    eaten = get_food_today(tg_id)
    rem = limit - eaten
    prog = get_user_program(tg_id)
    plan_text = ""
    if prog:
        pname, day = prog
        p = PROGRAMS.get(pname)
        if p:
            td = p["days"][day % 7]
            plan_text = f"\n📅 **{td['day']}**\n"
            if td['exercises']:
                for e in td['exercises'][:3]:
                    plan_text += f"• {e}\n"
                if len(td['exercises']) > 3: plan_text += f"...и ещё {len(td['exercises']) - 3}\n"
            else:
                plan_text = "\n📅 Сегодня — **отдых** 😴\n"
    else:
        plan_text = "\n📅 Программа не выбрана\n"
    fire = "🔥" * min(streak, 5) if streak else ""
    txt = f"☀️ **Сегодня, {name}**\n\n"
    txt += f"🏆 Ур. {lvl} | ⭐ {xp} XP | 🔥 {streak} {fire}\n"
    txt += plan_text
    txt += f"\n🍔 Калории: **{eaten}/{limit}** (осталось {rem})\n"
    txt += f"💪 Тренировок сегодня: **{done_today}**\n"
    txt += f"\n{get_tip_of_day()}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Записать тренировку", callback_data="log")],
        [InlineKeyboardButton("🍔 Записать еду", callback_data="log_food")],
        [InlineKeyboardButton("🏛️ Легенды", callback_data="legends_menu")],
        [InlineKeyboardButton("🔄 Обновить", callback_data="today"),
         InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
    ])
    await q.edit_message_text(txt, reply_markup=kb, parse_mode='Markdown')

# ============ СТАРЫЕ ЭКРАНЫ ============
async def show_level(query, tg_id):
    info = get_streak_info(tg_id)
    if not info:
        await query.edit_message_text("🏆 Пока нет данных, бро!\nЗапиши первую тренировку 💪", reply_markup=back_kb()); return
    streak, mx, level, xp, tot = info
    title = get_level_title(level)
    next_xp = level * 500
    prog = int((xp % 500) / 500 * 100)
    bar = "▓" * (prog // 5) + "░" * (20 - prog // 5)
    fire = "🔥" * min(streak, 7)
    text = f"🏆 **{title}**\n\n📊 Ур. {level} | ⭐ {xp}/{next_xp}\n{bar} {prog}%\n\n🔥 Стрик: **{streak}** {fire}\n🏅 Макс: {mx} | 💪 Всего: {tot}"
    await query.edit_message_text(text, reply_markup=back_kb(), parse_mode='Markdown')

async def show_my_workouts(query, tg_id):
    workouts = get_all_workouts(tg_id)
    if not workouts:
        await query.edit_message_text("📋 Нет тренировок, бро!", reply_markup=back_kb()); return
    text = "📋 **История:**\n\n"
    for i, (ex, w, r, s, st, d) in enumerate(workouts, 1):
        s_t = "✅" if st == 'done' else "❌" if st == 'fail' else "⏳"
        d_s = str(d)[:10] if d else ""
        text += f"{i}. {ex} — {w}кг×{r}×{s} {s_t} [{d_s}]\n"
    await query.edit_message_text(text, reply_markup=back_kb(), parse_mode='Markdown')

async def show_calories(query, tg_id):
    user = get_user(tg_id)
    if not user: await query.edit_message_text("Сначала /start"); return
    limit = user[5] or 2500
    today = get_food_today(tg_id)
    rem = limit - today
    prog = int((today / limit) * 100) if limit > 0 else 0
    bar = "▓" * (prog // 5) + "░" * (20 - prog // 5)
    text = f"🍔 **Калории:**\n\n{bar} {prog}%\n🔥 {today} / 💪 {limit}\n⚡ Осталось: {rem}\n\n"
    foods = get_food_log(tg_id)
    if foods:
        text += "**Сегодня:**\n"
        for p, c, g in foods[:5]: text += f"• {p} — {c} ккал ({g}г)\n"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Еда", callback_data="log_food"),
         InlineKeyboardButton("⚙️ Лимит", callback_data="set_cal_limit")],
        [InlineKeyboardButton("🔙 Назад", callback_data="food_menu")]
    ])
    await query.edit_message_text(text, reply_markup=kb, parse_mode='Markdown')

# ============ ОБРАБОТЧИК ТЕКСТА ============
async def handle_message(update, context):
    tg_id = update.effective_user.id
    text = update.message.text
    if tg_id not in user_data:
        await update.message.reply_text("Нажми /start, бро."); return
    step = user_data[tg_id].get("step")

    if step == "onerm_input":
        try:
            parts = text.replace("х", " ").replace("x", " ").replace("×", " ").split()
            weight = float(parts[0].replace(",", ".")); reps = int(parts[1])
            if reps < 1 or reps > 20:
                await update.message.reply_text("Повторения 1-20, бро."); return
            one_rm = calc_1rm(weight, reps)
            table = get_1rm_table(one_rm)
            txt = f"📐 **Твой 1RM: {one_rm} кг**\n\n**Рабочие веса:**\n"
            for name, w in table.items(): txt += f"• {name}: **{w} кг**\n"
            del user_data[tg_id]
            await update.message.reply_text(txt, reply_markup=back_kb(), parse_mode='Markdown')
        except: await update.message.reply_text("Формат: `80 5`", parse_mode='Markdown')
        return

    if step == "progression_input":
        try:
            parts = text.replace("х", " ").replace("x", " ").replace("×", " ").split()
            weight = float(parts[0].replace(",", ".")); reps = int(parts[1])
            advice = get_progression(weight, reps)
            del user_data[tg_id]
            await update.message.reply_text(f"Ты сделал: **{weight} кг × {reps}**\n\n{advice}", reply_markup=back_kb(), parse_mode='Markdown')
        except: await update.message.reply_text("Формат: `80 8`", parse_mode='Markdown')
        return

    if step == "subs_input":
        subs = get_subs(text)
        del user_data[tg_id]
        if subs:
            txt = f"🔄 **Замены для «{text}»:**\n\n"
            for s in subs: txt += f"• {s}\n"
            await update.message.reply_text(txt, reply_markup=back_kb(), parse_mode='Markdown')
        else:
            await update.message.reply_text("🤔 Не знаю такого.\nПопробуй: присед, жим, становая, подтягивания, тяга, отжимания, выпады, планка, бицепс, трицепс", reply_markup=back_kb())
        return

    if step == "bju_weight":
        try:
            weight = float(text.replace(",", "."))
            if weight < 30 or weight > 250:
                await update.message.reply_text("Вес 30-250 кг, бро."); return
            user_data[tg_id] = {"step": "bju_goal", "weight": weight}
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏋️ Масса", callback_data="bjugoal_mass")],
                [InlineKeyboardButton("🔥 Похудеть", callback_data="bjugoal_lose")],
                [InlineKeyboardButton("💪 Форма", callback_data="bjugoal_keep")]
            ])
            await update.message.reply_text("Какая цель?", reply_markup=kb)
        except: await update.message.reply_text("Введи число, бро.")
        return

    if step == "set_bw":
        try:
            bw = float(text.replace(",", "."))
            if bw < 30 or bw > 250:
                await update.message.reply_text("Вес 30-250 кг, бро."); return
            set_bodyweight(tg_id, bw)
            del user_data[tg_id]
            await update.message.reply_text(f"✅ Вес сохранён: **{bw} кг**", reply_markup=back_kb(), parse_mode='Markdown')
        except: await update.message.reply_text("Введи число, бро.")
        return

    if step == "ask_bw_for_std":
        try:
            bw = float(text.replace(",", "."))
            if bw < 30 or bw > 250:
                await update.message.reply_text("Вес 30-250 кг, бро."); return
            set_bodyweight(tg_id, bw)
            del user_data[tg_id]
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Жим лёжа", callback_data="std_жим")],
                [InlineKeyboardButton("Присед", callback_data="std_присед")],
                [InlineKeyboardButton("Становая", callback_data="std_становая")]
            ])
            await update.message.reply_text(f"✅ Вес {bw} кг сохранён!\n\n🎯 Выбери упражнение:", reply_markup=kb)
        except: await update.message.reply_text("Введи число, бро.")
        return

    if step == "std_input":
        lift = user_data[tg_id]["lift"]
        try:
            parts = text.replace("х", " ").replace("x", " ").replace("×", " ").split()
            weight = float(parts[0].replace(",", ".")); reps = int(parts[1])
            one_rm = calc_1rm(weight, reps)
            bw = get_bodyweight(tg_id)
            if not bw:
                await update.message.reply_text("Сначала укажи вес в «Профиль → Мой вес»"); return
            result = check_standard(lift, one_rm, bw)
            del user_data[tg_id]
            txt = f"🎯 **{STRENGTH_STANDARDS[lift]['name']}**\n\n"
            txt += f"Твой 1RM: **{one_rm} кг**\nКоэффициент: **{result['ratio']}× веса тела**\n\n"
            txt += f"Уровень: **{result['level']}**\n"
            if result['next_weight']:
                txt += f"\n🎯 До следующего: **{result['next_weight']} кг**"
            else:
                txt += "\n🏆 Ты на максимуме!"
            await update.message.reply_text(txt, reply_markup=back_kb(), parse_mode='Markdown')
        except: await update.message.reply_text("Формат: `80 5`", parse_mode='Markdown')
        return

    if step == "log_exercise":
        user_data[tg_id]["exercise"] = text
        user_data[tg_id]["step"] = "log_weight"
        await update.message.reply_text("Вес?"); return
    if step == "log_weight":
        try:
            user_data[tg_id]["weight"] = float(text.replace(",", "."))
            user_data[tg_id]["step"] = "log_reps"
            await update.message.reply_text("Повтор?")
        except: await update.message.reply_text("Число, бро.")
        return
    if step == "log_reps":
        try:
            user_data[tg_id]["reps"] = int(text)
            user_data[tg_id]["step"] = "log_sets"
            await update.message.reply_text("Подходы?")
        except: await update.message.reply_text("Целое, бро.")
        return

    if step == "log_sets":
        try:
            sets = int(text)
            ex = user_data[tg_id]["exercise"]; w = user_data[tg_id]["weight"]; r = user_data[tg_id]["reps"]
            result = save_workout(tg_id, ex, w, r, sets, 'done')
            del user_data[tg_id]
            txt = f"✅ **{ex}: {w}кг × {r} × {sets}**\n\n"
            trigger_video = False
            if result:
                txt += f"🔥 Стрик: **{result['streak']} дней**\n⭐ +50 XP | Ур. **{result['level']}**\n"
                if result.get('level_up'):
                    txt += f"\n🎉 **НОВЫЙ УРОВЕНЬ!** {get_level_title(result['level'])}"
                    trigger_video = True
                if result['streak'] in [3, 7, 14, 30, 50, 100]:
                    txt += f"\n🏆 **СТРИК {result['streak']}!** Ты машина!"
                    trigger_video = True
            await update.message.reply_text(txt, reply_markup=back_kb(), parse_mode='Markdown')
            caption = random.choice([
                "🔥 Вот так надо тренироваться!",
                "💪 Ты машина, брат!",
                "🦍 Зверь на тренировке!",
                "⚡ Мотивация для тебя!",
            ]) if trigger_video else "🔥 Продолжай в том же духе!"
            await send_motivation_video(update, caption)
        except Exception as e:
            logging.error(f"log_sets error: {e}")
            await update.message.reply_text("Ошибка.")
        return

    if step == "log_food":
        results = search_food(text)
        if not results:
            await update.message.reply_text("❌ Не найдено."); return
        kb = []
        for n, c in results[:6]:
            kb.append([InlineKeyboardButton(f"{n} — {c} ккал/100г", callback_data=f"food_{n}_{c}")])
        kb.append([InlineKeyboardButton("🔙 Назад", callback_data="food_menu")])
        user_data[tg_id] = {"step": "food_select"}
        await update.message.reply_text("Выбери:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if step == "food_select":
        if "product" not in user_data[tg_id]:
            await update.message.reply_text("Сначала выбери продукт."); return
        try:
            g = int(text)
            p = user_data[tg_id]["product"]; cp = user_data[tg_id]["cal_per_100"]
            tc = cp * g // 100
            save_food(tg_id, p, tc, g)
            del user_data[tg_id]
            user = get_user(tg_id)
            limit = user[5] if user else 2500
            eaten = get_food_today(tg_id)
            rem = limit - eaten
            txt = f"✅ **{p}** — {tc} ккал ({g}г)\n\n🍔 Съедено: {eaten}/{limit} ккал\n"
            if rem < 0:
                txt += f"⚠️ Превысил лимит на {abs(rem)} ккал!"
                caption = "🍔 Не жри лишнего, брат!"
            elif rem < 300:
                txt += f"⚡ Осталось {rem} ккал — не переедай!"
                caption = "🍗 Топливо для мышц! Но меру знай!"
            else:
                txt += f"💪 Осталось: {rem} ккал"
                caption = random.choice(["🍖 Жри правильно!", "🥩 Это топливо!", "💪 Питание — 80% результата!"])
            await update.message.reply_text(txt, reply_markup=back_kb(), parse_mode='Markdown')
            if rem < 300:
                await send_motivation_video(update, caption)
        except Exception as e:
            logging.error(f"food_select error: {e}")
            await update.message.reply_text("Число, бро.")
        return

    if step == "set_cal_limit":
        try:
            lim = int(text)
            update_cal_limit(tg_id, lim)
            del user_data[tg_id]
            await update.message.reply_text(f"✅ Лимит: {lim} ккал/день", reply_markup=back_kb())
        except: await update.message.reply_text("Число, бро.")
        return

async def bju_handler(update, context):
    q = update.callback_query
    await q.answer()
    tg_id = q.from_user.id
    if q.data.startswith("bjugoal_"):
        goal = q.data.replace("bjugoal_", "")
        weight = user_data.get(tg_id, {}).get("weight", 70)
        cal, prot, fat, carbs = calc_bju(weight, goal)
        water = round(weight * 0.03, 1)
        goal_ru = {"mass": "🏋️ Масса", "lose": "🔥 Похудение", "keep": "💪 Форма"}[goal]
        txt = f"🥗 **Твоя норма ({goal_ru}):**\n\n"
        txt += f"🔥 Калории: **{cal} ккал**\n🥩 Белки: **{prot} г**\n🧈 Жиры: **{fat} г**\n🍞 Углеводы: **{carbs} г**\n\n💧 Вода: **{water} л**"
        del user_data[tg_id]
        await q.edit_message_text(txt, reply_markup=back_kb(), parse_mode='Markdown')

# === РАСПИСАНИЕ ===
async def morning_reminder(context):
    users = get_all_users()
    for tg_id, name in users:
        try:
            prog = get_user_program(tg_id)
            if prog:
                pname, day = prog
                p = PROGRAMS.get(pname)
                if p:
                    today = p["days"][day % 7]
                    text = f"☀️ Доброе утро, {name or 'бро'}!\n\n📅 **{today['day']}**\n"
                    if today['exercises']:
                        for e in today['exercises']: text += f"• {e}\n"
                        text += "\n💪 Вперёд!"
                    else: text += "😴 Отдыхай сегодня"
                    await context.bot.send_message(chat_id=tg_id, text=text, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=tg_id, text=f"☀️ Доброе утро, {name or 'бро'}!\n\n💪 Не забудь про тренировку!")
        except Exception as e: logging.error(f"Morning {tg_id}: {e}")

async def weekly_report(context):
    users = get_all_users()
    for tg_id, name in users:
        try:
            week_count = get_week_workout_count(tg_id)
            info = get_streak_info(tg_id)
            best = get_week_stats(tg_id)
            text = f"📊 **Отчёт за неделю, {name or 'бро'}!**\n\n💪 Тренировок: **{week_count}**\n"
            if info:
                streak, mx, lvl, xp, tot = info
                text += f"🔥 Стрик: **{streak} дней**\n🏆 Уровень: **{lvl}** | ⭐ {xp} XP\n"
            if best:
                text += "\n🏋️ **Рекорды:**\n"
                for ex, w in best[:5]: text += f"• {ex}: {w} кг\n"
            if week_count >= 4: text += "\n🔥 Ты машина!"
            elif week_count >= 2: text += "\n💪 Хороший темп!"
            else: text += "\n😤 Мало тренировок. Наверстаем!"
            await context.bot.send_message(chat_id=tg_id, text=text, parse_mode='Markdown')
        except Exception as e: logging.error(f"Weekly {tg_id}: {e}")

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(bju_handler, pattern="^bjugoal_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    if app.job_queue:
        app.job_queue.run_daily(morning_reminder, time=dt.time(hour=6, minute=0), name="morning")
        app.job_queue.run_daily(weekly_report, time=dt.time(hour=16, minute=0), days=(6,), name="weekly")
    print("🚀 PumpBot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()