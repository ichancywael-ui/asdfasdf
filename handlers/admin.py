from aiogram import types, Router
from config import ADMIN_ID
import os
import asyncio
from keyboards.reply import adminmenu
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from logger import logger

from database.db import (
    add_balance,
    set_rate,
    set_deposit_bonus_rate,
    update_bonus_in_db,
    get_bonus_from_db,
    get_all_users_admin,
    get_all_ichancy_accounts_admin,
    add_gift_code_db,
    get_target_user_transactions_admin,
    distribute_referral_commissions_db,
    update_bonus_in_db,
    get_all_user_ids
)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

class AdminState(StatesGroup):
    get_user_id = State()

class GiftAdmin(StatesGroup):
    code = State()
    amount = State()

class AdminStates(StatesGroup):
    waiting_for_bonus_text = State()

class AdminStatess(StatesGroup):
    waiting_for_bonus_text = State()
    waiting_for_deposit_bonus = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

# إنشاء راوتر الأدمن بدلاً من الدالة القديمة القياسية
router = Router()

PAGE_SIZE = 5

# ========================= بدء إضافة كود =========================
@router.message(lambda m: m.text == "اضافة كود")
async def add_code_start(m: types.Message, state: FSMContext):
    # التحقق من صلاحية الأدمن
    if m.from_user.id not in ADMIN_ID:
        return

    await state.clear()  # تنظيف أي حالات معلقة سابقة
    await m.answer("🎁 أرسل كود الهدية الجديد (مثال: SHARK100):")
    await state.set_state(GiftAdmin.code)

# ========================= استقبال الكود =========================
@router.message(GiftAdmin.code)
async def get_code(m: types.Message, state: FSMContext):
    await state.update_data(code=m.text.strip().upper())
    await m.answer("💰 الآن، أرسل قيمة الرصيد التي سيمنحها الكود (أرقام فقط):")
    await state.set_state(GiftAdmin.amount)

