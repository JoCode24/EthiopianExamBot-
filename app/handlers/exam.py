"""
app/handlers/exam.py
Handles all exam flow: subject selection, question delivery,
answer checking, scoring, leaderboard, retry.

Access rules:
- Every user (including admin) gets FREE_QUESTIONS_PER_SUBJECT (5) free questions per subject.
- After free questions are used up, user must subscribe.
- Subscription gives unlimited access ONLY to the subscribed exam_type + stream/dept.
- has_full_access() is called with BOTH stream= AND dept= so exit/coc subscriptions work.
"""
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import aiosqlite
from config import DATABASE_PATH, FREE_QUESTIONS_PER_SUBJECT
from app.utils.access import has_full_access, can_do_free_for_subject, increment_free_for_subject
from app.utils.logger import logger


# ── DB helpers ──────────────────────────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_questions(exam_type: str, subject_key: str,
                        stream: str = None, year: int = None,
                        limit: int = 0) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM questions WHERE exam_type=? AND subject=?"
        params = [exam_type, subject_key]
        if stream:
            query += " AND (stream=? OR stream IS NULL OR stream='')"
            params.append(stream)
        if year:
            query += " AND year=?"
            params.append(year)
        cur = await db.execute(query, params)
        rows = await cur.fetchall()
        questions = [dict(r) for r in rows]
        random.shuffle(questions)
        if limit > 0:
            return questions[:limit]
        return questions


async def get_subjects_for(exam_type: str, stream: str = None) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if stream:
            cur = await db.execute(
                "SELECT * FROM subjects WHERE exam_type=? AND stream=?", (exam_type, stream))
        else:
            cur = await db.execute("SELECT * FROM subjects WHERE exam_type=?", (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


async def save_exam_session(telegram_id: int, exam_type: str, stream: str,
                            subject: str, year, total: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO exam_sessions "
            "(telegram_id, exam_type, stream, subject, year, total, score, completed) "
            "VALUES (?,?,?,?,?,?,0,0)",
            (telegram_id, exam_type, stream or "", subject, year, total))
        await db.commit()
        return cur.lastrowid


async def update_exam_score(session_id: int, score: int, completed: int = 0):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE exam_sessions SET score=?, completed=?, finished_at=datetime('now') "
            "WHERE id=?", (score, completed, session_id))
        await db.commit()


async def get_leaderboard(exam_type: str, subject: str, limit: int = 10) -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT u.full_name, u.username, es.score, es.total, "
            "CAST(es.score AS REAL)/es.total*100 AS pct "
            "FROM exam_sessions es "
            "JOIN users u ON u.telegram_id=es.telegram_id "
            "WHERE es.exam_type=? AND es.subject=? AND es.completed=1 AND es.total>0 "
            "ORDER BY pct DESC, es.score DESC LIMIT ?",
            (exam_type, subject, limit))
        return [dict(r) for r in await cur.fetchall()]


# ── Subscription paywall message ────────────────────────────────────────────────

async def _show_paywall(query, used: int):
    """Show the subscription required message politely."""
    await query.edit_message_text(
        "📚 *You've completed your free questions!*\n\n"
        f"You've used all *{used} free questions* for this subject.\n\n"
        "To continue practicing and access:\n"
        "  ✅ Unlimited questions\n"
        "  ✅ All subjects & years\n"
        "  ✅ Detailed explanations\n"
        "  ✅ Performance leaderboard\n\n"
        "👉 Subscribe now for only *50 ETB/month* and keep going! 🚀",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
            [InlineKeyboardButton("🎟️ Redeem Code", callback_data="redeem_menu")],
            [InlineKeyboardButton("🏠 Main Menu",    callback_data="main_menu")],
        ]),
    )


# ── Direct subject flow ─────────────────────────────────────────────────────────

