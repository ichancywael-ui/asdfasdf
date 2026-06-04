import os
import aiomysql

# إعداد المتغيرات البيئية (تأكد من مطابقتها لأسماء متغيرات Railway)
DB_HOST = os.getenv("MYSQLHOST", "localhost")
DB_USER = os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("MYSQLPASSWORD", "")
DB_NAME = os.getenv("MYSQLDATABASE", "botb")
DB_PORT = int(os.getenv("MYSQLPORT", 3306))

# حوض الاتصالات الرئيسي (سيتم ملؤه عند تشغيل البوت)
db_pool = None

async def init_pool():
    """إنشاء حوض الاتصالات لقاعدة البيانات"""
    global db_pool
    db_pool = await aiomysql.create_pool(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        port=DB_PORT,
        autocommit=True  # للحفظ التلقائي عند الإدخال والتعديل
    )

async def init():
    """إنشاء الجداول إذا لم تكن موجودة"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                balance DOUBLE DEFAULT 0,
                referrals_count INT DEFAULT 0,
                pending_commission DECIMAL(10, 2) DEFAULT 0.00
            )
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS usersichancy (
                user_id BIGINT PRIMARY KEY,
                email TEXT,
                password TEXT,
                username TEXT
            )
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                s_key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL
            )
            """)

            await cur.execute("""
            INSERT IGNORE INTO settings (s_key, value)
            VALUES ('deposit_bonus', '0'), ('rate', '1.0')
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS gift_codes (
                code VARCHAR(255) PRIMARY KEY,
                amount INT,
                used INT DEFAULT 0
            )
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS used_transactions(
                tx VARCHAR(255) PRIMARY KEY
            )
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                user_id BIGINT PRIMARY KEY,
                referrer_id BIGINT,
                current_period_earnings DECIMAL(10, 2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS pending (
                user_id BIGINT,
                amount DOUBLE,
                type VARCHAR(255)
            )
            """)

            await cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT,
                type VARCHAR(255),
                amount DOUBLE,
                status VARCHAR(50),
                txid VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # تم إضافة علامات الاقتباس المائلة key هنا لحل مشكلة الكلمة المحجوزة تماماً
            await cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                `key` VARCHAR(50) PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            # إدخال قيمة نص العروض الافتراضية لمنع ظهور خطأ NoneType لاحقاً
            await cur.execute("""
            INSERT IGNORE INTO bot_settings (`key`, value)
            VALUES ('bonus_text', '🎉 لا توجد عروض حالياً')
            """)

async def add_user(user_id: int) -> bool:
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            if await cur.fetchone():
                return False
            await cur.execute(
                "INSERT IGNORE INTO users (user_id, balance, referrals_count, pending_commission) VALUES (%s, 0, 0, 0.00)",
                (user_id,)
            )
            return True

async def get_balance(uid):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT balance FROM users WHERE user_id=%s", (uid,))
            r = await cur.fetchone()
            return r[0] if r else 0
        
async def add_balance(uid, amount):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE users SET balance = balance + %s WHERE user_id=%s",
                (amount, uid)
            )

async def get_rate():
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT value FROM settings WHERE s_key='rate'")
            r = await cur.fetchone()
            return float(r[0]) if r else 0.0

async def set_rate(v):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE settings SET value=%s WHERE s_key='rate'", (v,))

async def is_tx_used(tx):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tx FROM used_transactions WHERE tx=%s", (tx,))
            r = await cur.fetchone()
            return r is not None

async def save_tx(tx):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO used_transactions (tx) VALUES (%s)", (tx,))

async def has_referral(user_id: int):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM referrals WHERE user_id=%s", (user_id,))
            r = await cur.fetchone()
            return r is not None

async def add_referral(user_id: int, referrer_id: int) -> bool:
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM referrals WHERE user_id = %s", (user_id,))
            if await cur.fetchone():
                return False 

            try:
                await cur.execute(
                    "INSERT INTO referrals (user_id, referrer_id) VALUES (%s, %s)",
                    (user_id, referrer_id)
                )
                await cur.execute(
                    "UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = %s",
                    (referrer_id,)
                )
                return True
            except Exception as e:
                print(f"Database error: {e}")
                return False

async def save_user_to_db(user_id, username, password, email):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("""
                INSERT INTO usersichancy (user_id, username, password, email) VALUES (%s, %s, %s, %s)
                """, (user_id, username, password, email))
                return True
            except Exception as e:
                print("DB ERROR:", e)
                return False
    
