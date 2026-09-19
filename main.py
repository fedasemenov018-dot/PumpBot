import logging
import os
import sqlite3
import random
import asyncio
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

DATABASE_URL = os.getenv("DATABASE_URL")
USE_PG = DATABASE_URL is not None
if USE_PG:
    import psycopg2
    from psycopg2 import pool as pg_pool
    _pg_pool = None

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ============ БД ============
def _init_pool():
    global _pg_pool
    if USE_PG and _pg_pool is None:
        try:
            _pg_pool = pg_pool.SimpleConnectionPool(1, 10, DATABASE_URL)
        except Exception as e:
            logging.error(f"Pool init error: {e}")
            _pg_pool = None

class ConnWrapper:
    """Обёртка: возвращает соединение в пул при close()."""
    def __init__(self, conn, from_pool=False):
        self._conn = conn
        self._from_pool = from_pool
    def cursor(self): return self._conn.cursor()
    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):
        if self._from_pool and _pg_pool:
            try: _pg_pool.putconn(self._conn)
            except Exception: pass
        else:
            try: self._conn.close()
            except Exception: pass

def get_conn():
    if USE_PG:
        _init_pool()
        if _pg_pool:
            return ConnWrapper(_pg_pool.getconn(), from_pool=True)
        return ConnWrapper(psycopg2.connect(DATABASE_URL), from_pool=False)
    return ConnWrapper(sqlite3.connect("pumpbot.db"), from_pool=False)

def adapt(q):
    return q.replace("?", "%s") if USE_PG else q

def today_clause(col="date"):
    return f"{col} >= CURRENT_DATE" if USE_PG else f"{col} >= datetime('now', 'start of day')"

def week_ago_clause(col="date"):
    return f"{col} >= CURRENT_DATE - INTERVAL '7 days'" if USE_PG else f"{col} >= datetime('now', '-7 days')"

# ============ ВИДЕО ============
TREN_VIDEOS = {
    "workout": "https://t.me/fpfpldf/10?embed=1",
    "food": "https://t.me/fpfpldf/11?embed=1"
}

async def send_tren_video(update, video_type, caption):
    link = TREN_VIDEOS.get(video_type)
    if link:
        try:
            await update.message.reply_video(video=link, caption=caption, supports_streaming=True)
        except Exception as e:
            logging.error(f"Video error: {e}")
            await update.message.reply_text(caption)
    else:
        await update.message.reply_text(caption)

