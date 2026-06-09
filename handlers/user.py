from aiogram import types, BaseMiddleware, Router
from typing import Callable, Dict, Any, Awaitable
from keyboards.reply import menu, ichancymenu, ichancymenuregistered
from aiogram.fsm.state import State, StatesGroup
from subscribed import is_subscribed
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, TelegramObject
from logger import logger
from encryption import decrypt_password, encrypt_password
import asyncio

class GiftState(StatesGroup):
    waiting_code = State()

# استيراد دوال الأسنك وحوض الاتصالات الرئيسي
from database.db import (
    db_pool,
    add_user,
    get_balance,
    save_user_to_db,
    has_referral,
    add_referral,
    add_balance,
    get_user,
    get_bonus_from_db,
    get_user_referral_stats,
    redeem_gift_code_db,
    get_user_transactions_paginated
)
from config import TOKKEN, PARENT_ID
from aiogram.fsm.context import FSMContext

from buttons.games_ichancy import router as games_router
from buttons.deposit import router as deposit_router
from buttons.tutorials import router as tutorials_router
from buttons.withdraw import router as withdraw_router

from ichancy.ichancy_api import register_new_player_async, get_player_balance_async, withdraw_from_player_async, find_player_id_by_username, deposit_to_player_async

# إنشاء الراوتر بدلاً من الـ Dispatcher القديم
router = Router()

class RegisterState(StatesGroup):
    username = State()
    password = State()

class DepositState(StatesGroup):
    amountichancy = State()

class WithdrawState(StatesGroup):
    amount = State()

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        if not await is_subscribed(user_id, event.bot):
            await event.answer(
                f"❌ يجب الاشتراك بالقناة أولاً:\nhttps://t.me/Shark_Ichancy_Channel"
            )
            return
        return await handler(event, data)

# ربط الميدل وير بالراوتر الحالي
router.message.middleware(SubscriptionMiddleware())

# تضمين الراوترات الفرعية داخل راوتر المستخدم الرئيسي
router.include_router(games_router)
router.include_router(deposit_router)
router.include_router(tutorials_router)
router.include_router(withdraw_router)

@router.message(lambda m: m.text and m.text.startswith("/start"))
async def start(m: types.Message):
    await state.clear()
    user_id = m.from_user.id
    args = m.text.split(maxsplit=1)

    # إضافة await لأن الدوال أصبحت أسنك
    is_new_user = await add_user(user_id)
    balance = await get_balance(user_id)

    if len(args) > 1 and is_new_user:
        try:
            referrer_id = int(args[1])
            if referrer_id != user_id:
                success = await add_referral(user_id, referrer_id)
                if success:
                    await add_balance(referrer_id, 500)
                    try:
                        await m.bot.send_message(
                            referrer_id,
                            "🎉 تم إضافة إحالة جديدة!\n💰 تم إضافة 500 ل.س إلى رصيدك."
                        )
                    except Exception:
                        pass
        except ValueError:
            pass
        except Exception as e:
            print("Referral error:", e)

    await m.answer(
        f"🎰 أهلاً بك\n\n💰 رصيدك: {balance} ل.س",
        reply_markup=menu
    )

@router.message(lambda m: m.text == "💰 الرصيد")
async def balance(m: types.Message):
    bal = await get_balance(m.from_user.id)
    await m.answer(f"💰 رصيدك الحالي:\n\n{bal} ل.س")

@router.message(lambda m: m.text == "🎰 ichancy")
async def ichancy(m: types.Message):
    user = await get_user(m.from_user.id)
    if user:
        username, password, email = user
        ppass = decrypt_password(password)
        await m.answer(
            "🎰 مرحباً بك في ichancy\n\n"
            f"👤 username: {username}\n"
            f"🔑 password: {ppass}\n"
            f"id: {m.from_user.id}\n\n"
            "✅ أنت مسجل بالفعل",
            reply_markup=ichancymenuregistered
        )
        return
    await m.answer(
        "🎰 مرحباً بك في ichancy\n\n"
        f"id:  {m.from_user.id}",
        reply_markup=ichancymenu
    )

