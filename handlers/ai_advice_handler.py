#!/usr/bin/env python3
"""AI advice handler using OpenRouter"""

import os
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import user_exists
import requests

logger = logging.getLogger(__name__)

AI_QUESTION = 0

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start AI advice conversation"""
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await update.message.reply_text(
            "⚠️ Сначала зарегистрируйся! Используй /register"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🤖 Я помогу тебе с советами по упражнениям!\n\n"
        "О чём хочешь узнать?"
    )
    return AI_QUESTION

async def question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get AI advice"""
    if not OPENROUTER_API_KEY:
        await update.message.reply_text(
            "⚠️ API ключ не настроен. Обратись к администратору."
        )
        return ConversationHandler.END
    
    user_question = update.message.text
    await update.message.reply_text("⏳ Думаю...")
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты опытный фитнес-тренер. Давай краткие, практичные советы по упражнениям и тренировкам. Говори на русском языке. Максимум 300 символов."
                },
                {
                    "role": "user",
                    "content": user_question
                }
            ],
            "max_tokens": 300
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        advice = data['choices'][0]['message']['content']
        
        await update.message.reply_text(
            f"🤖 Совет:\n\n{advice}"
        )
    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text(
            "❌ Ошибка при получении совета. Попробуй позже."
        )
    
    return ConversationHandler.END