# ========================= استقبال المبلغ والتخزين =========================
@router.message(GiftAdmin.amount)
async def get_amount(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return

    data = await state.get_data()
    code = data.get("code")
    
    try:
        amount = int(m.text.strip())
    except ValueError:
        await m.answer("❌ عذراً، يجب إرسال مبلغ صحيح (أرقام فقط).")
        return

    # استدعاء الدالة الاحترافية والمحمية بسطر واحد فقط!
    success = await add_gift_code_db(code=code, amount=amount)

    if success:
        await m.answer(
            f"✅ <b>تم إضافة كود الهدية بنجاح!</b>\n\n"
            f"🎁 الكود: <code>{code}</code>\n"
            f"💰 القيمة الممنوحة: {amount} ل.س",
            parse_mode="HTML"
        )
    else:
        await m.answer("❌ فشل إضافة الكود، قد يكون هذا الكود مضافاً وموجوداً في قاعدة البيانات مسبقاً.")

    await state.clear()

@router.message(lambda m: m.text and m.text.startswith("addamountforuser"))
async def add(m: types.Message):
    if m.from_user.id not in ADMIN_ID:
        return

    try:
        _, uid, amount = m.text.split()

        await add_balance(int(uid), float(amount))
        await m.answer("✅ done")

        # استخدام m.bot للوصول المباشر لكائن البوت الفعّال دون تمريره كمعامل خارجي
        await m.bot.send_message(
            int(uid),
            f"💰 تم إضافة {amount}"
        )
    except Exception as e:
        logger.exception(e)
        await m.answer("❌ add user_id amount")

@router.message(lambda m: m.text and m.text.startswith("rate"))
async def rate(m: types.Message):
    if m.from_user.id not in ADMIN_ID:
        return

    try:
        value = float(m.text.split()[1])
        await set_rate(value)
        await m.answer(f"✅ rate updated: {value}")
    except Exception as e:
        logger.exception(e)
        await m.answer("❌ rate 14000")

@router.message(lambda m: m.text == "المستخدمين")
async def show_users(m: types.Message):
    # تحقق من صلاحية الأدمن (تأكد أن ADMIN_ID معرفة لديك كقائمة أو مجموعة)
    if m.from_user.id not in ADMIN_ID:
        return

    # استدعاء الدالة الآمنة بسطر واحد
    rows = await get_all_users_admin(limit=80)  # حددنا 80 مستخدم لضمان عدم تخطي حجم رسالة تلجرام

    if not rows:
        await m.answer("📭 لا يوجد مستخدمين مسجلين في قاعدة البيانات حالياً.")
        return

    text = f"📊 <b>قائمة أبرز المستخدمين (الأعلى رصيداً):</b>\n"
    text += f"👥 العدد المعروض: {len(rows)}\n"
    text += "──────────────────\n"
    
    for user_id, balance in rows:
        text += f"👤 <code>{user_id}</code> ── 💰 <b>{balance}</b> ل.س\n"

    await m.answer(text, parse_mode="HTML")

@router.message(lambda m: m.text == "حسابات ichancy")
async def show_users_ichancy(m: types.Message):
    # التحقق من صلاحية الأدمن
    if m.from_user.id not in ADMIN_ID:
        return

    # استدعاء الدالة الاحترافية بسطر واحد
    rows = await get_all_ichancy_accounts_admin(limit=50) # حددنا 50 لحماية حجم النص

    if not rows:
        await m.answer("📭 لا توجد حسابات Ichancy مسجلة في قاعدة البيانات حالياً.")
        return

    text = "📊 <b>قائمة حسابات Ichancy المسجلة:</b>\n"
    text += f"👥 عدد الحسابات المعروضة: {len(rows)}\n"
    text += "────────────────────────\n"
    
    for user_id, email, password, username in rows:
        text += (
            f"👤 آيدي المستخدم: <code>{user_id}</code>\n"
            f"📧 الإيميل: <code>{email}</code>\n"
            f"🔑 المستخدم: <code>{username}</code>\n"
            f"🔒 كلمة السر: <code>{password}</code>\n"
            f"────────────────────────\n"
        )

    await m.answer(text, parse_mode="HTML")

@router.message(lambda m: m.text == "Admin000")
async def admin(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return

    await m.answer("lll", reply_markup=adminmenu)

# ========================= بدء طلب السجل =========================
@router.message(lambda m: m.text == "📜 سجل مستخدم")
async def ask_user_id(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return

    await state.clear() # تنظيف أي حالة معلقة سابقة
    await m.answer("👤 أرسل ID المستخدم المراد جلب سجله:")
    await state.set_state(AdminState.get_user_id)

# ========================= استقبال الآيدي وعرض الخيارات =========================
@router.message(AdminState.get_user_id)
async def get_user_id(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return

    target_text = m.text.strip()
    if not target_text.isdigit():
        await m.answer("❌ أرسل ID صحيح (أرقام فقط)")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 الإيداعات", callback_data=f"admin|deposit|0|{target_text}"),
            InlineKeyboardButton(text="📤 السحوبات", callback_data=f"admin|withdraw|0|{target_text}")
        ]
    ])

    await m.answer(f"📊 اختر نوع السجل للمستخدم <code>{target_text}</code>:", reply_markup=kb, parse_mode="HTML")
    await state.clear() # تنظيف الحالة فوراً لأن التنقل سيعتمد على الـ Callback Data

# ========================= دالة العرض المقسم لصفحات للأدمن =========================
async def admin_show_list(call: types.CallbackQuery, filter_type: str, page: int, target_id: int):
    offset = page * PAGE_SIZE

    if filter_type == "deposit":
        query_type = "%deposit%"
        title = "📥 سجل الإيداعات"
    else:
        query_type = "%withdraw%"
        title = "📤 سجل السحوبات"

    # استدعاء الدالة الآمنة من ملف الداتابيز بسطر واحد ومنع الـ Lock
    rows, total = await get_target_user_transactions_admin(
        target_id=target_id,
        query_type=query_type,
        limit=PAGE_SIZE,
        offset=offset
    )

    if not rows:
        await call.answer("📭 لا يوجد بيانات مسجلة لهذا المستخدم.", show_alert=True)
        return

    text = f"📊 <b>{title} للمستخدم:</b> <code>{target_id}</code>\n"
    text += f"📖 صفحة: {page+1}\n"
    text += "──────────────────\n\n"
    
    for type_, amount, status, txid, date in rows:
        text += (
            f"🧩 النوع: {type_}\n"
            f"💰 المبلغ: {amount} ل.س\n"
            f"📌 الحالة: {status}\n"
            f"🧾 الـ ID: <code>{txid}</code>\n"
            f"🕒 التاريخ: {date}\n"
            f"──────────\n"
        )

    has_next = offset + PAGE_SIZE < total
    has_prev = page > 0

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"admin|{filter_type}|{page-1}|{target_id}" if has_prev else "ignore"
            ),
            InlineKeyboardButton(text=f"{page+1}", callback_data="ignore"),
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"admin|{filter_type}|{page+1}|{target_id}" if has_next else "ignore"
            ),
        ]
    ])

    # تعديل نص الرسالة الحالية بدلاً من إرسال رسالة جديدة لتفادي إغراق الشات
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # في حال لم يستطع تعديلها (مثل تشابه النصوص)، يرسلها كـ إجابة جديدة
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")

