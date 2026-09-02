#!/usr/bin/env python3
"""Motivational quotes handler"""

import random
from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

QUOTES = [
    "💪 Боль - это слабость, покидающая твоё тело.",
    "🔥 Невозможно строить мышцы дома. Нужно разрушить их в зале, а потом построить дома.",
    "🚀 Не считай дни, делай дни счётом.",
    "💡 Один подход - это всё, что тебе нужно. Последний.",
    "🏆 Чемпионы не рождаются, они создаются в спортзале.",
    "⚡ Твоё тело может выдержать всё. Только ум согласится с этим.",
    "🏃 Вставай, когда падаешь. Это то, о чём идёт речь.",
    "💎 Результаты занимают время. Стань терпеливым.",
    "🌟 Каждый повтор - это шанс стать сильнее.",
    "🔨 Давай сделаем это. Сейчас. Без оправданий."
]

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send motivational quote"""
    random_quote = random.choice(QUOTES)
    await update.message.reply_text(random_quote)
