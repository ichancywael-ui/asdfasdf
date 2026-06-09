from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

menu = ReplyKeyboardMarkup(
    keyboard=[

        [
            KeyboardButton(text="🎰 ichancy"),
            KeyboardButton(text="💳 شحن رصيد في البوت")
        ],

        [
            KeyboardButton(text="💸 سحب رصيد من البوت"),
            KeyboardButton(text="👥 نظام الاحالات")
        ],

        [
            KeyboardButton(text="🎁 كود هدية"),
            KeyboardButton(text="💝 اهداء رصيد")
        ],

        [
            KeyboardButton(text="☎️ تواصل معنا"),
            KeyboardButton(text="📨 رسالة للادمن")
        ],

        [
            KeyboardButton(text="📚 الشروحات"),
            KeyboardButton(text="📜 السجل")
        ],

        [
            KeyboardButton(text="🎡 عجلة حظ"),
            KeyboardButton(text="🏆 الجاكبوت")
        ],

        [
            KeyboardButton(text="🎉 البونصات والعروض الحالية")
        ],

        [
            KeyboardButton(text="🎮 دخول مباشر للالعاب"),
            KeyboardButton(text="🕹 أقسام ايشانسي")
        ],

        [
            KeyboardButton(text="Ichancy Apk")
        ],

        [
            KeyboardButton(text="💰 الرصيد")
        ]

    ],

    resize_keyboard=True
)

explanations = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="ما هو موقع Ichancy؟")],
        [KeyboardButton(text="كيفية شحن الرصيد ضمن بوت Ichancy")],
        [KeyboardButton(text="كيفية إنشاء حساب Ichancy جديد")],
        [KeyboardButton(text="كيفيّة سحب الرصيد من بوت Ichancy")],
        [KeyboardButton(text="كيفية شحن رصيد ضمن حساب Ichancy")],
        [KeyboardButton(text="كيفية سحب رصيد من حساب Ichancy")],
        [KeyboardButton(text="القائمة الرئيسية")],
    ],
    resize_keyboard=True
    
)

ichancymenu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="انشاء حساب Ichancy")],
        [KeyboardButton(text="القائمة الرئيسية")],
    ]
)

ichancymenuregistered = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="شحن رصيد بالحساب")],
        [KeyboardButton(text="سحب رصيد من الحساب")],
        [KeyboardButton(text="القائمة الرئيسية")],
    ]
)

adminmenu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="المستخدمين")],
        [KeyboardButton(text="حسابات ichancy")],
        [KeyboardButton(text="اضافة كود")],
        [KeyboardButton(text="📜 سجل مستخدم")],
        [KeyboardButton(text="💰 توزيع أرباح الإحالات")],  
        [KeyboardButton(text="تعديل نص البونصات و العروض الحالية")], 
        [KeyboardButton(text="اضافة او حذف البونص")], 
        [KeyboardButton(text="الإذاعة")],
        [KeyboardButton(text="القائمة الرئيسية")],
    ],
    resize_keyboard=True, 
    input_field_placeholder="👨‍✈️ لوحة تحكم الإدارة"
)