@router.message(lambda m: m.text == "انشاء حساب Ichancy")
async def register_ichancy(m: types.Message, state: FSMContext):
    await m.answer("username?")
    await state.set_state(RegisterState.username)

@router.message(RegisterState.username)
async def reg_username(m: types.Message, state: FSMContext):
    username = m.text.strip()
    await state.update_data(username=username)
    await m.answer("password?")
    await state.set_state(RegisterState.password)

@router.message(RegisterState.password)
async def reg_password(m: types.Message, state: FSMContext):
    usertelegram = m.from_user.id
    password = m.text.strip()
    data = await state.get_data()
    username = data["username"]
    passs = encrypt_password(password)

    response_result = await register_new_player_async(player_username=username, player_password=password)
    if response_result and response_result.get("success") is True:
        await m.answer(
            f"🎉 *تهانياً! تم إنشاء حسابك على Ichancy بنجاح.*\n\n"
            f"👤 *اسم المستخدم:* {username}\n"
            f"🔑 *كلمة المرور:* {password}\n"
            f"📧 *البريد الإلكتروني:* {username}@gmail.com\n\n"
            "يمكنك الآن استخدام هذه البيانات لتسجيل الدخول إلى ألعاب Ichancy.",
            reply_markup=menu
        )
        await save_user_to_db(user_id=usertelegram, email=f"{username}@shark.com", password=passs, username=f"{username}_777")
    else:
        error_reason = response_result.get("error", "حدث خطأ غير معروف في السيرفر")
        await m.answer(
            f"❌ *عذراً، فشل إنشاء الحساب.*\n\n"
            f"⚠️ *السبب:* {error_reason}\n\n"
            f"يرجى المحاولة مجدداً باستخدام اسم مستخدم آخر.",
            parse_mode="Markdown",
            reply_markup=menu
        )
    await state.clear()

@router.message(lambda m: m.text == "شحن رصيد بالحساب")
async def reg_depositichancy(m: types.Message, state: FSMContext):
    await m.answer("💰 ارسل المبلغ")
    await state.set_state(DepositState.amountichancy)

@router.message(DepositState.amountichancy)
async def reg_amount(m: types.Message, state: FSMContext):
    try:
        amount = int(m.text)
    except Exception as e:
        logger.exception(e)
        await m.answer("❌ ارسل رقم صحيح")
        await state.clear()
        return
    
    from_id = m.from_user.id
    user = await get_user(from_id)

    if not user:
        await m.answer("❌ لم يتم العثور على الحساب")
        await state.clear()
        return
    
    sender_balance = await get_balance(from_id)
    if sender_balance < amount:
        await m.answer("❌ رصيدك غير كافي")
        await state.clear()
        return
    
    if amount < 5000:
        await m.answer("اقل عملية شحن يجب ان تكون 5000")
        await state.clear()
        return
    
    username, password, email = user
    await m.answer("🔍 جاري التحقق من وجود الحساب على السيرفر وجلب المعرف...")

    user_info = await find_player_id_by_username(target_username=username)
    if not user_info or not user_info.get("found"):
        await m.answer(f"❌ فشل الشحن. اللاعب {username} غير موجود.")
        await state.clear()
        return

    target_player_id = user_info["id"]
    depositichancy = await deposit_to_player_async(
        player_id=target_player_id,  
        amount=amount,
        comment="شحن تلقائي عبر البوت"
    )

    if depositichancy and depositichancy.get("success") is True:
        # استخدام الـ Pool للحصول على اتصال معزول وآمن بدلاً من المغير العام cur
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET balance = balance - %s WHERE user_id = %s",
                    (amount, from_id)
                )
                await m.answer(
            f"✅ تم شحن {amount} بنجاح لحسابك.\n"
            f"👤 اللاعب: {username}\n"
            f"🆔 معرف اللاعب: {target_player_id}"
        )
        await state.clear()
        return
    else:
        error_reason = depositichancy.get("error", "حدث خطأ في منظومة الشحن")
        await m.answer(f"❌ فشل الشحن\n\n⚠️ السبب: {error_reason}")
        await state.clear()
        return

