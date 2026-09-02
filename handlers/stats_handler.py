#!/usr/bin/env python3
"""Weekly statistics handler"""

from telegram import Update
from telegram.ext import ContextTypes
from database import user_exists, get_week_stats
import logging

logger = logging.getLogger(__name__)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show weekly statistics"""
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await update.message.reply_text(
            "⚠️ Сначала зарегистрируйся! Используй /register"
        )
        return
    
    results = get_week_stats(user_id)
    
    if not results:
        await update.message.reply_text(
            "📊 Пока нет данных за эту неделю. Запиши тренировку! 💪"
        )
        return
    
    message = "📊 Статистика за неделю:\n\n"
    for row in results:
        message += (
            f"🏋️ {row['exercise']}\n"
            f"  • Тренировок: {row['count']}\n"
            f"  • Подходов: {row['total_sets']}\n"
            f"  • Повторений: {row['total_reps']}\n"
            f"  • Максимум: {row['max_weight']} кг\n\n"
        )
    
    await update.message.reply_text(message)
