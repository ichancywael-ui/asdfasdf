import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# استيراد إعدادات البوت والجروب
from config import TOKEN

# استيراد دوال تهيئة قاعدة البيانات من ملف db
from database.db import init_pool, init

# استيراد الراوترات (تأكد من مطابقة أسماء الملفات لديك)
from ichancy.ichancy_api import initialize_tokens
from handlers import user, admin, referral
from buttons import deposit  # ملف الشحن الذي يحتوي على سيرياتيل وشام كاش
# import user   # فك الحظر عن هذه الأسطر إذا كانت ملفاتك جاهزة
# import admin  

async def main():
    # 1. تفعيل تسجيل الأحداث (Logging) لعرض الأخطاء في التيرمنال بوضوح
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # 2. إنشاء كائن البوت والموزع (Dispatcher) مع ذاكرة مؤقتة للحالات
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    print("جاري الاتصال بقاعدة البيانات...")
    try:
        # 3. أول خطوة: إنشاء حوض الاتصالات (Pool) وتعبئته بالذاكرة ليتعرف عليه البوت
        await init_pool()
        print("✅ تم إنشاء حوض الاتصالات (Pool) بنجاح.")

        # 4. ثاني خطوة: إنشاء وفحص الجداول الاعتمادية
        await init()
        print("✅ تم التحقق من الجداول وإصلاحها بنجاح.")
        
        await initialize_tokens()

    except Exception as db_err:
        print(f"❌ فشل إقلاع قاعدة البيانات: {db_err}")
        return

    # 5. تضمين الراوترات (Routers) بالترتيب الصحيح
    # ملاحظة مهمة: يجب وضع راوتر الشحن (deposit) أولاً لتأمين مسار الـ FSM وحالات الشحن
    
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(referral.router)

    
    # إذا كان لديك راوترات أخرى قم بتضمينها هنا هكذا:
    # dp.include_router(user.router)
    # dp.include_router(admin.router)

    # 6. حذف أي تحديثات معلقة أرسلت للبوت أثناء إغلاقه (Webhook Cleanup)
    await bot.delete_webhook(drop_pending_updates=True)

    # 7. إطلاق البوت والبدء في استقبال رسائل المستخدمين
    print("🚀 تم الاتصال بنجاح. البوت يعمل الآن ويستقبل الطلبات...")
    try:
        await dp.start_polling(bot)
    finally:
        # إغلاق الجلسة بأمان عند إيقاف البوت
        await bot.session.close()

if __name__ == "__main__":
    try:
        # تشغيل دالة الإقلاع الرئيسية عبر asyncio
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 تم إيقاف تشغيل البوت بأمان.")