async def direct_subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: direct_subject_<exam_type>|<stream>|<subject_key>
    stream field is used for both stream (entrance/remedial) and dept (exit/coc).
    """
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    raw = query.data.replace("direct_subject_", "")
    parts = raw.split("|")
    if len(parts) < 3:
        await query.edit_message_text("⚠️ Invalid subject selection.")
        return

    exam_type, stream_or_dept, subject_key = parts[0], parts[1], parts[2]
    stream_or_dept = stream_or_dept or ""

    user = await get_user(tid)
    if not user:
        await query.edit_message_text("Please start the bot first with /start")
        return

    # Determine stream vs dept for access check
    stream_val = stream_or_dept if exam_type in ("entrance", "remedial") else None
    dept_val   = stream_or_dept if exam_type in ("exit", "coc") else None

    full_access = await has_full_access(user, exam_type, stream=stream_val, dept=dept_val)
    can_free, used = await can_do_free_for_subject(tid, subject_key)

    if not full_access and not can_free:
        await _show_paywall(query, FREE_QUESTIONS_PER_SUBJECT)
        return

    # Get available years
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT year FROM questions "
            "WHERE exam_type=? AND subject=? AND year IS NOT NULL ORDER BY year DESC",
            (exam_type, subject_key))
        years = [r[0] for r in await cur.fetchall()]

    buttons = []
    row = []
    for yr in years:
        row.append(InlineKeyboardButton(
            f"📅 {yr}",
            callback_data=f"start_exam_{exam_type}|{stream_or_dept}|{subject_key}|{yr}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        "🎲 Random Mix",
        callback_data=f"start_exam_{exam_type}|{stream_or_dept}|{subject_key}|0"
    )])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])

    # Subject display name
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT subject_name, emoji FROM subjects WHERE subject_key=?", (subject_key,))
        row_s = await cur.fetchone()
    subj_name = f"{row_s[1]} {row_s[0]}" if row_s else subject_key

    if full_access:
        status_line = "✅ *Full Access* — unlimited questions"
    else:
        free_left = FREE_QUESTIONS_PER_SUBJECT - used
        status_line = f"🆓 *Free Preview* — {free_left} question(s) remaining"

    await query.edit_message_text(
        f"📚 *{subj_name}*\n\n"
        f"{status_line}\n\n"
        "Select a year or try a random mix:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def start_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the exam.
    Callback: start_exam_<exam_type>|<stream_or_dept>|<subject_key>|<year>
    """
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    raw = query.data.replace("start_exam_", "")
    parts = raw.split("|")
    if len(parts) < 4:
        await query.edit_message_text("⚠️ Invalid exam selection.")
        return

    exam_type, stream_or_dept, subject_key, year_str = parts[0], parts[1], parts[2], parts[3]
    year = int(year_str) if year_str and year_str != "0" else None
    stream_or_dept = stream_or_dept or ""

    user = await get_user(tid)
    if not user:
        await query.edit_message_text("Please start the bot first with /start")
        return

    # Determine stream vs dept
    stream_val = stream_or_dept if exam_type in ("entrance", "remedial") else None
    dept_val   = stream_or_dept if exam_type in ("exit", "coc") else None

    full_access = await has_full_access(user, exam_type, stream=stream_val, dept=dept_val)
    can_free, used = await can_do_free_for_subject(tid, subject_key)

    if full_access:
        max_q = 0  # 0 = no cap, return all available questions
    elif can_free:
        max_q = FREE_QUESTIONS_PER_SUBJECT - used  # Only remaining free questions
    else:
        await _show_paywall(query, FREE_QUESTIONS_PER_SUBJECT)
        return

    questions = await get_questions(exam_type, subject_key,
                                     stream=stream_val or stream_or_dept or None,
                                     year=year, limit=max_q)
    if not questions:
        await query.edit_message_text(
            "😕 *No questions found*\n\n"
            "The admin hasn't uploaded questions for this selection yet.\n"
            "Please check back later!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
            ])
        )
        return

    session_id = await save_exam_session(
        tid, exam_type, stream_or_dept, subject_key, year, len(questions))

    context.user_data["exam"] = {
        "questions": questions,
        "current": 0,
        "score": 0,
        "session_id": session_id,
        "exam_type": exam_type,
        "stream_or_dept": stream_or_dept,
        "stream_val": stream_val,
        "dept_val": dept_val,
        "subject_key": subject_key,
        "year": year,
        "full_access": full_access,
    }

    await _send_question(query, context)