# ============ БАЗА ПРОДУКТОВ ============
FOOD_DB = {
    "курица": 165, "куриная грудка": 165, "куриное филе": 110, "куриная ножка": 180,
    "говядина": 250, "говяжий фарш": 270, "свинина": 320, "свиной фарш": 340,
    "баранина": 280, "индейка": 130, "утка": 350, "кролик": 156,
    "печень": 130, "куриная печень": 140, "говяжья печень": 130, "сердце": 160,
    "лосось": 200, "семга": 200, "тунец": 130, "скумбрия": 180,
    "сельдь": 160, "треска": 75, "минтай": 70, "окунь": 120,
    "щука": 90, "судак": 85, "лещ": 110, "карась": 85,
    "карп": 100, "форель": 150, "горбуша": 140,
    "креветки": 90, "кальмар": 100, "мидии": 80,
    "яйцо": 155, "яйца": 155, "яичный белок": 45, "яичный желток": 320,
    "молоко": 60, "кефир": 50, "ряженка": 55, "йогурт": 60,
    "творог": 120, "творог обезжиренный": 80, "сметана": 200, "сметана 15%": 150,
    "сливки": 300, "сыр": 350, "пармезан": 400, "моцарелла": 300, "фета": 260,
    "масло сливочное": 750, "маргарин": 720,
    "рис": 130, "гречка": 110, "овсянка": 80, "геркулес": 85,
    "манка": 120, "перловка": 130, "пшено": 140, "кукурузная крупа": 150,
    "макароны": 130, "вермишель": 130, "спагетти": 130, "лапша": 140,
    "хлеб": 250, "хлеб черный": 200, "батон": 260, "лаваш": 270,
    "картофель": 80, "батат": 90, "морковь": 35, "свекла": 43,
    "лук": 40, "чеснок": 149, "помидор": 18, "огурец": 15,
    "перец болгарский": 26, "кабачок": 17, "тыква": 26, "брокколи": 34,
    "цветная капуста": 25, "капуста": 28, "сельдерей": 16, "спаржа": 20,
    "горошек": 80, "кукуруза": 100, "редис": 16, "салат": 15, "шпинат": 23,
    "банан": 90, "яблоко": 52, "груша": 57, "апельсин": 47, "мандарин": 38,
    "лимон": 34, "грейпфрут": 35, "виноград": 65, "арбуз": 30, "дыня": 35,
    "персик": 45, "абрикос": 48, "слива": 42, "вишня": 50, "черешня": 52,
    "клубника": 32, "малина": 42, "черника": 44, "голубика": 40, "смородина": 45,
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

# ============ БД: СХЕМА + МИГРАЦИИ ============
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

    # ---- миграции (добавляем колонки, если их нет) ----
    _safe_add_column(c, "users", "tz_offset", "INTEGER DEFAULT 0")
    _safe_add_column(c, "users", "remind_morning", "INTEGER DEFAULT 1")
    _safe_add_column(c, "users", "remind_evening", "INTEGER DEFAULT 1")
    _safe_add_column(c, "users", "morning_hour", "INTEGER DEFAULT 10")
    _safe_add_column(c, "users", "evening_hour", "INTEGER DEFAULT 20")

    conn.commit(); conn.close()

def _safe_add_column(cursor, table, column, definition):
    """Добавляет колонку, если её нет. Работает в PG и SQLite."""
    try:
        if USE_PG:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
        else:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [r[1] for r in cursor.fetchall()]
            if column not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except Exception as e:
        logging.warning(f"Migration skip {table}.{column}: {e}")

# ============ ПОЛЬЗОВАТЕЛЬ ============
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

def update_tz(tg_id, tz_offset):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("UPDATE users SET tz_offset = ? WHERE tg_id = ?"), (tz_offset, tg_id))
    conn.commit(); conn.close()

def update_reminders(tg_id, morning, evening):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("UPDATE users SET remind_morning = ?, remind_evening = ? WHERE tg_id = ?"),
              (1 if morning else 0, 1 if evening else 0, tg_id))
    conn.commit(); conn.close()

def get_tz_offset(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT tz_offset FROM users WHERE tg_id = ?"), (tg_id,))
    r = c.fetchone(); conn.close()
    return r[0] if r and r[0] is not None else 0

def local_now(tg_id):
    """Локальное время юзера (naive datetime)."""
    return datetime.utcnow() + timedelta(hours=get_tz_offset(tg_id))

def local_today_str(tg_id):
    return local_now(tg_id).strftime("%Y-%m-%d")

# ============ ЕДА ============
def save_food(tg_id, product, cal, grams):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if u:
        c.execute(adapt("INSERT INTO food_log (user_id, product, calories, grams, date) VALUES (?, ?, ?, ?, ?)"),
                  (u[0], product, cal, grams, datetime.utcnow()))
        conn.commit()
    conn.close()

def get_food_today(tg_id):
    # границы локального дня в UTC
    off = get_tz_offset(tg_id)
    now_local = datetime.utcnow() + timedelta(hours=off)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local - timedelta(hours=off)
    end_utc = end_local - timedelta(hours=off)

    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT SUM(calories) FROM food_log WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND date >= ? AND date < ?"),
              (tg_id, start_utc, end_utc))
    t = c.fetchone()[0]; conn.close(); return t or 0

def get_food_log(tg_id):
    off = get_tz_offset(tg_id)
    now_local = datetime.utcnow() + timedelta(hours=off)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    start_utc = start_local - timedelta(hours=off)
    end_utc = end_local - timedelta(hours=off)

    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT product, calories, grams FROM food_log WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND date >= ? AND date < ? ORDER BY date DESC"),
              (tg_id, start_utc, end_utc))
    f = c.fetchall(); conn.close(); return f

