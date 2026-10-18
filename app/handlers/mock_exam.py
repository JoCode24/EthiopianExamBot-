"""
app/handlers/mock_exam.py
Mock / Model Exam section.

Rules:
- FREE for every user — no subscription required.
- Each user gets FREE_MOCK_QUESTIONS (10) free questions per subject key.
  Tracked in the same free_subject_usage table as regular exams (subject key
  is unique so there's no collision with entrance/exit/coc subjects).
- After 10 questions are exhausted the user is offered to subscribe for unlimited access.
- Does NOT touch any exit / coc / entrance logic.
"""
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import aiosqlite
from config import DATABASE_PATH, FREE_MOCK_QUESTIONS
from app.utils.logger import logger


# ── DB helpers ──────────────────────────────────────────────────────────────────

async def _get_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def _get_mock_subjects() -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects WHERE exam_type='mock' ORDER BY subject_name")
        return [dict(r) for r in await cur.fetchall()]


async def _get_mock_questions(subject_key: str, year=None, limit: int = 40) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        sql = "SELECT * FROM questions WHERE exam_type='mock' AND subject=?"
        params = [subject_key]
        if year:
            sql += " AND year=?"
            params.append(year)
        cur = await db.execute(sql, params)
        rows = [dict(r) for r in await cur.fetchall()]
        random.shuffle(rows)
        return rows[:limit]


async def _get_mock_used(telegram_id: int, subject_key: str) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS free_subject_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                used_count INTEGER DEFAULT 0,
                UNIQUE(telegram_id, subject)
            )""")
        await db.commit()
        cur = await db.execute(
            "SELECT used_count FROM free_subject_usage WHERE telegram_id=? AND subject=?",
            (telegram_id, subject_key))
        row = await cur.fetchone()
        return row[0] if row else 0


async def _increment_mock_used(telegram_id: int, subject_key: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS free_subject_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                used_count INTEGER DEFAULT 0,
                UNIQUE(telegram_id, subject)
            )""")
        await db.commit()
        row = await (await db.execute(
            "SELECT used_count FROM free_subject_usage WHERE telegram_id=? AND subject=?",
            (telegram_id, subject_key))).fetchone()
        if row:
            await db.execute(
                "UPDATE free_subject_usage SET used_count=used_count+1 "
                "WHERE telegram_id=? AND subject=?", (telegram_id, subject_key))
        else:
            await db.execute(
                "INSERT INTO free_subject_usage (telegram_id,subject,used_count) VALUES (?,?,1)",
                (telegram_id, subject_key))
        await db.commit()


async def _is_subscribed(user: dict) -> bool:
    """Check if user has any active subscription (for unlimited mock questions)."""
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    if not user.get("is_subscribed"):
        return False
    expiry = user.get("subscription_expiry") or ""
    return not expiry or expiry > now


async def _save_session(telegram_id: int, subject_key: str, total: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO exam_sessions "
            "(telegram_id, exam_type, stream, subject, year, total, score, completed) "
            "VALUES (?,?,?,?,?,?,0,0)",
            (telegram_id, "mock", "mock", subject_key, None, total))
        await db.commit()
        return cur.lastrowid


async def _update_session(session_id: int, score: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE exam_sessions SET score=?, completed=1, finished_at=datetime('now') "
            "WHERE id=?", (score, session_id))
        await db.commit()


# ── Handlers ────────────────────────────────────────────────────────────────────