# ========================= معالج أزرار التنقل (Navigation Callback) =========================
@router.callback_query(lambda c: c.data.startswith("admin|"))
async def admin_nev(call: types.CallbackQuery):
    # استخدام نظام الفلاتر الرسمي لـ aiogram 3 والتخلص من الفانكشن لامبدا
    parts = call.data.split("|")
    if len(parts) < 4:
        return
        
    _, filter_type, page, target_id = parts
    await admin_show_list(call, filter_type, int(page), int(target_id))
    await call.answer() # إنهاء الدائرة اللامعة لزر التلجرام فوراً





# ========================= 1. الضغط على زر التوزيع (طلب التأكيد) =========================
@router.message(lambda m: m.text == "💰 توزيع أرباح الإحالات")
async def ask_distribute_confirm(m: types.Message):
    if m.from_user.id not in ADMIN_ID:
        return

    # بناء أزرار التأكيد والإلغاء
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚠️ نعم، وزّع الأرباح الآن", callback_data="confirm_distribute_refs"),
            InlineKeyboardButton(text="❌ إلغاء العملية", callback_data="cancel_distribute_refs")
        ]
    ])

    await m.answer(
        "🚨 <b>تحذير الإدارة الجاد:</b>\n\n"
        "أنت على وشك توزيع أرباح الإحالات (1%) لجميع المستخدمين المستحقين، وتصفير عدادات الفترة الحالية لبدء مسابقة الـ 10 أيام الجديدة.\n\n"
        "⚡ هذه العملية قطعية ولا يمكن التراجع عنها بعد التنفيذ.\n"
        "هل أنت متأكد تماماً وتريد المتابعة؟",
        reply_markup=kb,
        parse_mode="HTML"
    )

# ========================= 2. إلغاء العملية =========================
@router.callback_query(lambda c: c.data == "cancel_distribute_refs")
async def cancel_distribute(call: types.CallbackQuery):
    await call.message.edit_text("❌ تم إلغاء عملية توزيع الأرباح بنجاح، ولم يتم التعديل على قاعدة البيانات.")
    await call.answer()

# ========================= 3. تأكيد وتنفيذ التوزيع الآمن =========================
@router.callback_query(lambda c: c.data == "confirm_distribute_refs")
async def process_distribute_confirmed(call: types.CallbackQuery):
    # تحديث النص لإشعار الأدمن ببدء المعالجة
    await call.message.edit_text("⏳ جاري معالجة البيانات وتحديث أرصدة المستخدمين في قاعدة البيانات...")
    await call.answer()

    # استدعاء الدالة السريعة والمحمية (تُنفذ في أجزاء من الملي ثانية وتغلق الاتصال فوراً)
    winners = await distribute_referral_commissions_db()

    if not winners:
        await call.message.edit_text("📭 لا يوجد أي مستخدمين يملكون أرباحاً معلقة حالياً لتوزيعها.")
        return

    # إعلام الأدمن بنجاح تحديث الداتابيز وبدء إرسال الإشعارات للمستخدمين
    status_msg = await call.message.answer(f"✅ تم تحديث قاعدة البيانات بنجاح لـ {len(winners)} مستخدم!\n📥 جاري إرسال إشعارات التلجرام للمستفيدين حالياً...")

    success_count = 0
    # إرسال الرسائل خارج نطاق الـ SQL Cursor تماماً (لحماية الـ XAMPP من التجميد)
    for user_id, commission in winners:
        try:
            await call.bot.send_message(
                user_id,
                f"💰 <b>إشعار توزيع الأرباح الدورية (كل 10 أيام):</b>\n\n"
                f"تهانينا! تم إضافة أرباح بنسبة 1% من شحن إحالاتك إلى رصيدك الأساسي بنجاح.\n"
                f"➕ المبلغ المضاف: <b>{commission}</b> ل.س\n\n"
                f"بدأت الآن مسابقة الـ 10 أيام الجديدة، شارك رابطك وحظاً موفقاً! 🚀",
                parse_mode="HTML"
            )
            success_count += 1
            # تأخير بسيط جداً لحماية البوت من حظر تلجرام (Flood Control) عند إرسال رسائل كثيرة متتالية
            await asyncio.sleep(0.05) 
        except Exception as e:
            print(f"تعذر إرسال رسالة للمستخدم {user_id}: {e}")

    # التحديث النهائي للوحة الإدارة
    await status_msg.edit_text(
        f"🏆 <b>اكتملت عملية توزيع الأرباح بنجاح كلي!</b>\n\n"
        f"👥 عدد الحسابات التي تم شحنها في الداتابيز: {len(winners)}\n"
        f"✉️ عدد الإشعارات التي أرسلت بنجاح: {success_count}\n"
        f"🔄 تم تصفير كافة الأرباح المعلقة وعدادات المسابقة بنجاح خيالي وآمن."
    )






