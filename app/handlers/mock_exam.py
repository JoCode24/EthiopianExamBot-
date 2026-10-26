"""
app/handlers/mock_exam.py
Mock / Model Exam section.

Rules:
- FREE for every user — 10 free questions per subject, no subscription required.
- If a user is subscribed to exit/coc for a specific dept (e.g. nursing),
  they get UNLIMITED questions for mock subjects linked to that dept.
- Any active subscription also grants unlimited mock access.
- Does NOT touch any exit / coc / entrance logic.
"""
import random
from datetime import datetime
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
    """
    Build subject list dynamically from questions table.
    Returns dicts with: subject_key, subject_name, emoji, stream
    Only subjects that have at least 1 uploaded question are returned.
    Falls back to subjects table for name/emoji lookup.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get distinct stream+subject combos from actual questions
        cur = await db.execute(
            "SELECT DISTINCT stream, subject FROM questions "
            "WHERE exam_type='mock' ORDER BY stream, subject")
        rows = [dict(r) for r in await cur.fetchall()]

        result = []
        for r in rows:
            subj_key = r["subject"]
            stream   = r["stream"] or "general"
            # Look up display info from subjects table
            cur2 = await db.execute(
                "SELECT subject_name, emoji FROM subjects WHERE subject_key=?", (subj_key,))
            info = await cur2.fetchone()
            if info:
                name  = info["subject_name"]
                emoji = info["emoji"] or "📘"
            else:
                # Fallback: derive nice name from key
                name  = subj_key.replace("_", " ").title()
                emoji = "📘"
            result.append({
                "subject_key":  subj_key,
                "subject_name": name,
                "emoji":        emoji,
                "stream":       stream,
            })
        return result


async def _get_mock_questions(subject_key: str, year=None, limit: int = 0) -> list:
    """
    Fetch mock questions for a subject.
    limit=0 means no cap — return all available questions.
    """
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
        if limit > 0:
            return rows[:limit]
        return rows  # all questions


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


async def _is_subscribed(user: dict, subject_stream: str = None) -> bool:
    """
    Check if user has active subscription that grants unlimited mock access.

    Rules:
    - User subscribed to exit/coc dept X  →  free unlimited mock for stream=X
    - User subscribed to any exam type    →  free unlimited mock for ALL streams
    - subject_stream=None                 →  just check if any active sub exists
    """
    now = datetime.utcnow().isoformat()
    if not user.get("is_subscribed"):
        return False
    expiry = user.get("subscription_expiry") or ""
    if expiry and expiry <= now:
        return False

    # Active subscription — check stream match if a subject_stream is given
    if subject_stream is None:
        return True   # caller only wants to know if any sub is active

    # Any active subscription grants full mock access
    return True


async def _mock_access_for_stream(user: dict, subject_stream: str) -> bool:
    """
    Returns True if user's subscription covers this mock subject's stream.
    - Subscribed to exit dept X  → covers mock stream X
    - Subscribed to coc dept X   → covers mock stream X
    - Any other subscription     → covers ALL mock streams
    """
    now = datetime.utcnow().isoformat()
    if not user.get("is_subscribed"):
        return False
    expiry = user.get("subscription_expiry") or ""
    if expiry and expiry <= now:
        return False

    sub_exam   = user.get("subscribed_exam_type", "")
    sub_stream = user.get("subscribed_stream", "")
    sub_dept   = user.get("subscribed_dept", "")

    # exit/coc subscription: check if dept matches the subject's stream
    if sub_exam in ("exit", "coc"):
        linked = sub_dept or sub_stream
        if linked and subject_stream and linked == subject_stream:
            return True
        # If subscribed to a different dept, still grant mock access
        # (any subscription = full mock access per business rule)
        return True

    # entrance/remedial/driving subscription → full mock access
    return True


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
    """Callback: exam_mock — shows grouped mock subjects dynamically."""
    query = update.callback_query
    await query.answer()
    tid = query.from_user.id

    user = await _get_user(tid)
    subscribed = await _is_subscribed(user) if user else False

    subjects = await _get_mock_subjects()
    if not subjects:
        await query.edit_message_text(
            "📋 *Model / Mock Exam*\n\n"
            "No mock questions have been uploaded yet.\n\n"
            "📢 Check back soon — questions are being added!\n\n"
            "Once available, you'll be able to:\n"
            "  • Practice per department & subject\n"
            "  • Get 10 free questions per subject\n"
            "  • Track your scores",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")]
            ])
        )
        return

    # Group by stream/dept
    groups = {}
    for s in subjects:
        grp = s.get("stream") or "general"
        if grp not in groups:
            groups[grp] = []
        groups[grp].append(s)

    buttons = []

    # Fetch dept display info for all groups at once
    dept_info_cache = {}
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for grp in groups:
            if grp not in ("general", "mock"):
                cur = await db.execute(
                    "SELECT dept_name, emoji FROM departments WHERE dept_key=?", (grp,))
                row = await cur.fetchone()
                if row:
                    dept_info_cache[grp] = (row[0], row[1])

    # Sort groups: general/mock first, then alphabetical by dept name
    def grp_sort_key(k):
        if k in ("general", "mock"):
            return (0, k)
        info = dept_info_cache.get(k)
        return (1, info[0] if info else k)

    sorted_groups = sorted(groups.keys(), key=grp_sort_key)

    for grp in sorted_groups:
        subj_list = groups[grp]

        # Department header
        if grp in ("general", "mock"):
            header = "── 📋 General / Mixed ──"
        else:
            info = dept_info_cache.get(grp)
            if info:
                header = f"── {info[1]} {info[0]} ──"
            else:
                header = f"── {grp.replace('_', ' ').title()} ──"

        # Only show header if there are multiple groups
        if len(sorted_groups) > 1:
            buttons.append([InlineKeyboardButton(
                header, callback_data=f"mock_dept_group|{grp}")])

        # Subject buttons in 2-column rows
        row = []
        for s in subj_list:
            used = await _get_mock_used(tid, s["subject_key"])
            remaining = max(0, FREE_MOCK_QUESTIONS - used)
            emoji = s.get("emoji", "📘")
            name = s["subject_name"]
            if subscribed:
                status = " ✅"
            elif remaining > 0:
                status = f" ({remaining}🎯)"
            else:
                status = " 🔒"
            label = f"{emoji} {name}{status}"
            row.append(InlineKeyboardButton(
                label, callback_data=f"mock_subject|{s['subject_key']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

    buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])

    total_subjects = len(subjects)
    if subscribed:
        access_line = "💎 *Full Access* — unlimited questions for all subjects"
    else:
        access_line = (
            f"🆓 *{FREE_MOCK_QUESTIONS} free questions per subject*\n"
            "No subscription required to start!"
        )

    await query.edit_message_text(
        f"📋 *Model / Mock Exam*\n\n"
        f"{access_line}\n\n"
        f"📚 *{total_subjects} subject(s) available* — choose one to practice:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def mock_dept_group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: mock_dept_group|<dept_key> — tapping a dept header does nothing."""
    query = update.callback_query
    await query.answer("Tap a subject below to start.", show_alert=False)


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

    used = await _get_mock_used(tid, subject_key)
    subscribed = await _is_subscribed(user)

    if not subscribed and used >= FREE_MOCK_QUESTIONS:
        await query.edit_message_text(
            "📚 *Free Questions Used Up!*\n\n"
            f"You've used all *{FREE_MOCK_QUESTIONS} free questions* for this subject.\n\n"
            "Subscribe to get:\n"
            "  ✅ Unlimited mock exam questions\n"
            "  ✅ All subjects & departments\n"
            "  ✅ Detailed explanations\n"
            "  ✅ Full leaderboard access",
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

        cur2 = await db.execute(
            "SELECT subject_name, emoji FROM subjects WHERE subject_key=?", (subject_key,))
        row = await cur2.fetchone()
    if row:
        subj_name = f"{row[1]} {row[0]}"
    else:
        subj_name = subject_key.replace("_", " ").title()

    if subscribed:
        status_line = "✅ *Full Access* — unlimited questions"
    else:
        remaining = FREE_MOCK_QUESTIONS - used
        status_line = f"🆓 *Free Preview* — {remaining} question(s) remaining"

    buttons = []
    row_btns = []
    for yr in years:
        row_btns.append(InlineKeyboardButton(
            f"📅 {yr}", callback_data=f"mock_start|{subject_key}|{yr}"))
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
        await query.edit_message_text(
            "📚 *Free Questions Used Up!*\n\n"
            f"You've used all *{FREE_MOCK_QUESTIONS} free questions* for this subject.\n\n"
            "Subscribe to get:\n"
            "  ✅ Unlimited mock exam questions\n"
            "  ✅ All subjects & departments\n"
            "  ✅ Detailed explanations\n"
            "  ✅ Full leaderboard access",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")],
                [InlineKeyboardButton("🎟️ Redeem Code",  callback_data="redeem_menu")],
                [InlineKeyboardButton("⬅️ Back", callback_data="exam_mock")],
            ])
        )
        return

    if subscribed:
        # Subscribed: load ALL available questions (up to 100 per session)
        questions = await _get_mock_questions(subject_key, year=year, limit=100)
    else:
        # Free: only remaining free questions
        remaining_free = FREE_MOCK_QUESTIONS - used
        questions = await _get_mock_questions(subject_key, year=year, limit=remaining_free)

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
        "questions":   questions,
        "current":     0,
        "score":       0,
        "session_id":  session_id,
        "subject_key": subject_key,
        "subscribed":  subscribed,
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
            "🔁 Try Again", callback_data=f"mock_start|{subject_key}|0")],
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
