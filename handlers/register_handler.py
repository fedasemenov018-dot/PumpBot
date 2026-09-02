#!/usr/bin/env python3
"""User registration handler"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import user_exists, create_user
import logging

logger = logging.getLogger(__name__)

REGISTERING_NAME, REGISTERING_GOAL, REGISTERING_LEVEL = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start registration process"""
    user_id = update.effective_user.id
    
    if user_exists(user_id):
        await update.message.reply_text(
            "✅ Вы уже зарегистрированы! Используйте /help для справки."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🎯 Начнём регистрацию! 💪\n\n"
        "Как тебя зовут?"
    )
    return REGISTERING_NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user name"""
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "Спасибо! Какая твоя основная цель?\n\n"
        "Примеры: набор массы, похудение, выносливость, рельеф"
    )
    return REGISTERING_GOAL

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user goal"""
    context.user_data['goal'] = update.message.text
    await update.message.reply_text(
        "Отлично! Какой у тебя уровень подготовки?\n\n"
        "Варианты: новичок, средний, продвинутый"
    )
    return REGISTERING_LEVEL

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user level and complete registration"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    level = update.message.text
    
    name = context.user_data.get('name')
    goal = context.user_data.get('goal')
    
    create_user(user_id, username, name, goal, level)
    
    await update.message.reply_text(
        f"🎉 Регистрация завершена!\n\n"
        f"👤 Имя: {name}\n"
        f"🎯 Цель: {goal}\n"
        f"💪 Уровень: {level}\n\n"
        f"Используй /help для списка команд!"
    )
    return ConversationHandler.END
