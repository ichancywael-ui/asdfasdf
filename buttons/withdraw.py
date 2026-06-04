from aiogram import types, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# استيراد الحوض والدوال بنظام الأسنك
from database.db import db_pool, get_balance, add_transaction, check_and_add_pending_withdraw, accept_pending_withdraw_db, reject_pending_withdraw_db

from config import GROUP_ID

class SyriatelStateW(StatesGroup):
    process = State()
    amount = State()

class ShamCashStateW(StatesGroup):
    process = State()
    amount = State()

class UsdtStateW(StatesGroup):
    process = State()
    amount = State()

router = Router()

# ========================= سحب =========================
@router.message(lambda m: m.text == "💸 سحب رصيد من البوت")
async def withdraw(m: types.Message):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="W 📱 سيرياتيل كاش")],
            [KeyboardButton(text="W 💳 شام كاش")],
            [KeyboardButton(text="القائمة الرئيسية")],
        ],
        resize_keyboard=True
    )
    await m.answer("💳 اختر طريقة السحب:", reply_markup=kb)

# ========================= سيرياتيل كاش سحب =========================
@router.message(lambda m: m.text == "W 📱 سيرياتيل كاش")
async def syriatelW(m: types.Message, state: FSMContext):
    await state.clear()  # تنظيف أي حالة سابقة منعاً للتعليق
    await m.answer("📱 أرسل رقم الهاتف الذي تريد السحب عليه:")
    await state.set_state(SyriatelStateW.process)

# ========================= رقم الهاتف =========================
@router.message(SyriatelStateW.process)
async def process_number_syriatel(m: types.Message, state: FSMContext):
    tx = m.text.strip()
    if not tx.isdigit():
        await m.answer("❌ أدخل رقم هاتف صحيح (أرقام فقط)")
        return
        
    await state.update_data(process=tx)
    await m.answer("💰 أرسل المبلغ الذي تريد سحبه")
    await state.set_state(SyriatelStateW.amount)

# ========================= المبلغ =========================
@router.message(SyriatelStateW.amount)
async def process_amount_syriatel(m: types.Message, state: FSMContext):
    data = await state.get_data()
    process = data.get("process")

    try:
        amount = int(m.text.strip())
    except ValueError:
        await m.answer("❌ أرسل مبلغ صحيح (أرقام فقط)")
        return

    uid = m.from_user.id

    # استخدام الدالة الذكية الموحدة (تفحص الرصيد، الطلبات المعلقة، تخصم وتحجز المبلغ بسطر واحد)
    success, status = await check_and_add_pending_withdraw(user_id=uid, amount=amount, tx_type="SyriatelCash")

    if not success:
        if status == "insufficient_balance":
            await m.answer("❌ رصيدك غير كافي لإتمام عملية السحب.")
        elif status == "has_pending":
            await m.answer("❌ لديك طلب (سحب أو شحن) قيد المراجعة سابقاً بالفعل.")
        else:
            await m.answer("❌ حدث خطأ ما أو أن حسابك غير مسجل، أرسل /start وعاود المحاولة.")
        
        await state.clear()
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ قبول", callback_data=f"acceptW_S_{uid}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"rejectW_S_{uid}")
            ]
        ]
    )

    await m.answer("⏳ تم حجز الرصيد بنجاح، انتظر قليلاً لمراجعة طلب السحب من قبل الإدارة.")
    
    try:
        await m.bot.send_message(
            GROUP_ID,
            f"📤 طلب سحب جديد\n\n"
            f"نوع السحب: SyriatelCash\n\n"
            f"👤 ID المستخدم: {uid}\n"
            f"🧾 رقم الهاتف: {process}\n"
            f"💰 المبلغ المطلوب: {amount} ل.س",
            reply_markup=kb
        )
    except Exception as e:
        print(f"فشل إرسال إشعار سحب سيرياتيل للجروب: {e}")
        
    await state.clear()

# ========================= قبول عملية سيرياتيل كاش =========================
@router.callback_query(lambda c: c.data.startswith("acceptW_S_"))
async def accept_syriatel_withdraw(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])

    # استدعاء دالة القبول الآمنة (تمسح السجل المعلق وتعيد قيمته، والرصيد مخصوم مسبقاً)
    amount = await accept_pending_withdraw_db(uid)
    
    if amount is None:
        await call.answer("❌ العملية غير موجودة أو تم معالجتها مسبقاً", show_alert=True)
        return

    # أرشفة المعاملة بنجاح
    await add_transaction(
        user_id=uid,
        tx_type="withdraw",
        amount=amount,
        status="completed",
        txid="SyriatelCash"
    )

    await call.message.edit_text(call.message.text + "\n\n✅ تم قبول العملية وتأكيد السحب!")
    
    try:
        await call.bot.send_message(
            uid,
            f"✅ تم تأكيد طلب سحبك بنجاح بمبلغ {amount} ل.س عبر سيرياتيل كاش.\n"
            f"📱 سيتم تحويل الرصيد إلى رقمك خلال مدة تتراوح من 5 دقائق إلى 6 ساعات."
        )
    except Exception as e:
        print(f"تعذر إرسال رسالة السحب للمستخدم {uid}: {e}")

# ========================= رفض عملية سيرياتيل كاش =========================
@router.callback_query(lambda c: c.data.startswith("rejectW_S_"))
async def reject_syriatel_withdraw(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])
    # استدعاء دالة الرفض (تحذف الطلب وتعيد الرصيد المحجوز للمستخدم تلقائياً)
    amount = await reject_pending_withdraw_db(uid)

    if amount is None:
        await call.answer("❌ العملية معالجة مسبقاً أو غير موجودة", show_alert=True)
        return

    await call.message.edit_text(call.message.text + "\n\n❌ تم رفض العملية وإعادة الرصيد للمستخدم.")
    
    try:
        await call.bot.send_message(
            uid, 
            f"❌ تم رفض طلب السحب الخاص بك عبر سيرياتيل كاش من قبل الإدارة.\n"
            f"💰 تم إعادة الرصيد المحجوز ({amount} ل.س) إلى حسابك في البوت بالكامل."
        )
    except Exception as e:
        print(f"تعذر مراسلة المستخدم عند الرفض: {e}")

