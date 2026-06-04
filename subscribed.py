from config import GROUP_ICHANCY_CHANNEL_ID
from logger import logger


async def is_subscribed(user_id, bot):

    try:
        member = await bot.get_chat_member(GROUP_ICHANCY_CHANNEL_ID, user_id)

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception as e:
        logger.exception(e)
        return False