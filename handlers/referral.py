from aiogram import Router, types

router= Router()


def get_ref_link(user_id: int):

    return f"https://t.me/YOUR_BOT_USERNAME?start={user_id}"


@router.message(lambda m: m.text == "🔗 رابط الإحالة")
async def referral_link(m: types.Message):

    link = get_ref_link(m.from_user.id)

    await m.answer(f"🔗 رابطك:\n{link}")