async def user_exists(user_id):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM usersichancy WHERE user_id=%s", (user_id,))
            r = await cur.fetchone()
            return r is not None

async def get_user(user_id):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT username, password, email
                FROM usersichancy
                WHERE user_id=%s
            """, (user_id,))
            return await cur.fetchone()
        
async def add_transaction(user_id, tx_type, amount, txid=None, status="completed"):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
            INSERT INTO transactions
            (user_id, type, amount, status, txid)
            VALUES (%s, %s, %s, %s, %s)
            """, (user_id, tx_type, amount, status, txid))

async def process_deposit_commission(user_id: int, deposit_amount: float):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT referrer_id FROM referrals WHERE user_id = %s", (user_id,))
            row = await cur.fetchone()
            
            if row:
                referrer_id = row[0]
                commission = deposit_amount * 0.01
                
                await cur.execute("""
                    UPDATE referrals 
                    SET current_period_earnings = current_period_earnings + %s 
                    WHERE user_id = %s
                """, (commission, user_id))
                 
                await cur.execute("""
                    UPDATE users 
                    SET pending_commission = pending_commission + %s 
                    WHERE user_id = %s
                """, (commission, referrer_id))





async def get_deposit_bonus_rate():
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT value FROM settings WHERE s_key='deposit_bonus'")
            r = await cur.fetchone()
            try:
                return float(r[0]) / 100 if r else 0.0
            except:
                return 0.0

async def set_deposit_bonus_rate(percentage):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE settings SET value=%s WHERE s_key='deposit_bonus'",
                (str(percentage),)
            )