@router.message(lambda m: m.text == "سحب رصيد من الحساب")
async def start_withdraw(m: types.Message, state: FSMContext):
    await m.answer("💸 ارسل المبلغ")
    await state.set_state(WithdrawState.amount)

@router.message(WithdrawState.amount)
async def do_withdraw(m: types.Message, state: FSMContext):
    try:
        amount = int(m.text)
    except Exception as e:
        logger.exception(e)
        await m.answer("❌ ارسل رقم صحيح")
        await state.clear()
        return
    
    from_id = m.from_user.id
    user = await get_user(from_id)

    if not user:
        await m.answer("❌ لم يتم العثور على الحساب")
        await state.clear()
        return
        
    if amount < 5000:
        await m.answer("أقل قيمة سحب يجب أن تكون 5000")
        await state.clear()
        return

    username, password, email = user
    await m.answer("🔍 جاري فحص الحساب والتحقق من الرصيد على المنصة...")

    user_info = await find_player_id_by_username(target_username=username)
    if not user_info or not user_info.get("found"):
        await m.answer(f"❌ فشل السحب. حساب اللاعب {username} غير موجود في المنظومة.")
        await state.clear()
        return

    target_player_id = user_info["id"]
    balance_check = await get_player_balance_async(player_id=target_player_id)
    
    if not balance_check or not balance_check.get("success"):
        error_msg = balance_check.get("error", "تعذر قراءة بيانات المحفظة الحالية")
        await m.answer(f"❌ تم إلغاء العملية.\n⚠️ السبب: {error_msg}")
        await state.clear()
        return
        
    server_player_balance = balance_check["balance"]
    if server_player_balance < amount:
        await m.answer(
            f"❌ طلب سحب غير صالح.\n\n"
            f"⚠️ *رصيدك الحالي في اللعبة هو:* {server_player_balance} NSP\n"
            f"💰 *المبلغ المطلوب سحبه:* {amount} NSP\n\n"
            f"رصيدك غير كافٍ لإتمام هذه العملية."
        )
        await state.clear()
        return

    withdraw_result = await withdraw_from_player_async(
        player_id=target_player_id,
        amount=amount,
        comment="سحب تلقائي آمن عبر البوت"
    )

    if withdraw_result and withdraw_result.get("success") is True:
        async with db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE users SET balance = balance + %s WHERE user_id = %s",
                    (amount, from_id)
                )
        await m.answer(
            f"✅ تم تأكيد السحب بنجاح!\n\n"
            f"👤 اللاعب: {username}\n"
            f"💰 المبلغ المسحوب: {amount} NSP\n"
            f"📥 تم إضافة الرصيد إلى محفظتك في البوت بنجاح."
        )
    else:
        error_reason = withdraw_result.get("error", "حدث خطأ أثناء معالجة السحب")
        await m.answer(f"❌ فشلت عملية السحب من المنصة\n\n⚠️ السبب: {error_reason}")
        
    await state.clear()

@router.message(lambda m: m.text == "👥 نظام الاحالات")
async def refs(m: types.Message):
    
    row = await get_user_referral_stats(m.from_user.id)

    if not row:
        return await m.answer("لا يوجد بيانات")

    referrals, balance, pending_commission = row

    await m.answer(
            f"نظام احالات <b>Ichancy Shark</b>\n"
            f"يقدّم لك فرصة لدخل إضافي كل 10 أيام.\n"
            f"إحصل على نسبة ثابتة 1% لكل عمليات الشحن القادمة عن طريق رابط احالتك!\n\n"
            f"📊 إحصائياتك الحالية:\n"
            f"👥 عدد إحالاتك: {referrals}\n"
            f"💰 أرباحك المعلقة (ستوزع بعد انتهاء الـ 10 أيام): {pending_commission} ل.س\n\n"
            f"🔗 رابط الإحالة الخاص بك:\n"
            f"https://t.me/sharkichancy_bot?start={m.from_user.id}",
            parse_mode="HTML"
        )

