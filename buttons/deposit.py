import aiohttp  # استبدال requests بـ aiohttp للأسنك
from aiogram import types, Router, F  # تم استيراد F لاستخدامه كفلتر متقدم وآمن
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# استيراد الحوض والدوال بنظام الأسنك
from database.db import (
    db_pool,
    add_balance,
    is_tx_used,
    save_tx,
    add_transaction,
    process_deposit_commission,
    get_deposit_bonus_rate,
    check_and_add_pending_deposit,
    fetch_and_delete_pending,
    delete_pending_only
)

from config import GROUP_ID, GSM, API_KEY

class SyriatelState(StatesGroup):
    process = State()
    amount = State()

router = Router()

# ========================= شحن رصيد =========================
@router.message(F.text == "💳 شحن رصيد في البوت")
async def deposit(m: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 سيرياتيل كاش")],
            [KeyboardButton(text="💳 شام كاش")],
            [KeyboardButton(text="القائمة الرئيسية")],
        ],
        resize_keyboard=True
    )
    await m.answer("💳 اختر طريقة الشحن:", reply_markup=kb)

# ========================= سيرياتيل كاش =========================
@router.message(F.text == "📱 سيرياتيل كاش")
async def syriatelcashD(m: types.Message, state: FSMContext):
    await state.clear()  # تصفية أي حالات سابقة لتفادي التعليق الافتراضي
    await m.answer(
        "📱 يرجى تحويل المبلغ عن طريق الشحن اليدوي\n\n"
        "📞 الأرقام المتاحة:\n\n"
        f"1️⃣ {11095128}\n"
        "2️⃣ \n"
        "3️⃣ \n\n"
        "🧾 أرسل رقم العملية",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(SyriatelState.process)

# ========================= رقم العملية =========================
@router.message(SyriatelState.process)
async def process_number_syriatelcach(m: types.Message, state: FSMContext):
    tx_text = m.text.strip()
    if not tx_text:
        await m.answer("❌ يرجى إرسال رقم عملية صحيح")
        return
        
    await state.update_data(process=tx_text)
    await m.answer("💰 أرسل المبلغ المحول")
    await state.set_state(SyriatelState.amount)

# ========================= المبلغ =========================
@router.message(SyriatelState.amount)
async def process_amount_syriatelCash(m: types.Message, state: FSMContext):
    data = await state.get_data()
    process = data.get("process")

    try:
        amount = int(m.text.strip())
    except ValueError:
        await m.answer("❌ أرسل مبلغ صحيح (أرقام فقط)")
        return

    uid = m.from_user.id
    success = await check_and_add_pending_deposit(user_id=uid, amount=amount, tx_type= "SyriatelCash")
    if not success:
        await m.answer("❌ لديك طلب قيد المراجعة سابقاً بالفعل.")
        await state.clear()
        return
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ قبول", callback_data=f"acceptD_SY_{uid}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"rejectD_SY_{uid}")
            ]
        ]
    )

    await m.answer("⏳ انتظر قليلاً للتحقق من العملية من قبل الإدارة")
    
    try:
        await m.bot.send_message(
            GROUP_ID,
            f"📥 طلب شحن جديد\n\n"
            f"نوع الشحن: SyriatelCash\n\n"
            f"👤 ID المستخدم: {uid}\n"
            f"🧾 رقم العملية: {process}\n"
            f"💰 المبلغ: {amount} ل.س",
            reply_markup=kb
        )
    except Exception as e:
        print(f"فشل إرسال الإشعار للجروب: {e}")
        await m.answer("⚠️ حدثت مشكلة أثناء إرسال طلبك للإدارة.")
        
    await state.clear()
    # ========================= قبول العملية =========================

@router.callback_query(F.data.startswith("acceptD_SY_"))
async def accept_syriatelcash(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])

    amount = await fetch_and_delete_pending(uid)

    if amount is None:
        await call.answer("❌ العملية غير موجودة أو تم معالجتها مسبقاً", show_alert=True)
        return

    await add_transaction(
        user_id=uid,
        tx_type="deposit",
        amount=amount,
        status="completed",
        txid="SyriatelCash"
    )
    
    await call.message.edit_text(call.message.text + "\n\n✅ تم قبول العملية بنجاح!")

    await process_deposit_commission(user_id=uid, deposit_amount=amount)
    
    bonus_rate = await get_deposit_bonus_rate()
    bonus_amount = amount * bonus_rate
    total_amount = amount + bonus_amount
    
    await add_balance(uid, total_amount)
    
    try:
        if bonus_amount > 0:
            await call.bot.send_message(
                uid,
                f"✅ تم تأكيد شحن حسابك بمبلغ {amount} ل.س وبسبب وجود بونص شحن بقيمة {bonus_rate*100}% تم إضافة {bonus_amount} ل.س مكافأة لحسابك! الرصيد المضاف كلياً: {total_amount} ل.س"
            )
        else:
            await call.bot.send_message(
                uid,
                f"✅ تم تأكيد العملية\n\n💰 تم إضافة {amount} إلى رصيدك"
            )
    except Exception as e:
        print(f"تعذر إرسال رسالة للمستخدم {uid}: {e}")

# ========================= رفض العملية =========================
@router.callback_query(F.data.startswith("rejectD_SY_"))
async def rejectsyriatelcash(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])

    await delete_pending_only(uid)
    
    await call.message.edit_text(call.message.text + "\n\n❌ تم رفض العملية")
    try:
        await call.bot.send_message(uid, "❌ يوجد خطأ بالعملية، يرجى التحقق منها وتعديل البيانات المعطاة.")
    except Exception as e:
        print(f"تعذر مراسلة المستخدم المرفوض: {e}")





# ========================== شام كاش =========================
@router.message(F.text == "💳 شام كاش")
async def shamcashD(m: types.Message, state: FSMContext):
    await state.clear()  # تصفية أي حالات سابقة لتفادي التعليق الافتراضي
    await m.answer(
        "يجب التواصل مع الدعم للسحب عن طريث شام كاش\n"
        "تواصل هنا👇/n"
        "@SHARK_SUPPORT_ICHANCY7",
        reply_markup=kb
    )


