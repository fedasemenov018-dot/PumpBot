#!/usr/bin/env python3
"""Achievements handler"""

from telegram import Update
from telegram.ext import ContextTypes
from database import user_exists, get_achievements
import logging

logger = logging.getLogger(__name__)

async def achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user achievements"""
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await update.message.reply_text(
            "⚠️ Сначала зарегистрируйся! Используй /register"
        )
        return
    
    results = get_achievements(user_id)
    
    if not results:
        await update.message.reply_text(
            "🏆 Пока нет достижений. Начни тренироваться! 💪"
        )
        return
    
    message = "🏆 Твои личные рекорды:\n\n"
    for i, row in enumerate(results, 1):
        message += f"{i}. 🏋️ {row['exercise']}: {row['max_weight']} кг\n"
    
    await update.message.reply_text(message)