async def _send_question(query, context: ContextTypes.DEFAULT_TYPE):
    """Renders the current question."""
    exam = context.user_data.get("exam")
    if not exam:
        return

    q_list = exam["questions"]
    idx = exam["current"]
    total = len(q_list)

    if idx >= total:
        await _finish_exam(query, context)
        return

    q = q_list[idx]
    num = idx + 1
    bar_filled = round(num / total * 10)
    progress_bar = "▓" * bar_filled + "░" * (10 - bar_filled)

    buttons = [
        [InlineKeyboardButton(f"🅐  {q['option_a']}", callback_data="answer_A")],
        [InlineKeyboardButton(f"🅑  {q['option_b']}", callback_data="answer_B")],
        [InlineKeyboardButton(f"🅒  {q['option_c']}", callback_data="answer_C")],
        [InlineKeyboardButton(f"🅓  {q['option_d']}", callback_data="answer_D")],
    ]

    text = (
        f"📝 *Question {num} of {total}*\n"
        f"`{progress_bar}` {num}/{total}\n\n"
        f"{q['question_text']}"
    )

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user's answer. Callback: answer_<A|B|C|D>"""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    exam = context.user_data.get("exam")
    if not exam:
        await query.edit_message_text("⚠️ No active exam. Use /start to begin.")
        return

    choice = query.data.replace("answer_", "").upper()
    idx = exam["current"]
    q = exam["questions"][idx]
    correct = q["correct_answer"].upper()

    is_correct = (choice == correct)
    if is_correct:
        exam["score"] += 1
        icon = "✅"
        verdict = "*Correct!* 🎉"
    else:
        icon = "❌"
        verdict = f"*Wrong.* Correct answer: *{correct}*"

    # Count free usage if not subscribed
    if not exam.get("full_access"):
        await increment_free_for_subject(tid, exam["subject_key"])

    explanation = q.get("explanation") or ""
    expl_block = f"\n\n💡 *Explanation:*\n{explanation}" if explanation else ""

    options_display = (
        f"\n\n🅐  {q['option_a']}\n"
        f"🅑  {q['option_b']}\n"
        f"🅒  {q['option_c']}\n"
        f"🅓  {q['option_d']}"
    )

    text = f"{icon} {verdict}{options_display}{expl_block}"

    exam["current"] += 1
    remaining = len(exam["questions"]) - exam["current"]

    # If free user: check if they've hit the limit
    if not exam.get("full_access"):
        _, used_now = await can_do_free_for_subject(tid, exam["subject_key"])
        # used_now is actually current used count; check against limit
        from app.utils.access import get_free_used_for_subject
        used_total = await get_free_used_for_subject(tid, exam["subject_key"])
        if used_total >= FREE_QUESTIONS_PER_SUBJECT:
            # Force end of exam after showing this result
            exam["current"] = len(exam["questions"])
            remaining = 0

    if remaining > 0:
        nav_row = [InlineKeyboardButton(f"➡️ Next  ({remaining} left)", callback_data="next_question")]
    else:
        nav_row = [InlineKeyboardButton("🏁 See Results", callback_data="next_question")]

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([nav_row]),
    )


async def next_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Advances to next question or shows results."""
    query = update.callback_query
    await query.answer()

    exam = context.user_data.get("exam")
    if not exam:
        await query.edit_message_text("⚠️ No active exam. Use /start to begin.")
        return

    if exam["current"] >= len(exam["questions"]):
        await _finish_exam(query, context)
    else:
        await _send_question(query, context)


async def _finish_exam(query, context: ContextTypes.DEFAULT_TYPE):
    """Shows final score and options."""
    exam = context.user_data.get("exam")
    if not exam:
        return

    score = exam["score"]
    total = len(exam["questions"])
    pct = round(score / total * 100) if total else 0
    session_id = exam.get("session_id")

    if session_id:
        await update_exam_score(session_id, score, completed=1)

    # Store for leaderboard
    context.user_data["last_exam_type"] = exam["exam_type"]
    context.user_data["last_subject"] = exam["subject_key"]

    # Grade
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

    full_access = exam.get("full_access", False)

    kb_rows = [
        [InlineKeyboardButton(
            "🔁 Try Again",
            callback_data=f"retry_exam_{exam['exam_type']}|{exam['stream_or_dept']}|{exam['subject_key']}|{exam.get('year') or 0}"
        )],
        [InlineKeyboardButton("🏅 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]

    if not full_access:
        kb_rows.insert(1, [InlineKeyboardButton("💎 Unlock Full Access", callback_data="subscribe")])

    await query.edit_message_text(
        f"{grade_icon} *Exam Complete!*\n\n"
        f"{bar}\n\n"
        f"✅ Score: *{score} / {total}*  ({pct}%)\n\n"
        f"_{grade_msg}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )
    context.user_data.pop("exam", None)


async def retry_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: retry_exam_<exam_type>|<stream_or_dept>|<subject_key>|<year>"""
    query = update.callback_query
    await query.answer()
    raw = query.data.replace("retry_exam_", "")
    query.data = f"start_exam_{raw}"
    await start_exam_handler(update, context)