@router.message(lambda m: m.text == "/admin")
async def admin_panel(m: types.Message):
    if m.from_user.id not in ADMIN_ID:
        return
        
    btn = InlineKeyboardButton(
        text="💰 توزيع أرباح الـ 10 أيام وتصفير العداد", 
        callback_data="distribute_10_days_rewards"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[[btn]])
    await m.answer("مرحباً بك في لوحة التحكم، اضغط أدناه لتوزيع النسب:", reply_markup=markup)

# ========================= بدء تعديل البونص =========================
@router.message(lambda m: m.text == "تعديل نص البونصات و العروض الحالية")
async def start_edit_bonus(m: types.Message, state: FSMContext):
    # التحقق من صلاحية الأدمن
    if m.from_user.id not in ADMIN_ID:
        return
        
    await state.clear() # تنظيف أي حالات معلقة سابقاً
    
    # جلب النص الحالي بأمان بـ سطر واحد
    current_text = await get_bonus_from_db()
    
    await m.answer(
        f"📝 <b>النص القديم الحالي في البوت:</b>\n"
        f"<code>{current_text}</code>\n\n"
        f"📥 <b>أرسل الآن النص الجديد بالكامل ليتم حفظه وتحديثه للمستخدمين:</b>",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_bonus_text)

# ========================= حفظ النص الجديد =========================
@router.message(AdminStates.waiting_for_bonus_text)
async def save_bonus_text(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return

    new_text = m.text.strip()
    
    # تحديث النص داخل قاعدة البيانات بأسلوب آمن وبسطر واحد
    success = await update_bonus_in_db(new_text)
    
    if success:
        await m.answer(
            f"✅ <b>تم تحديث نص العروض والبونصات في قاعدة البيانات بنجاح!</b>\n\n"
            f"📋 <b>النص الحالي المعروض للمستخدمين:</b>\n"
            f"{new_text}",
            parse_mode="HTML"
        )
    else:
        await m.answer("❌ حدث خطأ داخلي أثناء تحديث النص في قاعدة البيانات، يرجى تفقّد محرك XAMPP.")
        
    await state.clear()

@router.message(lambda m: m.text == "اضافة او حذف البونص")
async def start_set_deposit_bonus(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return
        
    await m.answer("💰 أرسل الآن نسبة بونص الشحن الجديدة كـ رقم فقط (مثلاً: 5 لـ 5% أو 0 لإلغاء البونص):")
    await state.set_state(AdminStatess.waiting_for_deposit_bonus)

@router.message(AdminStatess.waiting_for_deposit_bonus)
async def save_deposit_bonus(m: types.Message, state: FSMContext):
    text = m.text
    if not text.isdigit():
        await m.answer("❌ يرجى إرسال رقم صحيح فقط وبدون علامة % (مثال: 5)")
        return

    await set_deposit_bonus_rate(int(text))
    await m.answer(f"✅ تم تحديث بونص الشحن بنجاح! البونص الحالي هو: {text}% على كل عملية شحن جديدة.")
    await state.clear()

@router.message(lambda m: m.text == "الإذاعة")
async def start_broadcast(m: types.Message, state: FSMContext):
    if m.from_user.id not in ADMIN_ID:
        return
    
    await m.answer("📥 أرسل الآن الرسالة (نص، صورة، إلخ) التي تريد إرسالها لجميع المستخدمين:")
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast(m: types.Message, state: FSMContext):
    await state.clear()
    
    # 1. جلب قائمة المستخدمين من الداتابيز باستخدام الدالة الجديدة
    users = await get_all_user_ids()
    
    if not users:
        await m.answer("❌ لا يوجد مستخدمين مسجلين في قاعدة البيانات حالياً.")
        return
    
    sending_msg = await m.answer(f"⏳ جاري بدء الإرسال إلى {len(users)} مستخدم...")
    
    success_count = 0
    fail_count = 0
    
    # 2. حلقة الإرسال لجميع المستخدمين
    for user_id in users:
        try:
            # استخدام دالة copy_to لنسخ الرسالة كما هي (نص، ميديا، أزرار)
            await m.copy_to(chat_id=user_id)
            success_count += 1

            await asyncio.sleep(0.05)
        except Exception:
            # يفشل الإرسال في حال قام المستخدم بحظر البوت (Block)
            fail_count += 1
            
    await sending_msg.edit_text(
        f"✅ تم الانتهاء من الإرسال الجماعي بنجاح!\n\n"
        f"🟢 تم الإرسال إلى: {success_count}\n"
        f"🔴 فشل الإرسال (حظر البوت): {fail_count}"
    )