async def check_and_add_pending_deposit(user_id: int, amount: float, tx_type: str) -> bool:
    """
    التحقق من وجود طلب معلق، وإذا لم يوجد يتم إضافته فوراً في معاملة واحدة محمية.
    تعيد True إذا تم إضافة الطلب بنجاح.
    تعيد False إذا كان لدى المستخدم طلب معلق بالفعل.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لقفل العملية وحمايتها من التضارب المحلي
                await conn.begin()
                
                # 1. التحقق من وجود طلب سابق
                await cur.execute("SELECT 1 FROM pending WHERE user_id = %s", (user_id,))
                existing = await cur.fetchone()
                
                if existing:
                    # ننهي المعاملة ونعيد False لأن لديه طلب معلق
                    await conn.commit()
                    return False
                
                # 2. إذا لم يكن لديه طلب، يتم الإدخال فوراً
                await cur.execute(
                    "INSERT INTO pending (user_id, amount, type) VALUES (%s, %s, %s)",
                    (user_id, amount, tx_type)
                )
                
                # تثبيت الحفظ التلقائي وفك قفل الجدول في XAMPP
                await conn.commit()
                return True
                
            except Exception as e:
                # في حال حدوث أي خطأ مفاجئ، يتم التراجع لحماية الداتابيز
                print(f"❌ خطأ في دالة التحقق والإدخال لـ pending: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return False
            
async def fetch_and_delete_pending(user_id: int) -> float:
    """
    تقوم بجلب مبلغ الطلب المعلق للمستخدم وحذفه فوراً في معاملة واحدة آمنة.
    تعيد المبلغ (float) إذا كان الطلب موجوداً، أو تعيد None إذا لم تجده.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                
                # 1. جلب المبلغ
                await cur.execute("SELECT amount FROM pending WHERE user_id = %s", (user_id,))
                row = await cur.fetchone()
                
                if not row:
                    await conn.commit()
                    return None
                
                amount = float(row[0])
                
                # 2. حذف الطلب فوراً لمنع التكرار
                await cur.execute("DELETE FROM pending WHERE user_id = %s", (user_id,))
                
                await conn.commit()
                return amount
                
            except Exception as e:
                print(f"❌ خطأ في fetch_and_delete_pending: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return None

async def delete_pending_only(user_id: int) -> bool:
    """
    حذف الطلب المعلق للمستخدم مباشرة (حالة الرفض).
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                await cur.execute("DELETE FROM pending WHERE user_id = %s", (user_id,))
                await conn.commit()
                return True
            except Exception as e:
                print(f"❌ خطأ في delete_pending_only: {e}")
                return False

async def get_user_referral_stats(user_id: int):
    """
    جلب إحصائيات الإحالة الخاصة بالمستخدم في معاملة سريعة وآمنة.
    تعيد tuple يحتوي على (referrals_count, balance, pending_commission) أو None إذا لم يوجد المستخدم.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                await cur.execute(
                    "SELECT referrals_count, balance, pending_commission FROM users WHERE user_id = %s",
                    (user_id,)
                )
                row = await cur.fetchone()
                await conn.commit()
                return row
            except Exception as e:
                print(f"❌ خطأ في دالة get_user_referral_stats: {e}")
                return None

async def redeem_gift_code_db(user_id: int, code: str):
    """
    التحقق من الكود وتفعيله للمستخدم وتحديث حالته كمستخدم في معاملة ذرية (Atomic) واحدة.
    تعيد:
      - (True, amount) إذا تم التفعيل بنجاح.
      - (False, "not_found") إذا كان الكود غير صحيح.
      - (False, "already_used") إذا كان الكود مستخدماً مسبقاً.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لقفل السجل فوراً أثناء الفحص
                await conn.begin()
                
                # 1. جلب بيانات الكود
                await cur.execute("SELECT amount, used FROM gift_codes WHERE code = %s", (code,))
                result = await cur.fetchone()
                
                if not result:
                    await conn.commit()
                    return False, "not_found"
                
                amount, used = result
                if used == 1:
                    await conn.commit()
                    return False, "already_used"
                
                # 2. تحديث الكود ليصبح مستخدماً لمنع أي شخص آخر من قراءته في نفس اللحظة
                await cur.execute("UPDATE gift_codes SET used = 1 WHERE code = %s", (code,))
                
                # 3. إضافة الرصيد للمستخدم مباشرة من داخل المعاملة (تأكد أن دالة add_balance تدعم الاستدعاء الطبيعي)
                await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
                
                # حفظ التغييرات قطيعاً وفك الأقفال
                await conn.commit()
                return True, amount
                
            except Exception as e:
                print(f"❌ خطأ في دالة redeem_gift_code_db: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return False, "error"

async def get_user_transactions_paginated(user_id: int, query_type: str, limit: int, offset: int):
    """
    جلب عمليات المستخدم (إيداع أو سحب) مقسمة لصفحات مع حساب العدد الإجمالي للعمليات.
    تعيد tuple يحتوي على: (قائمة الصفوف المسترجعة, العدد الإجمالي)
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لضمان سرعة واستقرار القراءة
                await conn.begin()
                
                # 1. استعلام جلب الصفوف المحددة للصفحة الحالية
                await cur.execute("""
                    SELECT type, amount, status, txid, created_at
                    FROM transactions
                    WHERE user_id = %s AND type LIKE %s
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """, (user_id, query_type, limit, offset))
                rows = await cur.fetchall()
                
                # 2. استعلام حساب المجموع الكلي لمعرفة هل توجد صفحة تالية أم لا
                await cur.execute("""
                    SELECT COUNT(*)
                    FROM transactions
                    WHERE user_id = %s AND type LIKE %s
                """, (user_id, query_type))
                
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0
                
                # إنهاء المعاملة وتأكيد تحرير الجدول
                await conn.commit()
                return rows, total
                
            except Exception as e:
                print(f"❌ خطأ في دالة get_user_transactions_paginated: {e}")
                return [], 0

async def check_and_add_pending_withdraw(user_id: int, amount: float, tx_type: str) -> tuple:
    """
    دالة فحص رصيد السحب وإدخال الطلب المعلق مع خصم الرصيد فوراً (حجزه) لمنع التلاعب.
    تعيد tuple: (True/False, "الرسالة أو الحالة")
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لقفل السجلات وحمايتها محلياً في XAMPP
                await conn.begin()
                
                # 1. جلب رصيد المستخدم الحالي والتحقق منه
                await cur.execute("SELECT balance FROM users WHERE user_id = %s", (user_id,))
                user_row = await cur.fetchone()
                if not user_row:
                    await conn.commit()
                    return False, "user_not_found"
                
                balance = float(user_row[0])
                if balance < amount:
                    await conn.commit()
                    return False, "insufficient_balance"
                
                # 2. التحقق من عدم وجود طلب معلق سابق (سواء شحن أو سحب)
                await cur.execute("SELECT 1 FROM pending WHERE user_id = %s", (user_id,))
                existing = await cur.fetchone()
                if existing:
                    await conn.commit()
                    return False, "has_pending"
                
                # 3. خصم الرصيد فوراً وحجزه من حساب المستخدم
                await cur.execute("UPDATE users SET balance = balance - %s WHERE user_id = %s", (amount, user_id))
                
                # 4. إدخال الطلب في جدول الـ pending
                await cur.execute(
                    "INSERT INTO pending (user_id, amount, type) VALUES (%s, %s, %s)",
                    (user_id, amount, tx_type)
                )
                
                # حفظ التغييرات وتحرير الجداول
                await conn.commit()
                return True, "success"
                
            except Exception as e:
                print(f"❌ خطأ في دالة check_and_add_pending_withdraw: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return False, "error"

async def accept_pending_withdraw_db(user_id: int) -> float:
    """
    قبول عملية السحب: جلب مبلغ السحب المعلق وحذفه من جدول الـ pending.
    (الرصيد مخصوم مسبقاً عند تقديم الطلب)
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                
                # 1. جلب المبلغ المعلق للتأكد من وجوده
                await cur.execute("SELECT amount FROM pending WHERE user_id = %s", (user_id,))
                row = await cur.fetchone()
                if not row:
                    await conn.commit()
                    return None
                
                amount = float(row[0])
                
                # 2. حذف الطلب المعلق بنجاح
                await cur.execute("DELETE FROM pending WHERE user_id = %s", (user_id,))
                
                await conn.commit()
                return amount
                
            except Exception as e:
                print(f"❌ خطأ في دالة accept_pending_withdraw_db: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return None

async def reject_pending_withdraw_db(user_id: int) -> float:
    """
    رفض عملية السحب: جلب المبلغ المعلق، حذفه، وإعادة الرصيد المحجوز للمستخدم بالكامل.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                
                # 1. جلب المبلغ لإعادته للمستخدم
                await cur.execute("SELECT amount FROM pending WHERE user_id = %s", (user_id,))
                row = await cur.fetchone()
                if not row:
                    await conn.commit()
                    return None
                
                amount = float(row[0])
                
                # 2. إعادة الرصيد المحجوز للمستخدم
                await cur.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (amount, user_id))
                
                # 3. حذف الطلب من الـ pending
                await cur.execute("DELETE FROM pending WHERE user_id = %s", (user_id,))
                
                await conn.commit()
                return amount
                
            except Exception as e:
                print(f"❌ خطأ في دالة reject_pending_withdraw_db: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return None

async def get_all_users_admin(limit: int = 100):
    """
    جلب قائمة بالمستخدمين (محددة بـ 100 مستخدم كحد أقصى تفادياً لانفجار نص الرسالة) 
    في معاملة سريعة ومغلقة فوراً.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                # جلب أعلى 100 مستخدم كمثال، يمكنك تعديل الـ limit أو جلب الإجمالي
                await cur.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT %s", (limit,))
                rows = await cur.fetchall()
                await conn.commit()
                return rows
            except Exception as e:
                print(f"❌ خطأ في دالة get_all_users_admin: {e}")
                return []

async def get_all_ichancy_accounts_admin(limit: int = 80):
    """
    جلب قائمة بحسابات Ichancy المسجلة (محددة بـ 80 حساب كحد أقصى لحماية حجم رسالة تلجرام)
    في معاملات سريعة ومغلقة فوراً لحماية سيرفر XAMPP.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                # جلب البيانات وترتيبها من الأحدث للأقدم مع وضع حد أقصى للـ limit
                await cur.execute("SELECT user_id, email, password, username FROM usersichancy ORDER BY user_id DESC LIMIT %s", (limit,))
                rows = await cur.fetchall()
                await conn.commit()
                return rows
            except Exception as e:
                print(f"❌ خطأ في دالة get_all_ichancy_accounts_admin: {e}")
                return []

async def add_gift_code_db(code: str, amount: int) -> bool:
    """
    إضافة كود هدية جديد إلى قاعدة البيانات في معاملة سريعة ومحمية.
    تعيد True إذا تمت الإضافة بنجاح، أو False في حال حدوث خطأ (مثل تكرار الكود إذا كان PRIMARY KEY).
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لقفل العملية وحمايتها
                await conn.begin()
                
                # إدخال الكود الجديد
                await cur.execute(
                    "INSERT INTO gift_codes (code, amount, used) VALUES (%s, %s, 0)",
                    (code, amount)
                )
                
                # تثبيت الحفظ وفك قفل الجدول فوراً
                await conn.commit()
                return True
            except Exception as e:
                print(f"❌ خطأ في دالة add_gift_code_db: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return False

async def get_target_user_transactions_admin(target_id: int, query_type: str, limit: int, offset: int):
    """
    جلب عمليات مستخدم معين (إيداع أو سحب) مقسمة لصفحات للأدمن، مع حساب العدد الإجمالي.
    تعيد tuple يحتوي على: (قائمة الصفوف المسترجعة, العدد الإجمالي)
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لضمان عزل وسرعة الاستعلام في XAMPP
                await conn.begin()
                
                # 1. استعلام جلب الصفوف المحددة للصفحة الحالية
                await cur.execute("""
                    SELECT type, amount, status, txid, created_at
                    FROM transactions
                    WHERE user_id = %s AND type LIKE %s
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                """, (target_id, query_type, limit, offset))
                rows = await cur.fetchall()
                
                # 2. استعلام حساب المجموع الكلي لمعرفة حدود الصفحات
                await cur.execute("""
                    SELECT COUNT(*)
                    FROM transactions
                    WHERE user_id = %s AND type LIKE %s
                """, (target_id, query_type))
                
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0
                
                # إنهاء المعاملة قطيعاً وتأكيد تحرير الجداول
                await conn.commit()
                return rows, total
                
            except Exception as e:
                print(f"❌ خطأ في دالة get_target_user_transactions_admin: {e}")
                return [], 0

async def distribute_referral_commissions_db():
    """
    توزيع أرباح الإحالات المعلقة لجميع المستخدمين وتصفير العدادات في معاملة ذرية سريعة ومحمية.
    تعيد قائمة بـ tuples تحتوي على (user_id, commission) لإرسال الإشعارات لهم لاحقاً خارج الداتابيز.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لقفل الجداول وتحديثها معاً بأمان
                await conn.begin()
                
                # 1. جلب المستخدمين الذين يملكون عمولات مستحقة
                await cur.execute("SELECT user_id, pending_commission FROM users WHERE pending_commission > 0")
                winners = await cur.fetchall()
                
                if not winners:
                    await conn.commit()
                    return []
                
                # 2. تحديث أرصدة المستخدمين وتصفير عمولاتهم المعلقة دفعة واحدة وبسرعة خرافية
                await cur.execute("""
                    UPDATE users 
                    SET balance = balance + pending_commission, 
                        pending_commission = 0 
                    WHERE pending_commission > 0
                """)
                
                # 3. تصفير أرباح الفترة الحالية في جدول الإحالات
                await cur.execute("UPDATE referrals SET current_period_earnings = 0")
                
                # تثبيت المعاملة قطيعاً وفك أقفال الجداول فوراً
                await conn.commit()
                return winners
                
            except Exception as e:
                print(f"❌ خطأ في دالة distribute_referral_commissions_db: {e}")
                try:
                    await conn.rollback()
                except:
                    pass
                return []


async def get_bonus_from_db() -> str:
    """
    جلب نص البونص الحالي من جدول bot_settings بأمان وسرعة.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()
                await cur.execute("SELECT value FROM bot_settings WHERE `key` = 'bonus_text'")
                result = await cur.fetchone()
                await conn.commit()
                
                # التحقق من أن النتيجة ليست فارغة ولها قيمة
                if result and result[0]:
                    return str(result[0])
                return "🎉 لا توجد عروض حالياً"
                
            except Exception as e:
                print(f"❌ خطأ في دالة get_bonus_from_db: {e}")
                return "🎉 لا توجد عروض حالياً"

async def update_bonus_in_db(new_text: str) -> bool:
    """
    تحديث نص البونص في جدول bot_settings في معاملة ذرية محمية لمنع تعليق XAMPP.
    تعيد True في حال النجاح.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                # بدء المعاملة لقفل السجل وحمايته أثناء التعديل
                await conn.begin()
                
                # تنفيذ التحديث بناءً على الـ Schema الخاصة بك
                await cur.execute(
                    "UPDATE bot_settings SET value = %s WHERE `key` = 'bonus_text'", 
                    (new_text,)
                )
                
                # تأكيد الحفظ التلقائي وفك الأقفال فوراً
                await conn.commit()
                return True
                
            except Exception as e:
                print(f"❌ خطأ في دالة update_bonus_in_db: {e}")
                try:
                    await conn.rollback()  # التراجع في حال حدوث خطأ مفاجئ
                except:
                    pass
                return False