@router.message(lambda m: m.text == "🎁 كود هدية")
async def gift(m: types.Message, state: FSMContext):
    await m.answer("🎁 ارسل كود الهدية", reply_markup=ReplyKeyboardRemove())
    await state.set_state(GiftState.waiting_code)
    
@router.message(GiftState.waiting_code)
async def redeem_code(m: types.Message, state: FSMContext):
    code = m.text.strip().upper()
    uid = m.from_user.id

    success, status_or_amount = await redeem_gift_code_db(user_id=uid, code=code)

    if not success:
        if status_or_amount == "not_found":
            await m.answer("❌ الكود غير صحيح")
        elif status_or_amount == "already_used":
            await m.answer("❌ هذا الكود مستخدم مسبقاً")
        else:
            await m.answer("⚠️ حدث خطأ أثناء تفعيل الكود، يرجى المحاولة مرة أخرى.")
        
        await state.clear()
        return
    amount = status_or_amount
    await m.answer(f"🎁 تم تفعيل الكود!\n💰 +{amount} ل.س")
    await state.clear()

@router.message(lambda m: m.text == "💝 اهداء رصيد")
async def transfer1(m: types.Message):
    await m.answer("💝 ارسل ايدي الشخص والمبلغ\n\nمثال: transfer 123456789 100")
    
@router.message(lambda m: m.text and m.text.startswith("transfer "))
async def transfer(m: types.Message):
    try:
        data = m.text.split()
        to_id = int(data[1])
        amount = int(data[2])
    except Exception as e:
        logger.exception(e)
        return

    from_id = m.from_user.id
    sender_balance = await get_balance(from_id)

    if sender_balance < amount:
        await m.answer("❌ رصيدك غير كافي")
        return

    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE users SET balance = balance - %s WHERE user_id=%s", (amount, from_id))
            await add_balance(to_id, amount)

    await m.answer(f"💝 تم إرسال {amount} بنجاح")
    await m.bot.send_message(to_id, f"💝 استلمت {amount} من مستخدم")

@router.message(lambda m: m.text == "☎️ تواصل معنا")
async def support(m: types.Message):
    await m.answer("اكتب الرسالة وسيتم ارسالها للادمن")

@router.message(lambda m: m.text == "📨 رسالة للادمن")
async def admin_msg(m: types.Message):
    await m.answer("@SHARK_ICHANCY_SUPPORT7")

PAGE_SIZE = 5

@router.message(lambda m: m.text == "📜 السجل")
async def my_transactions(m: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 الإيداعات", callback_data="list_deposit_0"),
            InlineKeyboardButton(text="📤 السحوبات", callback_data="list_withdraw_0")
        ]
    ])
    await m.answer("📊 اختر نوع السجل:", reply_markup=kb)

async def show_list(call: types.CallbackQuery, filter_type: str, page: int):
    uid = call.from_user.id
    offset = page * PAGE_SIZE

    if filter_type == "deposit":
        query_type = "%deposit%"
        title = "📥 الإيداعات"
    else:
        query_type = "%withdraw%"
        title = "📤 السحوبات"
    
    rows, total = await get_user_transactions_paginated(
        user_id=uid,
        query_type=query_type,
        limit=PAGE_SIZE,
        offset=offset
    )
    if not rows:
        await call.message.answer("📭 لا يوجد بيانات")
        return
    text = f"{title} - صفحة {page+1}\n\n"
    for type_, amount, status, txid, date in rows:
        text += (
            f" {type_}\n"
            f"💰 {amount}\n"
            f"📌 {status}\n"
            f"🧾 {txid}\n"
            f"🕒 {date}\n"
            f"──────────\n"
        )
    
    has_next = offset + PAGE_SIZE < total
    has_prev = page > 0

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️", callback_data=f"{filter_type}_{page-1}" if has_prev else "ignore"),
            InlineKeyboardButton(text=f"{page+1}", callback_data="ignore"),
            InlineKeyboardButton(text="▶️", callback_data=f"{filter_type}_{page+1}" if has_next else "ignore"),
        ]
    ])
    await call.message.answer(text, reply_markup=kb)

