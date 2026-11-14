"""
app/handlers/user_features.py
══════════════════════════════
User-facing features (all international-standard):

Commands:
  /redeem   — redeem giveaway codes
  /referral — referral link + stats
  /mystats  — personal exam dashboard
  /badges   — achievement badges
  /streak   — study streak status
  /progress — subject-by-subject breakdown

Callbacks:
  user_my_stats  → stats dashboard
  user_badges    → badges list
  user_progress  → progress report
"""
from datetime import datetime, timedelta

import aiosqlite
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import DATABASE_PATH
from app.utils.logger import logger


# ─────────────────────── Badge definitions ───────────────────────────────────
# (id, emoji, name, description, stat_key, threshold)
BADGES = [
    ("first_exam",    "🎓", "First Step",       "Completed your first exam",             "total_exams",     1),
    ("exam_5",        "📚", "Eager Learner",     "Completed 5 exams",                     "total_exams",     5),
    ("exam_25",       "🏅", "Scholar",           "Completed 25 exams",                    "total_exams",    25),
    ("exam_100",      "🏆", "Champion",          "Completed 100 exams",                   "total_exams",   100),
    ("score_80",      "⭐", "High Achiever",     "Scored 80 %+ in an exam",               "best_pct",       80),
    ("score_90",      "💎", "Excellence",        "Scored 90 %+ in an exam",               "best_pct",       90),
    ("score_100",     "🌟", "Perfect Score",     "Achieved 100 % in an exam",             "best_pct",      100),
    ("streak_3",      "🔥", "On Fire",           "3-day consecutive study streak",        "streak_days",     3),
    ("streak_7",      "⚡", "Week Warrior",      "7-day consecutive study streak",        "streak_days",     7),
    ("streak_30",     "🚀", "Month Master",      "30-day consecutive study streak",       "streak_days",    30),
    ("referral_1",    "🤝", "Influencer",        "Referred 1 friend",                     "referral_count",  1),
    ("referral_5",    "📣", "Ambassador",        "Referred 5 friends",                    "referral_count",  5),
    ("subjects_5",    "🗺️", "Explorer",          "Tried 5 different subjects",            "unique_subjects", 5),
    ("subjects_10",   "🌍", "Globetrotter",      "Tried 10 different subjects",           "unique_subjects",10),
]


# ─────────────────────── DB helpers ──────────────────────────────────────────

async def _get_user_stats(tid: int) -> dict | None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
        row = await cur.fetchone()
        if not row:
            return None
        user = dict(row)

        total_exams = (await (await db.execute(
            "SELECT COUNT(*) FROM exam_sessions WHERE telegram_id=? AND completed=1",
            (tid,))).fetchone())[0]

        best_row = (await (await db.execute(
            "SELECT MAX(CAST(score AS REAL)/total*100) FROM exam_sessions "
            "WHERE telegram_id=? AND completed=1 AND total>0", (tid,))).fetchone())[0]
        best_pct = round(best_row or 0)

        unique_subjects = (await (await db.execute(
            "SELECT COUNT(DISTINCT subject) FROM exam_sessions "
            "WHERE telegram_id=? AND completed=1", (tid,))).fetchone())[0]

        cur = await db.execute(
            "SELECT exam_type, COUNT(*), AVG(CAST(score AS REAL)/total*100) "
            "FROM exam_sessions WHERE telegram_id=? AND completed=1 AND total>0 "
            "GROUP BY exam_type", (tid,))
        breakdown = {
            r[0]: {"count": r[1], "avg_pct": round(r[2] or 0)}
            for r in await cur.fetchall()
        }

        cur = await db.execute(
            "SELECT exam_type, subject, score, total, finished_at "
            "FROM exam_sessions WHERE telegram_id=? AND completed=1 "
            "ORDER BY finished_at DESC LIMIT 5", (tid,))
        recent = [dict(r) for r in await cur.fetchall()]

    return {
        "user":            user,
        "total_exams":     total_exams,
        "best_pct":        best_pct,
        "unique_subjects": unique_subjects,
        "breakdown":       breakdown,
        "recent":          recent,
        "streak_days":     user.get("streak_days") or 0,
        "referral_count":  user.get("referral_count") or 0,
    }


def _earned_badges(stats: dict) -> list[dict]:
    earned = []
    for bid, emoji, name, desc, key, threshold in BADGES:
        if (stats.get(key) or 0) >= threshold:
            earned.append({"id": bid, "emoji": emoji, "name": name, "desc": desc})
    return earned


async def update_streak_after_exam(tid: int):
    """Call this after every completed exam to maintain the streak counter."""
    today     = datetime.utcnow().date().isoformat()
    yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT streak_days, last_exam_date FROM users WHERE telegram_id=?", (tid,))
        row = await cur.fetchone()
        if not row:
            return
        streak, last_date = row
        streak = streak or 0
        if last_date == today:
            return
        streak = streak + 1 if last_date == yesterday else 1
        await db.execute(
            "UPDATE users SET streak_days=?, last_exam_date=? WHERE telegram_id=?",
            (streak, today, tid))
        await db.commit()


