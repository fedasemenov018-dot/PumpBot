#!/usr/bin/env python3
"""Training plan generator handler"""

import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import user_exists, get_user_info
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate training plan for today"""
    user_id = update.effective_user.id
    
    if not user_exists(user_id):
        await update.message.reply_text(
            "⚠️ Сначала зарегистрируйся! Используй /register"
        )
        return
    
    user_info = get_user_info(user_id)
    if not user_info:
        await update.message.reply_text("❌ Ошибка при получении данных пользователя.")
        return
    
    if not OPENROUTER_API_KEY:
        await update.message.reply_text(
            "⚠️ API ключ не настроен. Обратись к администратору."
        )
        return
    
    await update.message.reply_text("⏳ Генерирую план тренировки...")
    
    try:
        day_of_week = datetime.now().strftime("%A")
        
        prompt = f"""Создай план тренировки на сегодня ({day_of_week}) для человека:
- Цель: {user_info['goal']}
- Уровень: {user_info['level']}

Дай 5-6 упражнений с подробными инструкциями. Формат:
Упражнение: [название]
Подходы: [кол-во]
Повторения: [кол-во]
Отдых: [время]

Будь лаконичен и практичен."""
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты профессиональный фитнес-тренер. Создавай эффективные и безопасные тренировочные планы. Говори на русском языке."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 800
        }
        
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        plan_text = data['choices'][0]['message']['content']
        
        await update.message.reply_text(
            f"📋 План тренировки на сегодня:\n\n{plan_text}"
        )
    except Exception as e:
        logger.error(f"Training plan error: {e}")
        await update.message.reply_text(
            "❌ Ошибка при генерации плана. Попробуй позже."
        )