# ============ СТРИКИ / XP ============
def update_streak_and_xp(tg_id, xp_gain=50):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if not u:
        conn.close(); return None
    uid = u[0]
    today = local_today_str(tg_id)
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
    # вчера по локальному времени
    yest = (local_now(tg_id) - timedelta(days=1)).strftime("%Y-%m-%d")
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

# ============ ТРЕНИРОВКИ ============
def save_workout(tg_id, exercise, weight, reps, sets, status='done'):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT id FROM users WHERE tg_id = ?"), (tg_id,))
    u = c.fetchone()
    if not u:
        conn.close(); return None
    uid = u[0]
    c.execute(adapt("INSERT INTO workouts (user_id, exercise, weight, reps, sets, status, date) VALUES (?, ?, ?, ?, ?, ?, ?)"),
              (uid, exercise, weight, reps, sets, status, datetime.utcnow()))
    c.execute(adapt("SELECT max_weight FROM achievements WHERE user_id = ? AND exercise = ?"), (uid, exercise))
    a = c.fetchone()
    if not a:
        c.execute(adapt("INSERT INTO achievements (user_id, exercise, max_weight, date) VALUES (?, ?, ?, ?)"),
                  (uid, exercise, weight, datetime.utcnow()))
    elif weight > a[0]:
        c.execute(adapt("UPDATE achievements SET max_weight = ?, date = ? WHERE user_id = ? AND exercise = ?"),
                  (weight, datetime.utcnow(), uid, exercise))
    conn.commit(); conn.close()
    if status == 'done':
        return update_streak_and_xp(tg_id, 50)
    return None

def get_today_workouts(tg_id):
    off = get_tz_offset(tg_id)
    now_local = datetime.utcnow() + timedelta(hours=off)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = start_local - timedelta(hours=off)

    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT exercise, weight, reps, sets, status FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND date >= ? ORDER BY date DESC"),
              (tg_id, start_utc))
    w = c.fetchall(); conn.close(); return w

def get_week_stats(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt(f"SELECT exercise, MAX(weight) FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND {week_ago_clause()} AND status = 'done' GROUP BY exercise"), (tg_id,))
    b = c.fetchall(); conn.close(); return b

def get_all_workouts(tg_id):
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT exercise, weight, reps, sets, status, date FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) ORDER BY date DESC LIMIT 20"), (tg_id,))
    w = c.fetchall(); conn.close(); return w

def get_last_workout_for_exercise(tg_id, exercise):
    """Последняя запись по упражнению (для автоподстановки)."""
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT weight, reps, sets FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND LOWER(exercise) = LOWER(?) ORDER BY date DESC LIMIT 1"),
              (tg_id, exercise))
    r = c.fetchone(); conn.close(); return r

def get_exercise_history(tg_id, exercise, limit=15):
    """История по упражнению (для графика)."""
    conn = get_conn(); c = conn.cursor()
    c.execute(adapt("SELECT weight, reps, date FROM workouts WHERE user_id = (SELECT id FROM users WHERE tg_id = ?) AND LOWER(exercise) = LOWER(?) AND status = 'done' ORDER BY date DESC LIMIT ?"),
              (tg_id, exercise, limit))
    r = c.fetchall(); conn.close(); return r

# ============ УРОВНИ ============
LEVEL_TITLES = {1: "🥚 Новичок", 2: "🏃 Бегун", 3: "💪 Качок", 4: "🔥 Зверь",
                5: "🦍 Горилла", 6: "👹 Монстр", 7: "🐉 Дракон", 8: "⚡ Легенда"}
def get_level_title(l): return LEVEL_TITLES.get(l, "⚡ Легенда")

