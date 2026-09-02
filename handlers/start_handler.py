#!/usr/bin/env python3
"""Start command handler"""

from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    welcome_message = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в **PumpBot** - твоего персонального тренера для отслеживания тренировок! 💪

Я помогу тебе:
- 📝 Записывать тренировки (упражнения, вес, повторения, подходы)
- 📊 Отслеживать статистику за неделю
- 🏆 Отмечать личные достижения
- 🤖 Получать ИИ-советы по упражнениям
- 📅 Генерировать план тренировки на день
- 💬 Вдохновляться мотивационными цитатами
- 🎯 Выполнять ежедневные челленджи

Сначала зарегистрируйся, используя команду /register

Для справки введи /help
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')
    logger.info(f"User {user.id} started bot")