# ── Subscribed exam flow ────────────────────────────────────────────────────────

async def my_subscribed_exams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: my_sub_exams"""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    user = await get_user(tid)
    if not user:
        await query.edit_message_text("Please /start first.")
        return

    from datetime import datetime
    now = datetime.utcnow().isoformat()
    is_sub = bool(user.get("is_subscribed"))
    expiry = user.get("subscription_expiry") or ""
    sub_active = is_sub and (not expiry or expiry > now)

    if not sub_active:
        await query.edit_message_text(
            "❌ *No Active Subscription*\n\n"
            "You don't have an active subscription yet.\n\n"
            "Subscribe to access your exam subjects!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
            ])
        )
        return

    sub_exam = user.get("subscribed_exam_type") or ""
    sub_stream = user.get("subscribed_stream") or ""
    sub_dept = user.get("subscribed_dept") or ""
    stream_for_query = sub_stream or sub_dept or None

    subjects = await get_subjects_for(sub_exam, stream_for_query)

    buttons = [
        [InlineKeyboardButton(
            f"{s['emoji']} {s['subject_name']}",
            callback_data=f"sub_subject_{s['subject_key']}"
        )]
        for s in subjects
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])

    exp_text = f"\n📅 Expires: `{expiry[:10]}`" if expiry else ""
    await query.edit_message_text(
        f"📋 *Your Subscription*\n\n"
        f"📚 Exam: *{sub_exam.title()}*\n"
        f"🔀 Stream/Dept: *{sub_stream or sub_dept or 'General'}*"
        f"{exp_text}\n\n"
        "Choose a subject to practice:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def sub_subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: sub_subject_<subject_key>"""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    subject_key = query.data.replace("sub_subject_", "")
    context.user_data["sub_subject"] = subject_key

    user = await get_user(tid)
    if not user:
        return

    exam_type = user.get("subscribed_exam_type") or ""
    stream_or_dept = user.get("subscribed_stream") or user.get("subscribed_dept") or ""

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT year FROM questions "
            "WHERE exam_type=? AND subject=? AND year IS NOT NULL ORDER BY year DESC",
            (exam_type, subject_key))
        years = [r[0] for r in await cur.fetchall()]

    buttons = []
    row = []
    for yr in years:
        row.append(InlineKeyboardButton(str(yr), callback_data=f"subexamyear_{yr}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🎲 Random Mix", callback_data="subexamyear_0")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="my_sub_exams")])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT subject_name, emoji FROM subjects WHERE subject_key=?", (subject_key,))
        row_s = await cur.fetchone()
    subj_name = f"{row_s[1]} {row_s[0]}" if row_s else subject_key

    await query.edit_message_text(
        f"📚 *{subj_name}*\n\nChoose a year:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def sub_year_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: subexamyear_<year>"""
    query = update.callback_query
    await query.answer()

    year_str = query.data.replace("subexamyear_", "")
    subject_key = context.user_data.get("sub_subject", "")
    tid = query.from_user.id

    user = await get_user(tid)
    if not user:
        return

    exam_type = user.get("subscribed_exam_type") or ""
    stream_or_dept = user.get("subscribed_stream") or user.get("subscribed_dept") or ""

    query.data = f"start_exam_{exam_type}|{stream_or_dept}|{subject_key}|{year_str}"
    await start_exam_handler(update, context)


async def sub_start_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias: substart_<...> → delegates to start_exam_handler"""
    query = update.callback_query
    raw = query.data.replace("substart_", "")
    query.data = f"start_exam_{raw}"
    await start_exam_handler(update, context)


# ── Leaderboard ─────────────────────────────────────────────────────────────────

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: leaderboard"""
    query = update.callback_query
    await query.answer()

    last_exam_type = context.user_data.get("last_exam_type", "")
    last_subject = context.user_data.get("last_subject", "")

    if not last_exam_type or not last_subject:
        await query.edit_message_text(
            "ℹ️ *Leaderboard*\n\nComplete an exam first to see the leaderboard!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ])
        )
        return

    rows = await get_leaderboard(last_exam_type, last_subject)

    if not rows:
        text = "🏅 *Leaderboard*\n\nNo completed exams recorded yet. Be the first!"
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 *Top Scores*\n"]
        for i, r in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = r.get("full_name") or r.get("username") or "Anonymous"
            pct = round(r.get("pct") or 0)
            lines.append(f"{medal} {name} — {r['score']}/{r['total']} ({pct}%)")
        text = "\n".join(lines)

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
    )
