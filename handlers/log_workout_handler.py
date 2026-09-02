#!/usr/bin/env python3
"""Workout logging handler"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import user_exists, log_workout
import logging

logger = logging.getLogger(__name__)

LOGGING_EXERCISE, LOGGING_WEIGHT, LOGGING_REPS, LOGGING_SETS = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start workout logging"""
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await update.message.reply_text(
            "⚠️ Сначала зарегистрируйся! Используй /register"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "💪 Давайте запишем тренировку!\n\n"
        "Какое упражнение?"
    )
    return LOGGING_EXERCISE

async def exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get exercise name"""
    context.user_data['exercise'] = update.message.text
    await update.message.reply_text("⚖️ Сколько килограмм?")
    return LOGGING_WEIGHT

async def weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get weight"""
    try:
        context.user_data['weight'] = float(update.message.text)
        await update.message.reply_text("🔁 Сколько повторений?")
        return LOGGING_REPS
    except ValueError:
        await update.message.reply_text(
            "❌ Введи число, пожалуйста!"
        )
        return LOGGING_WEIGHT

async def reps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get reps"""
    try:
        context.user_data['reps'] = int(update.message.text)
        await update.message.reply_text("📦 Сколько подходов?")
        return LOGGING_SETS
    except ValueError:
        await update.message.reply_text(
            "❌ Введи число, пожалуйста!"
        )
        return LOGGING_REPS

async def sets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get sets and save workout"""
    try:
        user_id = update.effective_user.id
        sets_count = int(update.message.text)
        
        exercise = context.user_data['exercise']
        weight = context.user_data['weight']
        reps = context.user_data['reps']
        
        log_workout(user_id, exercise, weight, reps, sets_count)
        
        await update.message.reply_text(
            f"✅ Тренировка записана!\n\n"
            f"🏋️ {exercise}\n"
            f"⚖️ {weight} кг\n"
            f"🔁 {reps} повторений\n"
            f"📦 {sets_count} подходов"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ Введи число, пожалуйста!"
        )
        return LOGGING_SETS