#========================== شام كاش =========================
@router.message(lambda m: m.text == "W 💳 شام كاش")
async def shamcashlD(m: types.Message, state: FSMContext):
    await m.answer(
        "لإستلام أرباحك . . أرسل رابط الاستقبال الخاص بك\n"
        "عبر : الشام كاش >> زر الاستقبال 📲\n"
        "لإستلام مبالغ كبيرة و للمساعدة : @SHARK_SUPPORT_ICHANCY\n"
        "👑 يرجى عدم أرفاق صورة باركود 👑\n"
    )
    await state.set_state(ShamCashStateW.process)

# ========================= رابط الاستقبال =========================
@router.message(ShamCashStateW.process)
async def process_number_shamcash(m: types.Message, state: FSMContext):
    await state.update_data(process=m.text)
    await m.answer("💰 أرسل المبلغ الذي تريد سحبه")
    await state.set_state(ShamCashStateW.amount)

# ========================= المبلغ =========================
@router.message(ShamCashStateW.amount)
async def process_amount_shamcash(m: types.Message, state: FSMContext):
    data = await state.get_data()
    process = data.get("process")

    try:
        amount = int(m.text.strip())
    except ValueError:
        await m.answer("❌ أرسل مبلغ صحيح (أرقام فقط)")
        return

    uid = m.from_user.id

    # استدعاء الدالة الذكية الموحدة (تفحص الرصيد، الطلبات المعلقة، وتخصم وتدرج الطلب بسطر واحد)
    success, status = await check_and_add_pending_withdraw(user_id=uid, amount=amount, tx_type="ShamCash")

    if not success:
        if status == "insufficient_balance":
            await m.answer("❌ رصيدك غير كافي لإتمام هذه العملية.")
        elif status == "has_pending":
            await m.answer("❌ لديك طلب (سحب أو شحن) قيد المراجعة سابقاً بالفعل.")
        else:
            await m.answer("❌ حدث خطأ ما أو أن حسابك غير مسجل، أرسل /start وعاود المحاولة.")
        
        await state.clear()
        return

    # بناء أزرار الإدارة والجروب
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ قبول", callback_data=f"acceptW_SH_{uid}"),
                InlineKeyboardButton(text="❌ رفض", callback_data=f"rejectW_SH_{uid}")
            ]
        ]
    )

    await m.answer("⏳ تم حجز الرصيد بنجاح، انتظر قليلاً لمراجعة طلب السحب من قبل الإدارة.")
    
    try:
        await m.bot.send_message(
            GROUP_ID,
            f"📤 طلب سحب جديد\n\n"
            f"نوع السحب: ShamCash\n\n"
            f"👤 ID المستخدم: {uid}\n"
            f"🧾 رابط الاستقبال: {process}\n"
            f"💰 المبلغ المطلوب: {amount} ل.س",
            reply_markup=kb
        )
    except Exception as e:
        print(f"فشل إرسال إشعار السحب للجروب: {e}")
        
    await state.clear()


# ========================= قبول عملية شام كاش سحب =========================
@router.callback_query(lambda c: c.data.startswith("acceptW_SH_"))
async def accept_shamcash(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])

    # استدعاء دالة القبول من الداتابيز مباشرة (تمسح السجل المعلق وتعيد قيمته)
    amount = await accept_pending_withdraw_db(uid)
    
    if amount is None:
        await call.answer("❌ العملية غير موجودة أو تم معالجتها مسبقاً", show_alert=True)
        return

    # تسجيل المعاملة في جدول العمليات المؤرشفة
    await add_transaction(
        user_id=uid,
        tx_type="withdraw",
        amount=amount,
        status="completed",
        txid="ShamCash"
    )

    await call.message.edit_text(call.message.text + "\n\n✅ تم قبول العملية وتأكيد السحب!")
    
    try:
        await call.bot.send_message(
            uid,
            f"✅ تم تأكيد طلب سحبك بنجاح بمبلغ {amount} ل.س\n"
            f"💳 سيتم تحويل الرصيد إلى محفظتك خلال مدة تتراوح من 5 دقائق إلى 6 ساعات."
        )
    except Exception as e:
        print(f"تعذر إرسال رسالة السحب للمستخدم {uid}: {e}")


# ========================= رفض عملية شام كاش سحب =========================
@router.callback_query(lambda c: c.data.startswith("rejectW_SH_"))
async def rejectshamcash(call: types.CallbackQuery):
    uid = int(call.data.split("_")[2])

    # استدعاء دالة الرفض (تحذف الطلب وتعيد الرصيد المحجوز للمستفيد تلقائياً)
    amount = await reject_pending_withdraw_db(uid)

    if amount is None:
        await call.answer("❌ العملية معالجة مسبقاً أو غير موجودة", show_alert=True)
        return

    await call.message.edit_text(call.message.text + "\n\n❌ تم رفض العملية وإعادة الرصيد للمستخدم.")
    
    try:
        await call.bot.send_message(
            uid, 
            f"❌ تم رفض طلب السحب الخاص بك من قبل الإدارة.\n"
            f"💰 تم إعادة الرصيد المحجوز ({amount} ل.س) إلى حسابك في البوت بالكامل، يرجى مراجعة بياناتك."
        )
    except Exception as e:
        print(f"تعذر مراسلة المستخدم عند الرفض: {e}")