@router.callback_query(lambda c: c.data.startswith("list_deposit"))
async def deposits(call: types.CallbackQuery):
    _, _, page = call.data.split("_")
    await show_list(call, "deposit", int(page))

@router.callback_query(lambda c: c.data.startswith("list_withdraw"))
async def withdraws(call: types.CallbackQuery):
    _, _, page = call.data.split("_")
    await show_list(call, "withdraw", int(page))

@router.callback_query(lambda c: c.data.startswith("deposit_") or c.data.startswith("withdraw_"))
async def paginate(call: types.CallbackQuery):
    filter_type, page = call.data.split("_")
    await show_list(call, filter_type, int(page))

@router.callback_query(lambda c: c.data == "ignore")
async def ignore(call: types.CallbackQuery):
    await call.answer()

wheel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🎡 عجلة حظ",
                web_app=WebAppInfo(url="https://mdenmdenmden385-rgb.github.io/wwww/")
            )
        ],
        [KeyboardButton(text="القائمة الرئيسية")]
    ],
    resize_keyboard=True
)

@router.message(lambda m: m.text == "🎡 عجلة حظ")
async def wheel(m: types.Message):
    await m.answer("🎡 افتح العجلة من الزر", reply_markup=wheel_keyboard)

@router.message(lambda m: m.text == "🏆 الجاكبوت")
async def jackpot(m: types.Message):
    await m.answer("🏆 الجاكبوت قريباً")

@router.message(lambda m: m.text == "🎉 البونصات والعروض الحالية")
async def bonus(m: types.Message):
    current_text = await get_bonus_from_db()
    await m.answer(current_text)

@router.message(lambda m: m.text == "🎮 دخول مباشر للالعاب")
async def games(m: types.Message):
    gamesichancy = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Golden Tree: Buy Bonus", url="https://www.ichancy.com/ar/casino/slots/all/36/pascal-gaming/77612-500008078-golden-tree:-buy-bonus?mode=real")],
            [
                InlineKeyboardButton(text="🌳 Golden Tree", url="https://www.ichancy.com/ar/casino/slots/all/36/pascal-gaming/82711-500010058-golden-tree:-100-buy-bonus?mode=real"),
                InlineKeyboardButton(text="✨ Chancy: Buy Bonus", url="https://www.ichancy.com/ar/casino/slots/all/36/pascal-gaming/56245-420031709-golden-tree?mode=real")
            ],
            [
                InlineKeyboardButton(text="💎 Golden Tree: 100 Buy Bonus", url="https://www.ichancy.com/ar/casino/slots/all/247/pascal-gaming/99381-555573886-chancy-buy-bonus?mode=real"),
                InlineKeyboardButton(text="🍯 Honey Money", url="https://www.ichancy.com/ar/casino/slots/all/51/pascal-gaming/57564-420032128-honey-money?mode=real")
            ]
        ]
    )
    await m.answer(
        text="🎮 Games Ichancy\n\nإختر اللعبة التي تريدها من الأزرار أدناه:",
        reply_markup=gamesichancy,
        parse_mode="Markdown"
    )

@router.message(lambda m: m.text == "Ichancy Apk")
async def apk_download(m: types.Message):
    ichancyA = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ichancy Apk", url="https://android.betcoapps.com/novichok/ichancy_com/ichancy_com.apk")]
        ]
    )
    await m.answer(
        text="لتنزيل التطبيق يرجى الضغط على الزر👇🏻",
        reply_markup=ichancyA,
        parse_mode="Markdown"
    )
