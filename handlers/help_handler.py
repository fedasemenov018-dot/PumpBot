#!/usr/bin/env python3
"""Help command handler"""

from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    help_text = """📖 Доступные команды:

🔐 Регистрация:
/register - Зарегистрироваться в боте

💪 Тренировки:
/log - Записать тренировку
/stats - Статистика за неделю
/achievements - Твои личные рекорды

🤖 ИИ помощник:
/ai - Получить совет по упражнениям
/plan - Генерировать план на день

🎯 Мотивация:
/quote - Мотивационная цитата
/challenge - Челленж на день

❌ Отмена:
/cancel - Отменить текущую операцию
"""
    await update.message.reply_text(help_text)