async def mock_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: exam_mock  — shows all mock subjects."""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    subjects = await _get_mock_subjects()
    if not subjects:
        await query.edit_message_text(
            "📋 *Model Exam*\n\n"
            "No subjects have been uploaded yet.\n"
            "Check back soon — questions are being added!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
            ])
        )
        return

    buttons = []
    for s in subjects:
        used = await _get_mock_used(tid, s["subject_key"])
        remaining = max(0, FREE_MOCK_QUESTIONS - used)
        label = f"{s['emoji']} {s['subject_name']}"
        if remaining > 0:
            label += f"  ({remaining} free)"
        else:
            label += "  ✅ done"
        buttons.append([InlineKeyboardButton(
            label,
            callback_data=f"mock_subject|{s['subject_key']}"
        )])

    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])

    await query.edit_message_text(
        "📋 *Model / Mock Exam*\n\n"
        f"🆓 *{FREE_MOCK_QUESTIONS} free questions per subject — no subscription needed!*\n\n"
        "Pick a subject to start practicing:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def mock_subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: mock_subject|<subject_key>"""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    subject_key = query.data.split("|", 1)[1]
    user = await _get_user(tid)
    if not user:
        await query.edit_message_text("Please start the bot first with /start")
        return

    # Check remaining free questions
    used = await _get_mock_used(tid, subject_key)
    subscribed = await _is_subscribed(user)

    if not subscribed and used >= FREE_MOCK_QUESTIONS:
        await query.edit_message_text(
            "📚 *Free Questions Used Up!*\n\n"
            f"You've used all *{FREE_MOCK_QUESTIONS} free questions* for this subject.\n\n"
            "Subscribe to get:\n"
            "  ✅ Unlimited mock exam questions\n"
            "  ✅ All subjects & topics\n"
            "  ✅ Detailed explanations\n"
            "  ✅ Full leaderboard access\n\n"
            "👉 Only *50 ETB/month* — keep practicing! 🚀",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
                [InlineKeyboardButton("🎟️ Redeem Code",  callback_data="redeem_menu")],
                [InlineKeyboardButton("⬅️ Back to Mock Exam", callback_data="exam_mock")],
            ])
        )
        return

    # Get available years
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT year FROM questions "
            "WHERE exam_type='mock' AND subject=? AND year IS NOT NULL ORDER BY year DESC",
            (subject_key,))
        years = [r[0] for r in await cur.fetchall()]

    # Subject display name
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT subject_name, emoji FROM subjects WHERE subject_key=?", (subject_key,))
        row = await cur.fetchone()
    subj_name = f"{row[1]} {row[0]}" if row else subject_key

    if subscribed:
        status_line = "✅ *Full Access* — unlimited questions"
    else:
        remaining = FREE_MOCK_QUESTIONS - used
        status_line = f"🆓 *Free Preview* — {remaining} question(s) remaining"

    buttons = []
    row_btns = []
    for yr in years:
        row_btns.append(InlineKeyboardButton(
            f"📅 {yr}",
            callback_data=f"mock_start|{subject_key}|{yr}"
        ))
        if len(row_btns) == 3:
            buttons.append(row_btns)
            row_btns = []
    if row_btns:
        buttons.append(row_btns)

    buttons.append([InlineKeyboardButton(
        "🎲 Random Mix", callback_data=f"mock_start|{subject_key}|0")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="exam_mock")])

    await query.edit_message_text(
        f"📚 *{subj_name}*\n\n"
        f"{status_line}\n\n"
        "Select a year or try a random mix:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def mock_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: mock_start|<subject_key>|<year>"""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    parts = query.data.split("|")
    subject_key = parts[1]
    year_str = parts[2] if len(parts) > 2 else "0"
    year = int(year_str) if year_str and year_str != "0" else None

    user = await _get_user(tid)
    if not user:
        await query.edit_message_text("Please start the bot first with /start")
        return

    used = await _get_mock_used(tid, subject_key)
    subscribed = await _is_subscribed(user)

    if not subscribed and used >= FREE_MOCK_QUESTIONS:
        # Re-check — show paywall
        await query.edit_message_text(
            "📚 *Free Questions Used Up!*\n\n"
            f"You've used all *{FREE_MOCK_QUESTIONS} free questions* for this subject.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
                [InlineKeyboardButton("⬅️ Back", callback_data="exam_mock")],
            ])
        )
        return

    max_q = 40 if subscribed else (FREE_MOCK_QUESTIONS - used)
    questions = await _get_mock_questions(subject_key, year=year, limit=max_q)

    if not questions:
        await query.edit_message_text(
            "😕 *No questions found*\n\n"
            "Questions for this subject haven't been uploaded yet.\n"
            "Please check back later!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="exam_mock")]
            ])
        )
        return

    session_id = await _save_session(tid, subject_key, len(questions))

    context.user_data["mock_exam"] = {
        "questions":    questions,
        "current":      0,
        "score":        0,
        "session_id":   session_id,
        "subject_key":  subject_key,
        "subscribed":   subscribed,
    }

    await _send_mock_question(query, context)