# ============ ЗАМЕНА УПРАЖНЕНИЙ ============
EXERCISE_SUBS = {
    "присед": ["🦵 Болгарский выпад", "🦵 Гоблет-присед", "🦵 Жим ногами", "🦵 Фронтальный присед"],
    "жим": ["💪 Жим гантелей", "💪 Отжимания с весом", "💪 Жим в Смите", "💪 Отжимания на брусьях"],
    "жим лежа": ["💪 Жим гантелей", "💪 Отжимания с весом", "💪 Жим в Смите", "💪 Отжимания на брусьях"],
    "становая": ["🔥 Румынская тяга", "🔥 Гиперэкстензия", "🔥 Тяга на прямых ногах", "🔥 Гуд-морнинг"],
    "подтягивания": ["🏋️ Тяга верхнего блока", "🏋️ Тяга в наклоне", "🏋️ Австралийские подтягивания"],
    "тяга": ["🏋️ Тяга гантели", "🏋️ Тяга блока", "🏋️ Тяга Т-грифа"],
    "отжимания": ["💪 Жим лежа", "💪 Жим гантелей", "💪 Отжимания на брусьях"],
    "выпады": ["🦵 Болгарский выпад", "🦵 Зашагивания на платформу", "🦵 Присед на одной ноге"],
    "планка": ["🎯 Скручивания", "🎯 Велосипед", "🎯 Подъём ног в висе", "🎯 Ролл-аут"],
    "бицепс": ["💪 Молотки", "💪 Подъём на скамье Скотта", "💪 Концентрированный подъём"],
    "трицепс": ["💪 Французский жим", "💪 Разгибания на блоке", "💪 Отжимания узким хватом"],
    "жим ногами": ["🦵 Присед", "🦵 Гакк-присед", "🦵 Выпады"],
}

def get_subs(name):
    name = name.lower().strip()
    for key in EXERCISE_SUBS:
        if key in name:
            return EXERCISE_SUBS[key]
    return None

# ============ ПРОГРЕССИЯ ============
def get_progression(weight, reps):
    if reps <= 5:
        return f"📈 Попробуй **{weight + 5} кг × {reps}** или **{weight} кг × {reps + 1}**"
    elif reps <= 8:
        return f"📈 Попробуй **{weight + 2.5} кг × {reps}** или **{weight} кг × {reps + 1}**"
    elif reps <= 12:
        return f"📈 Попробуй **{weight + 1.25} кг × {reps}** или **{weight} кг × {reps + 2}**"
    else:
        return f"📈 Попробуй **{weight + 2.5} кг × 8** — ты уже сильный 💪"

# ============ 1RM ============
def calc_1rm(weight, reps):
    if reps == 1:
        return weight
    one_rm = weight * (1 + reps / 30)
    return round(one_rm, 1)

def get_1rm_table(one_rm):
    return {
        "100% (1 раз)": round(one_rm),
        "95% (2 раза)": round(one_rm * 0.95, 1),
        "90% (4 раза)": round(one_rm * 0.90, 1),
        "85% (6 раз)": round(one_rm * 0.85, 1),
        "80% (8 раз)": round(one_rm * 0.80, 1),
        "75% (10 раз)": round(one_rm * 0.75, 1),
        "70% (12 раз)": round(one_rm * 0.70, 1),
    }

# ============ БЖУ ============
def calc_bju(weight, goal):
    if goal == "mass":
        cal = weight * 33
        protein = weight * 2.0
        fat = weight * 1.0
    elif goal == "lose":
        cal = weight * 25
        protein = weight * 2.2
        fat = weight * 0.8
    else:
        cal = weight * 28
        protein = weight * 1.8
        fat = weight * 1.0
    carbs = (cal - protein * 4 - fat * 9) / 4
    return round(cal), round(protein), round(fat), round(carbs)

