import os
import aiohttp
from dotenv import load_dotenv, set_key
from database.db import save_tokens_to_db, get_tokens_from_db
load_dotenv()

# متغيرات عالمية يتم تحديثها في الذاكرة أثناء تشغيل السكربت
MY_TOKEN = ""
MY_REFRESH_TOKEN = ""

async def initialize_tokens():
    """
    دالة تهيئة التوكنات عند تشغيل المشروع.
    تُستدعى هذه الدالة مرة واحدة فقط عند إقلاع السيرفر أو التطبيق (Startup)
    بديلًا عن السطور القديمة التي كانت تقرأ من .env
    """
    global MY_TOKEN, MY_REFRESH_TOKEN
    
    # القراءة من قاعدة البيانات باستخدام الدالة التي عدلناها سابقاً
    MY_TOKEN, MY_REFRESH_TOKEN = await get_tokens_from_db()
    print("🚀 [System] Tokens initialized successfully from MySQL database!")
    print(MY_TOKEN)
    print(MY_REFRESH_TOKEN)

async def update_env_tokens(new_access, new_refresh):
    """تحديث قيم التوكنات في الذاكرة وداخل قاعدة بيانات MySQL فوراً"""
    global MY_TOKEN, MY_REFRESH_TOKEN
    MY_TOKEN = new_access
    MY_REFRESH_TOKEN = new_refresh
    
    await save_tokens_to_db(new_access, new_refresh)
    print("💾 [System] Memory and Database updated with new tokens!")

async def refresh_access_token_async():
    """طلب توكن جديد من السيرفر باستخدام الـ Refresh Token"""
    global MY_REFRESH_TOKEN
    url = "https://agents.ichancy.com/global/api/UserApi/refreshToken"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {"refreshToken": str(MY_REFRESH_TOKEN)}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") is True:
                        res = data.get("result", {})
                        # تحديث التوكنات في الذاكرة وقاعدة البيانات
                        await update_env_tokens(res.get("accessToken"), res.get("refreshToken"))
                        return True
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
    return False

async def send_post_request(url, payload, retry=True):
    """دالة وسيطة ذكية ترسل الطلبات وتجدد التوكن تلقائياً إذا أعاد السيرفر كود 401"""
    global MY_TOKEN
    headers = {
        "Authorization": f"Bearer {MY_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://agents.ichancy.com",
        "Referer": "https://agents.ichancy.com/"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 401 and retry:
                    print("⚠️ Token expired (401). Trying to refresh...")
                    if await refresh_access_token_async():
                        # إعادة المحاولة بالتوكن الجديد
                        return await send_post_request(url, payload, retry=False)
                    else:
                        return {"success": False, "error": "session_expired"}
                
                if response.status == 200:
                    return {"success": True, "data": await response.json()}
                return {"success": False, "error": f"server_error_{response.status}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ----------------- دالات المنظومة الأساسية -----------------

async def register_new_player_async(player_username, player_password):
    """إنشاء حساب لاعب جديد على السيرفر"""
    url = "https://agents.ichancy.com/global/api/UserApi/registerPlayer"
    parent_id = os.getenv("PARENT_ID")
    payload = {
        "player": {
            "email": f"{player_username}@shark.com",
            "password": player_password,
            "parentId": int(parent_id),
            "login": f"{player_username}_777"
        }
    }
    res = await send_post_request(url, payload)
    if res["success"]:
        response_data = res["data"]
        if response_data.get("status") is True:
            return {"success": True, "result": response_data.get("result")}
        else:
            notifications = response_data.get("notification", [])
            return {"success": False, "error": notifications[0].get("content") if notifications else "خطأ غير معروف"}
    if "422" in res.get("error", ""):
        return {"success": False, "error": "(422) صيغة بيانات غير مدعومة"}
    return {"success": False, "error": res.get("error")}

async def find_player_id_by_username(target_username):
    """البحث عن لاعب وجلب الـ playerId الرقمي"""
    url = "https://agents.ichancy.com/global/api/UserApi/getPlayersForCurrentAgent"
    payload = {
        "start": 0, "limit": 20,
        "filter": {"userName": {"action": "=", "value": str(target_username), "valueLabel": str(target_username)}}
    }
    res = await send_post_request(url, payload)
    if res["success"] and res["data"].get("status") is True:
        records = res["data"].get("result", {}).get("records", [])
        if records:
            return {"found": True, "id": records[0].get("playerId")}
    return {"found": False, "error": "اللاعب غير موجود في السيرفر"}

async def get_player_balance_async(player_id):
    """جلب رصيد اللاعب الفعلي من السيرفر"""
    url = "https://agents.ichancy.com/global/api/UserApi/getPlayerBalanceById"
    payload = {"playerId": int(player_id)}
    res = await send_post_request(url, payload)
    if res["success"] and res["data"].get("status") is True:
        result_list = res["data"].get("result", [])
        balance = result_list[0].get("balance", 0) if result_list else 0
        return {"success": True, "balance": float(balance)}
    return {"success": False, "error": "تعذر جلب رصيد اللاعب"}

async def deposit_to_player_async(player_id, amount, comment=""):
    """شحن رصيد اللاعب على السيرفر"""
    url = "https://agents.ichancy.com/global/api/UserApi/depositToPlayer"
    payload = {
        "amount": float(amount), "comment": str(comment), "playerId": int(player_id),
        "currencyCode": "NSP", "currency": "NSP", "moneyStatus": 5
    }
    res = await send_post_request(url, payload)
    if res["success"] and res["data"].get("status") is True and res["data"].get("result") is not False:
        return {"success": True}
    return {"success": False, "error": "فشل الشحن من السيرفر المالي"}

async def withdraw_from_player_async(player_id, amount, comment=""):
    """سحب رصيد من اللاعب (بمبلغ سالب)"""
    url = "https://agents.ichancy.com/global/api/UserApi/withdrawFromPlayer"
    payload = {
        "amount": -abs(float(amount)), "comment": str(comment), "playerId": int(player_id),
        "currencyCode": "NSP", "currency": "NSP", "moneyStatus": 5
    }
    res = await send_post_request(url, payload)
    if res["success"] and res["data"].get("status") is True and res["data"].get("result") is not False:
        return {"success": True}
    return {"success": False, "error": "فشل السحب من السيرفر المالي (تأكد من رصيد اللاعب)"}