async def _send_mock_question(query, context: ContextTypes.DEFAULT_TYPE):
    exam = context.user_data.get("mock_exam")
    if not exam:
        return

    q_list = exam["questions"]
    idx = exam["current"]
    total = len(q_list)

    if idx >= total:
        await _finish_mock_exam(query, context)
        return

    q = q_list[idx]
    num = idx + 1
    bar_filled = round(num / total * 10)
    progress_bar = "▓" * bar_filled + "░" * (10 - bar_filled)

    buttons = [
        [InlineKeyboardButton(f"🅐  {q['option_a']}", callback_data="mock_answer_A")],
        [InlineKeyboardButton(f"🅑  {q['option_b']}", callback_data="mock_answer_B")],
        [InlineKeyboardButton(f"🅒  {q['option_c']}", callback_data="mock_answer_C")],
        [InlineKeyboardButton(f"🅓  {q['option_d']}", callback_data="mock_answer_D")],
    ]

    await query.edit_message_text(
        f"📋 *Model Exam — Question {num} of {total}*\n"
        f"`{progress_bar}` {num}/{total}\n\n"
        f"{q['question_text']}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def mock_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: mock_answer_<A|B|C|D>"""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    exam = context.user_data.get("mock_exam")
    if not exam:
        await query.edit_message_text("⚠️ No active mock exam. Use /start to begin.")
        return

    choice = query.data.replace("mock_answer_", "").upper()
    idx = exam["current"]
    q = exam["questions"][idx]
    correct = q["correct_answer"].upper()

    is_correct = (choice == correct)
    if is_correct:
        exam["score"] += 1
        icon, verdict = "✅", "*Correct!* 🎉"
    else:
        icon, verdict = "❌", f"*Wrong.* Correct answer: *{correct}*"

    # Count usage if not subscribed
    if not exam.get("subscribed"):
        await _increment_mock_used(tid, exam["subject_key"])

    explanation = q.get("explanation") or ""
    expl_block = f"\n\n💡 *Explanation:*\n{explanation}" if explanation else ""

    options_display = (
        f"\n\n🅐  {q['option_a']}\n"
        f"🅑  {q['option_b']}\n"
        f"🅒  {q['option_c']}\n"
        f"🅓  {q['option_d']}"
    )

    exam["current"] += 1
    remaining = len(exam["questions"]) - exam["current"]

    # Force-end if free user hit the limit mid-exam
    if not exam.get("subscribed"):
        used_now = await _get_mock_used(tid, exam["subject_key"])
        if used_now >= FREE_MOCK_QUESTIONS:
            exam["current"] = len(exam["questions"])
            remaining = 0

    if remaining > 0:
        nav_row = [InlineKeyboardButton(
            f"➡️ Next  ({remaining} left)", callback_data="mock_next")]
    else:
        nav_row = [InlineKeyboardButton("🏁 See Results", callback_data="mock_next")]

    await query.edit_message_text(
        f"{icon} {verdict}{options_display}{expl_block}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([nav_row]),
    )


async def mock_next_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: mock_next"""
    query = update.callback_query
    await query.answer()

    exam = context.user_data.get("mock_exam")
    if not exam:
        await query.edit_message_text("⚠️ No active exam. Use /start to begin.")
        return

    if exam["current"] >= len(exam["questions"]):
        await _finish_mock_exam(query, context)
    else:
        await _send_mock_question(query, context)


async def _finish_mock_exam(query, context: ContextTypes.DEFAULT_TYPE):
    exam = context.user_data.get("mock_exam")
    if not exam:
        return

    score = exam["score"]
    total = len(exam["questions"])
    pct = round(score / total * 100) if total else 0
    session_id = exam.get("session_id")

    if session_id:
        await _update_session(session_id, score)

    if pct >= 80:
        grade_icon, grade_msg = "🏆", "Outstanding! You nailed it!"
    elif pct >= 60:
        grade_icon, grade_msg = "🎯", "Good job! Keep practicing!"
    elif pct >= 40:
        grade_icon, grade_msg = "📈", "Fair result. Keep going!"
    else:
        grade_icon, grade_msg = "📚", "Keep studying — you'll improve!"

    filled = round(pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    subject_key = exam.get("subject_key", "")
    subscribed = exam.get("subscribed", False)

    kb_rows = [
        [InlineKeyboardButton(
            "🔁 Try Again",
            callback_data=f"mock_start|{subject_key}|0"
        )],
        [InlineKeyboardButton("📋 More Subjects", callback_data="exam_mock")],
        [InlineKeyboardButton("🏠 Main Menu",     callback_data="main_menu")],
    ]
    if not subscribed:
        kb_rows.insert(1, [InlineKeyboardButton(
            "💎 Unlock Unlimited Access", callback_data="subscribe")])

    await query.edit_message_text(
        f"{grade_icon} *Model Exam Complete!*\n\n"
        f"{bar}\n\n"
        f"✅ Score: *{score} / {total}*  ({pct}%)\n\n"
        f"_{grade_msg}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )
    context.user_data.pop("mock_exam", None)