from aiogram import types, Router
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
router = Router()

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# تأكد أن @dp.message و async def على نفس مستوى المحاذاة في بداية السطر
@router.message(lambda m: m.text == "🕹 أقسام ايشانسي")
async def games(m: types.Message):
    
    gamesichancy = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="ألعاب", url="https://www.ichancy.com/ar/for-test"),
                InlineKeyboardButton(text="ألعاب تلفاز", url="https://www.ichancy.com/ar/tv-bet")
            ],
            [
                InlineKeyboardButton(text="كازينو مباشر", url="https://www.ichancy.com/ar/live-casino"),
                InlineKeyboardButton(text="كازينو", url="https://www.ichancy.com/ar/casino/slots/all")
            ]
        ]
    )
    
    await m.answer(
        text="🎮 أقسام ايشانسي\n\nإختر القسم الذي تريده من الأزرار أدناه:",
        reply_markup=gamesichancy,
        parse_mode="Markdown"
    )