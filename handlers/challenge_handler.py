#!/usr/bin/env python3
"""Daily challenges handler"""

import random
from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

CHALLENGES = [
    "💪 Челленж: Сделай 50 отжиманий за день!",
    "🏃 Челленж: Пробеги 5 км!",
    "🚴 Челленж: 100 приседаний без пауз!",
    "🤸 Челленж: Планка 3 минуты!",
    "⛹️ Челленж: 200 ударов по боксёрской груше!",
    "🧘 Челленж: 10 минут йоги!",
    "🏋️ Челленж: Становая тяга в личный рекорд!",
    "🤾 Челленж: 30 бросков на точность в корзину!",
    "🚣 Челленж: 20 минут гребли!",
    "⚽ Челленж: Тренировка как футболист: 40 минут интенсива!"
]

async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send daily challenge"""
    random_challenge = random.choice(CHALLENGES)
    await update.message.reply_text(
        f"🎯 Челленж на день:\n\n{random_challenge}\n\n"
        f"Ты сможешь! 🔥"
    )