# ============ СОВЕТ ДНЯ ============
DAILY_TIPS = [
    "💧 Пей 30 мл воды на кг веса",
    "😴 Спи 7-9 часов — мышцы растут во сне",
    "🥩 Ешь 1.6-2 г белка на кг веса",
    "🔥 Разминка 5-10 мин перед тренировкой",
    "📈 Прогрессия важнее идеальной техники",
    "💪 Не качай одну группу чаще 2-3 раз в неделю",
    "🏃 Кардио после силовой — жиросжигание +20%",
    "🍔 80% результата — питание",
]
def get_tip_of_day():
    return DAILY_TIPS[datetime.now().day % len(DAILY_TIPS)]

# ============ ASCII-ГРАФИК ============
def ascii_chart(values, labels, width=20):
    """Простой горизонтальный ASCII-график. values — числа, labels — подписи."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    lines = []
    for v, lbl in zip(values, labels):
        n = int((v - mn) / rng * width)
        bar = "▓" * max(n, 1)
        lines.append(f"{lbl} | {bar} {v}")
    return "\n".join(lines)

# ============ БОТ ============
user_data = {}

async def start(update, context):
    tg_id = update.effective_user.id
    user = get_user(tg_id)
    if user:
        await show_main_menu(update, context, user)
    else:
        user_data[tg_id] = {"step": "goal"}
        kb = [[InlineKeyboardButton("🏋️ Масса", callback_data="goal_mass")],
              [InlineKeyboardButton("🔥 Похудеть", callback_data="goal_lose")],
              [InlineKeyboardButton("💪 Форма", callback_data="goal_keep")]]
        await update.message.reply_text(f"Йо, {update.effective_user.first_name}! 💪 Цель?", reply_markup=InlineKeyboardMarkup(kb))

async def show_main_menu(update, context, user=None):
    tg_id = update.effective_user.id
    if not user:
        user = get_user(tg_id)
    kb = [
        [InlineKeyboardButton("🏋️ Тренировка", callback_data="training"),
         InlineKeyboardButton("📊 Прогресс", callback_data="progress")],
        [InlineKeyboardButton("🍔 Еда", callback_data="calories"),
         InlineKeyboardButton("🥗 БЖУ и вода", callback_data="bju")],
        [InlineKeyboardButton("📐 1RM", callback_data="onerm"),
         InlineKeyboardButton("📈 Прогрессия", callback_data="progression")],
        [InlineKeyboardButton("🔄 Замена упражнений", callback_data="subs")],
        [InlineKeyboardButton("⏱️ Таймер отдыха", callback_data="timer")],
        [InlineKeyboardButton("🏆 Уровень", callback_data="my_level"),
         InlineKeyboardButton("💡 Совет", callback_data="tip_of_day")],
        [InlineKeyboardButton("⚙️ Профиль", callback_data="profile"),
         InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    text = f"Чё качаем, {user[2] if user else 'бро'}? 💪"
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update, context):
    q = update.callback_query
    await q.answer()
    tg_id = q.from_user.id
    data = q.data
    back_kb = [[InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]]

    if data.startswith("goal_"):
        goal = data.replace("goal_", "")
        user_data[tg_id] = {"step": "level", "goal": goal}
        kb = [[InlineKeyboardButton("🟢 Новичок", callback_data="level_beginner")],
              [InlineKeyboardButton("🟡 Средний", callback_data="level_intermediate")],
              [InlineKeyboardButton("🔴 Про", callback_data="level_advanced")]]
        await q.edit_message_text("Уровень?", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("level_"):
        level = data.replace("level_", "")
        goal = user_data[tg_id]["goal"]
        add_user(tg_id, q.from_user.first_name, goal, level)
        del user_data[tg_id]
        await show_main_menu(update, context, get_user(tg_id))
        return

    if data == "training":
        kb = [[InlineKeyboardButton("➕ Записать", callback_data="log")],
              [InlineKeyboardButton("📋 История", callback_data="my_workouts")],
              [InlineKeyboardButton("📈 График упражнения", callback_data="ex_graph")],
              [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        await q.edit_message_text("🏋️ Тренировка:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "progress":
        await show_progress(q, tg_id); return
    if data == "my_level":
        await show_level(q, tg_id); return

    if data == "tip_of_day":
        await q.edit_message_text(f"💡 {get_tip_of_day()
