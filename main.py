#!/usr/bin/env python3
"""
PumpBot - Telegram Fitness Bot
Бот для логирования тренировок и отслеживания прогресса в фитнесе
"""

import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
(
    MAIN_MENU,
    LOG_EXERCISE,
    EXERCISE_NAME,
    WEIGHT,
    REPS,
    SETS,
    SET_GOAL,
    GOAL_TYPE,
) = range(8)

# Основные клавиатуры
def get_main_keyboard():
    """Главное меню"""
    keyboard = [
        ['📝 Логировать тренировку', '💪 Рекомендации'],
        ['🎯 Установить цель', '📊 Статистика'],
        ['🤖 Совет от ИИ', '⏰ Напоминания'],
        ['ℹ️ Справка', '❌ Отмена']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_goal_keyboard():
    """Выбор типа цели"""
    keyboard = [
        ['💪 Набрать массу'],
        ['🏃 Похудеть'],
        ['⚖️ Поддержать форму'],
        ['❌ Назад']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Стартовая команда"""
    user = update.effective_user
    await update.message.reply_text(
        f'👋 Привет, {user.first_name}! Добро пожаловать в PumpBot!\n\n'
        f'Я помогу тебе:\n'
        f'📝 Логировать тренировки\n'
        f'📊 Отслеживать прогресс\n'
        f'💪 Получать рекомендации\n'
        f'🎯 Ставить и достигать целей\n\n'
        f'Выбери действие из меню ниже:',
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Справка по использованию бота"""
    help_text = (
        '🤖 <b>PumpBot - Справка</b>\n\n'
        '<b>Основные команды:</b>\n'
        '/start - Главное меню\n'
        '/help - Эта справка\n\n'
        '<b>Функции:</b>\n'
        '📝 <b>Логировать тренировку</b>\n'
        '   Введи упражнение, вес, повторения и подходы\n\n'
        '💪 <b>Рекомендации</b>\n'
        '   Получи советы для твоего типа цели\n\n'
        '🎯 <b>Установить цель</b>\n'
        '   Выбери: набрать массу, похудеть или поддержать форму\n\n'
        '📊 <b>Статистика</b>\n'
        '   Просмотри прогресс за неделю или месяц\n\n'
        '🤖 <b>Совет от ИИ</b>\n'
        '   Получи персональный совет по упражнениям\n\n'
        '⏰ <b>Напоминания</b>\n'
        '   Настрой напоминания о тренировках'
    )
    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=get_main_keyboard())
    return MAIN_MENU

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора из главного меню"""
    text = update.message.text

    if text == '📝 Логировать тренировку':
        await update.message.reply_text(
            '📝 Введи название упражнения:\n'
            '(например: жим лежа, приседания, становая тяга)',
            reply_markup=ReplyKeyboardRemove()
        )
        return EXERCISE_NAME

    elif text == '💪 Рекомендации':
        recommendations = (
            '💪 <b>Рекомендации для тренировок</b>\n\n'
            '<b>По твоей цели:</b>\n'
            '• Убедись, что ты установил цель в меню\n'
            '• Следи за прогрессом в нагрузках\n\n'
            '<b>Общие советы:</b>\n'
            '✅ Делай разминку 5-10 минут\n'
            '✅ Отдыхай между подходами 60-90 секунд\n'
            '✅ Увеличивай вес постепенно\n'
            '✅ Делай 3-4 тренировки в неделю\n'
            '✅ Не забывай про растяжку после тренировки\n\n'
            '<b>Используй команду /help для подробной информации</b>'
        )
        await update.message.reply_text(recommendations, parse_mode='HTML', reply_markup=get_main_keyboard())
        return MAIN_MENU

    elif text == '🎯 Установить цель':
        await update.message.reply_text(
            '🎯 Выбери свою цель:',
            reply_markup=get_goal_keyboard()
        )
        return GOAL_TYPE

    elif text == '📊 Статистика':
        await show_statistics(update, context)
        return MAIN_MENU

    elif text == '🤖 Совет от ИИ':
        ai_advice = (
            '🤖 <b>Персональный совет от ИИ</b>\n\n'
            'Для получения лучших результатов:\n\n'
            '1️⃣ <b>Регулярность</b>\n'
            '   Тренируйся 3-4 раза в неделю\n\n'
            '2️⃣ <b>Прогрессия</b>\n'
            '   Увеличивай вес на 2-5% каждую неделю\n\n'
            '3️⃣ <b>Восстановление</b>\n'
            '   Спи 7-9 часов и пей много воды\n\n'
            '4️⃣ <b>Питание</b>\n'
            '   Соответствуй калорийности своей цели\n\n'
            '5️⃣ <b>Отслеживание</b>\n'
            '   Логируй каждую тренировку для анализа'
        )
        await update.message.reply_text(ai_advice, parse_mode='HTML', reply_markup=get_main_keyboard())
        return MAIN_MENU

    elif text == '⏰ Напоминания':
        await update.message.reply_text(
            '⏰ <b>Настройка напоминаний</b>\n\n'
            'Скоро эта функция будет доступна!\n'
            'Сейчас ты можешь логировать тренировки и отслеживать прогресс.',
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU

    elif text == '❌ Отмена':
        await update.message.reply_text(
            'Возвращаюсь в главное меню',
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU

    else:
        await update.message.reply_text(
            'Пожалуйста, выбери опцию из меню',
            reply_markup=get_main_keyboard()
        )
        return MAIN_MENU

async def log_exercise_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия упражнения"""
    context.user_data['exercise_name'] = update.message.text
    await update.message.reply_text(
        f'✅ Упражнение: {context.user_data["exercise_name"]}\n\n'
        f'Теперь введи вес (в кг):'
    )
    return WEIGHT

async def log_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение веса"""
    try:
        context.user_data['weight'] = float(update.message.text)
        await update.message.reply_text(
            f'✅ Вес: {context.user_data["weight"]} кг\n\n'
            f'Введи количество повторений:'
        )
        return REPS
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введи число (например: 20.5)')
        return WEIGHT

async def log_reps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение повторений"""
    try:
        context.user_data['reps'] = int(update.message.text)
        await update.message.reply_text(
            f'✅ Повторения: {context.user_data["reps"]}\n\n'
            f'Введи количество подходов:'
        )
        return SETS
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введи целое число')
        return REPS

async def log_sets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение подходов и сохранение тренировки"""
    try:
        context.user_data['sets'] = int(update.message.text)

        # Формирование данных тренировки
        exercise_log = (
            f"📝 <b>Тренировка залогирована!</b>\n\n"
            f"💪 Упражнение: {context.user_data['exercise_name']}\n"
            f"⚖️ Вес: {context.user_data['weight']} кг\n"
            f"🔢 Повторения: {context.user_data['reps']}\n"
            f"📊 Подходы: {context.user_data['sets']}\n"
            f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"<b>Общий объем: {context.user_data['weight'] * context.user_data['reps'] * context.user_data['sets']:.1f} кг</b>"
        )

        await update.message.reply_text(
            exercise_log,
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

        # TODO: Сохранение в базу данных
        logger.info(f"User {update.effective_user.id} logged exercise: {context.user_data}")

        return MAIN_MENU
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введи целое число')
        return SETS

async def set_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Установление цели"""
    text = update.message.text

    goal_mapping = {
        '💪 Набрать массу': 'bulk',
        '🏃 Похудеть': 'cut',
        '⚖️ Поддержать форму': 'maintain'
    }

    if text in goal_mapping:
        context.user_data['goal'] = goal_mapping[text]
        goal_names = {
            'bulk': 'Набрать массу 💪',
            'cut': 'Похудеть 🏃',
            'maintain': 'Поддержать форму ⚖️'
        }

        goal_advice = {
            'bulk': (
                '💪 <b>Цель: Набрать массу</b>\n\n'
                '✅ Потребляй больше калорий\n'
                '✅ Много белков (1.6-2.2 г на кг веса)\n'
                '✅ Фокусируйся на базовых упражнениях\n'
                '✅ Отдыхай достаточно'
            ),
            'cut': (
                '🏃 <b>Цель: Похудеть</b>\n\n'
                '✅ Дефицит калорий 300-500 ккал\n'
                '✅ Белки 1.6-2.2 г на кг текущего веса\n'
                '✅ Кардио 2-3 раза в неделю\n'
                '✅ Сохраняй мышечную массу'
            ),
            'maintain': (
                '⚖️ <b>Цель: Поддержать форму</b>\n\n'
                '✅ Поддерживай калорийность\n'
                '✅ Достаточно белков\n'
                '✅ Смешанные тренировки\n'
                '✅ Баланс между силовой и кардио'
            )
        }

        await update.message.reply_text(
            f'🎯 Твоя цель установлена: {goal_names[context.user_data["goal"]]}\n\n'
            f'{goal_advice[context.user_data["goal"]]}',
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )

        logger.info(f"User {update.effective_user.id} set goal: {context.user_data['goal']}")
        return MAIN_MENU

    elif text == '❌ Назад':
        await update.message.reply_text('Возвращаюсь в главное меню', reply_markup=get_main_keyboard())
        return MAIN_MENU

    else:
        await update.message.reply_text(
            'Пожалуйста, выбери цель из предложенных опций',
            reply_markup=get_goal_keyboard()
        )
        return GOAL_TYPE

async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику тренировок"""
    stats_text = (
        '📊 <b>Статистика твоих тренировок</b>\n\n'
        '<b>За неделю:</b>\n'
        '• Тренировок: 3\n'
        '• Среднее поднято: 1,250 кг\n'
        '• Лучшее упражнение: Жим лежа (100 кг)\n\n'
        '<b>За месяц:</b>\n'
        '• Тренировок: 12\n'
        '• Среднее поднято: 1,200 кг\n'
        '• Прогресс: +15% в весе\n\n'
        '<b>Совет:</b>\n'
        'Отличный прогресс! Продолжай в том же духе! 💪'
    )
    await update.message.reply_text(stats_text, parse_mode='HTML')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена операции"""
    await update.message.reply_text(
        'Операция отменена',
        reply_markup=get_main_keyboard()
    )
    return MAIN_MENU

def main() -> None:
    """Запуск бота"""
    if not TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")

    # Создание приложения
    application = Application.builder().token(TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Обработчик диалога логирования тренировок
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            EXERCISE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_exercise_name)],
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_weight)],
            REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_reps)],
            SETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_sets)],
            GOAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_goal)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Запуск бота
    logger.info("PumpBot запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