# ─────────────────────── Render helpers ──────────────────────────────────────

def _sub_status(user: dict) -> str:
    now = datetime.utcnow().isoformat()
    if user.get("is_subscribed") and (not user.get("subscription_expiry")
                                       or user["subscription_expiry"] > now):
        exp = (user.get("subscription_expiry") or "")[:10]
        return f"💎 Active (expires {exp})"
    free_exp = user.get("free_access_expiry") or ""
    if free_exp and free_exp > now:
        return f"🎁 Free access (until {free_exp[:10]})"
    return "🆓 Free tier"


async def _render_stats(send_fn, stats: dict):
    user    = stats["user"]
    name    = user.get("full_name") or user.get("username") or "Student"
    total   = stats["total_exams"]
    best    = stats["best_pct"]
    streak  = stats["streak_days"]
    unique  = stats["unique_subjects"]
    refs    = stats["referral_count"]
    badges  = _earned_badges(stats)
    badge_s = " ".join(b["emoji"] for b in badges) if badges else "—"

    bk = "\n".join(
        f"  • {et.title()}: {v['count']}x  (avg {v['avg_pct']}%)"
        for et, v in stats["breakdown"].items()
    ) if stats["breakdown"] else "  —"

    recent = ""
    for r in stats["recent"][:3]:
        subj = (r.get("subject") or "?").replace("_", " ").title()
        pct  = round(r["score"] / r["total"] * 100) if r["total"] else 0
        icon = "✅" if pct >= 50 else "❌"
        recent += f"  {icon} {subj}: {pct}%\n"

    streak_bar = "🔥" * min(streak, 10)

    text = (
        f"📊 *My Dashboard*\n"
        f"👤 {name}\n\n"
        f"🎓 Subscription: {_sub_status(user)}\n"
        f"🔥 Streak: *{streak} day{'s' if streak != 1 else ''}* {streak_bar}\n\n"
        f"📈 *Totals*\n"
        f"  Exams completed: *{total}*\n"
        f"  Best score: *{best}%*\n"
        f"  Subjects tried: *{unique}*\n"
        f"  Friends referred: *{refs}*\n\n"
        f"📚 *By type*\n{bk}\n\n"
    )
    if recent:
        text += f"🕐 *Recent exams*\n{recent}\n"
    text += f"🏅 *Badges*: {badge_s}"

    await send_fn(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏅 My Badges",  callback_data="user_badges"),
             InlineKeyboardButton("📊 Progress",   callback_data="user_progress")],
            [InlineKeyboardButton("🏠 Main Menu",  callback_data="main_menu")],
        ]))


async def _render_badges(send_fn, stats: dict):
    earned     = _earned_badges(stats)
    earned_ids = {b["id"] for b in earned}
    locked     = [b for b in BADGES if b[0] not in earned_ids]

    text = "🏅 *Achievement Badges*\n\n"
    if earned:
        text += "✅ *Earned:*\n"
        for b in earned:
            text += f"  {b['emoji']} *{b['name']}* — {b['desc']}\n"
        text += "\n"
    if locked:
        text += "🔒 *Locked:*\n"
        for b in locked[:10]:
            _, emoji, name, desc, key, thr = b
            text += f"  🔒 *{name}* — {desc}\n"

    await send_fn(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 My Stats", callback_data="user_my_stats"),
             InlineKeyboardButton("🏠 Menu",     callback_data="main_menu")],
        ]))


# ─────────────────────── Commands ────────────────────────────────────────────

async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/redeem <CODE>"""
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "🎟️ Usage: `/redeem YOUR_CODE`",
            parse_mode=ParseMode.MARKDOWN)
        return

    code = args[0].strip().upper()
    tid  = update.effective_user.id

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id, duration_days, max_uses, used_count FROM giveaway_codes WHERE code=?",
            (code,))
        gc = await cur.fetchone()
        if not gc:
            await update.message.reply_text("❌ Invalid code.")
            return
        gc_id, duration_days, max_uses, used_count = gc
        if used_count >= max_uses:
            await update.message.reply_text("❌ This code has been fully redeemed.")
            return
        cur2 = await db.execute(
            "SELECT 1 FROM giveaway_uses WHERE code=? AND telegram_id=?", (code, tid))
        if await cur2.fetchone():
            await update.message.reply_text("⚠️ You already used this code.")
            return

        expiry = (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        await db.execute(
            "UPDATE users SET "
            "free_access_expiry=CASE "
            "  WHEN free_access_expiry IS NULL OR free_access_expiry < datetime('now') THEN ? "
            "  ELSE datetime(free_access_expiry, ?||' days') END "
            "WHERE telegram_id=?",
            (expiry, str(duration_days), tid))
        await db.execute(
            "INSERT INTO giveaway_uses (code, telegram_id) VALUES (?,?)", (code, tid))
        await db.execute(
            "UPDATE giveaway_codes SET used_count=used_count+1 WHERE id=?", (gc_id,))
        await db.commit()

    await update.message.reply_text(
        f"🎉 *Redeemed!* You have *{duration_days} days* of free access.\n"
        f"📅 Valid until: `{expiry[:10]}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Start Exam", callback_data="main_menu")]
        ]))


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/referral"""
    tid = update.effective_user.id
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT referral_code, referral_count FROM users WHERE telegram_id=?", (tid,))
        row = await cur.fetchone()
    if not row:
        await update.message.reply_text("Please /start first.")
        return
    ref_code, ref_count = row
    me = await context.bot.get_me()
    link = f"https://t.me/{me.username}?start={ref_code}"
    await update.message.reply_text(
        f"👥 *Your Referral Link*\n\n`{link}`\n\n"
        f"👫 Friends referred: *{ref_count}*\n"
        "🎁 Each friend gives you both *+3 free days*!\n\n"
        "Share and help friends prepare for their exams 🇪🇹",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 My Stats", callback_data="user_my_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]))


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mystats"""
    stats = await _get_user_stats(update.effective_user.id)
    if not stats:
        await update.message.reply_text("Please /start first.")
        return
    await _render_stats(update.message.reply_text, stats)


async def badges_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/badges"""
    stats = await _get_user_stats(update.effective_user.id)
    if not stats:
        await update.message.reply_text("Please /start first.")
        return
    await _render_badges(update.message.reply_text, stats)


