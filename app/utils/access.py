"""
app/utils/access.py
Subscription and free-question access control.

IMPORTANT: Admin users are treated EXACTLY like regular users for exam access.
They get 5 free questions per subject and must subscribe for unlimited access.
Admin privileges only unlock the /admin panel — not exam content.
"""
import aiosqlite
from config import DATABASE_PATH, FREE_QUESTIONS_PER_SUBJECT
from datetime import datetime


async def get_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def is_any_admin(telegram_id: int) -> bool:
    """For admin panel access only — does NOT grant exam bypass."""
    from config import ADMIN_ID
    if telegram_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM admin_users WHERE telegram_id=?", (telegram_id,))
        return bool(await cur.fetchone())


async def get_admin_role(telegram_id: int):
    from config import ADMIN_ID
    if telegram_id == ADMIN_ID:
        return "super"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT role FROM admin_users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def has_full_access(user: dict, exam_type: str,
                           stream: str = None, dept: str = None) -> bool:
    """
    Returns True if user has a valid subscription or giveaway trial
    that matches exam_type + stream/dept.

    Admin users get NO special bypass here — they subscribe like everyone else.
    """
    if not user:
        return False

    now = datetime.utcnow().isoformat()

    # Free giveaway/referral trial window
    free_expiry = user.get("free_access_expiry") or ""
    if free_expiry and free_expiry > now:
        return True

    # Must be subscribed
    if not user.get("is_subscribed"):
        return False

    # Subscription must not be expired
    expiry = user.get("subscription_expiry") or ""
    if expiry and expiry < now:
        return False

    # exam_type must match
    sub_exam = user.get("subscribed_exam_type") or ""
    if not sub_exam or sub_exam != exam_type:
        return False

    # entrance / remedial → stream must match
    if exam_type in ("entrance", "remedial"):
        sub_stream = user.get("subscribed_stream") or ""
        if not sub_stream or not stream:
            return False
        return sub_stream == stream

    # exit / coc → dept must match
    if exam_type in ("exit", "coc"):
        sub_dept = user.get("subscribed_dept") or ""
        if not sub_dept or not dept:
            return False
        return sub_dept == dept

    # driving → no sub-category needed
    if exam_type == "driving":
        return True

    return False


async def get_free_used_for_subject(telegram_id: int, subject: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT used_count FROM free_subject_usage "
            "WHERE telegram_id=? AND subject=?",
            (telegram_id, subject))
        row = await cur.fetchone()
        return row[0] if row else 0


async def can_do_free_for_subject(telegram_id: int, subject: str):
    """Returns (can_do: bool, used_count: int)"""
    used = await get_free_used_for_subject(telegram_id, subject)
    return used < FREE_QUESTIONS_PER_SUBJECT, used


async def increment_free_for_subject(telegram_id: int, subject: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        row = await (await db.execute(
            "SELECT used_count FROM free_subject_usage "
            "WHERE telegram_id=? AND subject=?",
            (telegram_id, subject))).fetchone()
        if row:
            await db.execute(
                "UPDATE free_subject_usage SET used_count=used_count+1 "
                "WHERE telegram_id=? AND subject=?",
                (telegram_id, subject))
        else:
            await db.execute(
                "INSERT INTO free_subject_usage (telegram_id, subject, used_count) "
                "VALUES (?,?,1)",
                (telegram_id, subject))
        await db.commit()"""
app/utils/access.py
Subscription and free-question access control.

IMPORTANT: Admin users are treated EXACTLY like regular users for exam access.
They get 5 free questions per subject and must subscribe for unlimited access.
Admin privileges only unlock the /admin panel — not exam content.
"""
import aiosqlite
from config import DATABASE_PATH, FREE_QUESTIONS_PER_SUBJECT
from datetime import datetime


async def get_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def is_any_admin(telegram_id: int) -> bool:
    """For admin panel access only — does NOT grant exam bypass."""
    from config import ADMIN_ID
    if telegram_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM admin_users WHERE telegram_id=?", (telegram_id,))
        return bool(await cur.fetchone())


async def get_admin_role(telegram_id: int):
    from config import ADMIN_ID
    if telegram_id == ADMIN_ID:
        return "super"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT role FROM admin_users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def has_full_access(user: dict, exam_type: str,
                           stream: str = None, dept: str = None) -> bool:
    """
    Returns True if user has a valid subscription or giveaway trial
    that matches exam_type + stream/dept.

    Admin users get NO special bypass here — they subscribe like everyone else.
    """
    if not user:
        return False

    now = datetime.utcnow().isoformat()

    # Free giveaway/referral trial window
    free_expiry = user.get("free_access_expiry") or ""
    if free_expiry and free_expiry > now:
        return True

    # Must be subscribed
    if not user.get("is_subscribed"):
        return False

    # Subscription must not be expired
    expiry = user.get("subscription_expiry") or ""
    if expiry and expiry < now:
        return False

    # exam_type must match
    sub_exam = user.get("subscribed_exam_type") or ""
    if not sub_exam or sub_exam != exam_type:
        return False

    # entrance / remedial → stream must match
    if exam_type in ("entrance", "remedial"):
        sub_stream = user.get("subscribed_stream") or ""
        if not sub_stream or not stream:
            return False
        return sub_stream == stream

    # exit / coc → dept must match
    if exam_type in ("exit", "coc"):
        sub_dept = user.get("subscribed_dept") or ""
        if not sub_dept or not dept:
            return False
        return sub_dept == dept

    # driving → no sub-category needed
    if exam_type == "driving":
        return True

    return False


async def get_free_used_for_subject(telegram_id: int, subject: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT used_count FROM free_subject_usage "
            "WHERE telegram_id=? AND subject=?",
            (telegram_id, subject))
        row = await cur.fetchone()
        return row[0] if row else 0


async def can_do_free_for_subject(telegram_id: int, subject: str):
    """Returns (can_do: bool, used_count: int)"""
    used = await get_free_used_for_subject(telegram_id, subject)
    return used < FREE_QUESTIONS_PER_SUBJECT, used


async def increment_free_for_subject(telegram_id: int, subject: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        row = await (await db.execute(
            "SELECT used_count FROM free_subject_usage "
            "WHERE telegram_id=? AND subject=?",
            (telegram_id, subject))).fetchone()
        if row:
            await db.execute(
                "UPDATE free_subject_usage SET used_count=used_count+1 "
                "WHERE telegram_id=? AND subject=?",
                (telegram_id, subject))
        else:
            await db.execute(
                "INSERT INTO free_subject_usage (telegram_id, subject, used_count) "
                "VALUES (?,?,1)",
                (telegram_id, subject))
        await db.commit()