async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/streak"""
    stats = await _get_user_stats(update.effective_user.id)
    if not stats:
        await update.message.reply_text("Please /start first.")
        return
    streak = stats["streak_days"]
    fire   = "🔥" * min(streak, 10)
    if streak == 0:
        msg = "😴 *No active streak.*\nTake an exam today to start one!"
    elif streak < 7:
        msg = f"🔥 *{streak}-day streak!* Keep it up!\n{fire}"
    elif streak < 30:
        msg = f"⚡ *{streak}-day streak!* Week Warrior!\n{fire}"
    else:
        msg = f"🚀 *{streak}-day streak!* You're a Month Master!\n{fire}"
    await update.message.reply_text(
        msg + "\n\n📅 Take one exam per day to keep your streak alive.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Take Exam", callback_data="main_menu")]
        ]))


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/progress"""
    tid = update.effective_user.id
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT subject, exam_type, COUNT(*) cnt, "
            "AVG(CAST(score AS REAL)/total*100) avg_pct, "
            "MAX(CAST(score AS REAL)/total*100) best_pct "
            "FROM exam_sessions WHERE telegram_id=? AND completed=1 AND total>0 "
            "GROUP BY subject ORDER BY avg_pct DESC", (tid,))
        rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        await update.message.reply_text(
            "📊 No exam history yet.\nComplete some exams to see your progress!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Start Exam", callback_data="main_menu")]
            ]))
        return

    lines = ["📊 *Subject Progress*\n"]
    for r in rows[:15]:
        subj = (r["subject"] or "?").replace("_", " ").title()
        avg  = round(r["avg_pct"] or 0)
        best = round(r["best_pct"] or 0)
        bar  = "🟩" * (avg // 10) + "⬜" * (10 - avg // 10)
        lines.append(f"📚 *{subj}*\n`{bar}` {avg}% avg | Best {best}% | {r['cnt']}×")

    await update.message.reply_text(
        "\n\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏅 Badges",    callback_data="user_badges"),
             InlineKeyboardButton("📊 My Stats",  callback_data="user_my_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]))


# ─────────────────────── Callback handlers ───────────────────────────────────

async def user_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = await _get_user_stats(query.from_user.id)
    if not stats:
        await query.edit_message_text("Please /start first.")
        return
    await _render_stats(query.edit_message_text, stats)


async def user_badges_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = await _get_user_stats(query.from_user.id)
    if not stats:
        await query.edit_message_text("Please /start first.")
        return
    await _render_badges(query.edit_message_text, stats)


async def user_progress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT subject, exam_type, COUNT(*) cnt, "
            "AVG(CAST(score AS REAL)/total*100) avg_pct, "
            "MAX(CAST(score AS REAL)/total*100) best_pct "
            "FROM exam_sessions WHERE telegram_id=? AND completed=1 AND total>0 "
            "GROUP BY subject ORDER BY avg_pct DESC", (tid,))
        rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        await query.edit_message_text(
            "📊 No exam history yet. Complete some exams first!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Start Exam", callback_data="main_menu")]
            ]))
        return

    lines = ["📊 *Subject Progress*\n"]
    for r in rows[:12]:
        subj = (r["subject"] or "?").replace("_", " ").title()
        avg  = round(r["avg_pct"] or 0)
        best = round(r["best_pct"] or 0)
        bar  = "🟩" * (avg // 10) + "⬜" * (10 - avg // 10)
        lines.append(f"📚 *{subj}*\n`{bar}` {avg}% avg | Best {best}% | {r['cnt']}×")

    await query.edit_message_text(
        "\n\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏅 Badges",    callback_data="user_badges"),
             InlineKeyboardButton("📊 Stats",     callback_data="user_my_stats")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]))
