"""
app/handlers/start.py
/start command, main menu, stream/dept navigation.

Changes from previous version:
- Removed "Admin Panel" button from user-facing main menu.
  Admin panel is accessed via /admin command only.
- Fixed stream_ callback separator: uses | instead of _ to avoid
  conflicts with exam_type names like "entrance".
- Fixed dept_ callback separator: uses | instead of _ to avoid
  splitting dept_keys like "computer_science".
"""
from datetime import datetime
import secrets
import string

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import aiosqlite
from config import DATABASE_PATH, ADMIN_ID
from app.utils.logger import logger


async def _ensure_user(user_obj, referral_code: str = None):
    """Create or update user record. New users get 1 free trial day."""
    tid = user_obj.id
    username = user_obj.username or ""
    full_name = user_obj.full_name or ""
    is_admin_flag = 1 if tid == ADMIN_ID else 0

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT referral_code FROM users WHERE telegram_id=?", (tid,))
        existing = await cur.fetchone()

        if not existing:
            ref_code = "".join(
                secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            referred_by = None

            if referral_code:
                cur2 = await db.execute(
                    "SELECT telegram_id FROM users WHERE referral_code=?", (referral_code,))
                ref_row = await cur2.fetchone()
                if ref_row:
                    referred_by = referral_code
                    # +3 days for referrer
                    await db.execute(
                        "UPDATE users SET referral_count=referral_count+1, "
                        "free_access_expiry=CASE "
                        "  WHEN free_access_expiry IS NULL OR free_access_expiry < datetime('now') "
                        "  THEN datetime('now','+3 days') "
                        "  ELSE datetime(free_access_expiry,'+3 days') END "
                        "WHERE telegram_id=?", (ref_row[0],))

            await db.execute(
                "INSERT OR IGNORE INTO users "
                "(telegram_id, username, full_name, is_admin, referral_code, referred_by) "
                "VALUES (?,?,?,?,?,?)",
                (tid, username, full_name, is_admin_flag, ref_code, referred_by))
        else:
            await db.execute(
                "UPDATE users SET username=?, full_name=?, is_admin=?, "
                "last_active=datetime('now') WHERE telegram_id=?",
                (username, full_name, is_admin_flag, tid))
        await db.commit()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start [referral_code]"""
    user_obj = update.effective_user
    args = context.args or []
    referral_code = args[0] if args else None
    await _ensure_user(user_obj, referral_code)
    await _show_main_menu(update, context)


async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_obj = update.effective_user
    tid = user_obj.id

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tid,))
        user = await cur.fetchone()

    if not user:
        return
    user = dict(user)

    now_str = datetime.utcnow().isoformat()
    is_sub = bool(user.get("is_subscribed"))
    sub_exam = user.get("subscribed_exam_type") or ""
    expiry = user.get("subscription_expiry") or ""
    free_expiry = user.get("free_access_expiry") or ""
    sub_active = is_sub and (not expiry or expiry > now_str)
    trial_active = bool(free_expiry and free_expiry > now_str)

    # Status badge
    if sub_active:
        status = f"💎 Subscribed — {sub_exam.title()}"
    elif trial_active:
        days_left = (datetime.fromisoformat(free_expiry) - datetime.utcnow()).days + 1
        status = f"🆓 Free Trial — {days_left} day(s) left"
    else:
        status = "🔓 Free Mode (5 q/subject · 10 free on Model Exam)"

    # Main menu buttons — NO admin panel button here
    buttons = [
        [
            InlineKeyboardButton("📝 Entrance",   callback_data="exam_entrance"),
            InlineKeyboardButton("🎓 Exit Exam",  callback_data="exam_exit"),
        ],
        [
            InlineKeyboardButton("📋 Remedial",   callback_data="exam_remedial"),
            InlineKeyboardButton("🚗 Driving",    callback_data="exam_driving"),
        ],
        [
            InlineKeyboardButton("🏅 COC Exam",   callback_data="exam_coc"),
            InlineKeyboardButton("📋 Model Exam", callback_data="exam_mock"),
        ],
    ]

    if sub_active:
        buttons.append([InlineKeyboardButton(
            "📚 My Subscribed Exams", callback_data="my_sub_exams")])

    buttons.append([
        InlineKeyboardButton("💎 Subscribe",    callback_data="subscribe"),
        InlineKeyboardButton("🎟️ Redeem Code", callback_data="redeem_menu"),
    ])
    buttons.append([
        InlineKeyboardButton("👥 Refer & Earn",  callback_data="referral"),
        InlineKeyboardButton("🏆 Leaderboard",  callback_data="leaderboard"),
    ])

    first_name = user_obj.first_name or "Student"
    text = (
        f"👋 Hello, *{first_name}*! 🇪🇹\n\n"
        f"📊 Status: {status}\n\n"
        "Practice for Ethiopian national exams.\n"
        "Choose a category to begin:"
    )

    kb = InlineKeyboardMarkup(buttons)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catch-all for unmatched callback queries."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await _show_main_menu(update, context)
        return

    if data.startswith("exam_"):
        exam_type = data.replace("exam_", "")
        await _show_exam_type(query, exam_type)
        return

    if data == "redeem_menu":
        await query.edit_message_text(
            "🎟️ *Redeem a Code*\n\n"
            "Type the command below with your code:\n\n"
            "`/redeem YOUR_CODE`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
            ])
        )
        return

    if data == "referral":
        tid = query.from_user.id
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT referral_code, referral_count FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
        if row:
            code, count = row
            link = f"https://t.me/EthioExamBot?start={code}"
            await query.edit_message_text(
                f"👥 *Refer & Earn*\n\n"
                f"Your referral link:\n`{link}`\n\n"
                f"✅ Friends referred: *{count}*\n"
                f"🎁 Each referral = *+3 free days* for both of you!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]
                ])
            )
        return

    # Unknown — go home
    await query.edit_message_text(
        "⚠️ Something went wrong. Returning to menu...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
    )


async def _show_exam_type(query, exam_type: str):
    """Shows stream or dept selection depending on exam type."""
    exam_labels = {
        "entrance": "🎓 University Entrance Exam",
        "exit":     "📋 University Exit Exam",
        "remedial": "📚 Remedial Exam",
        "driving":  "🚗 Driving License Exam",
        "coc":      "🏅 COC Competency Exam",
        "mock":     "📋 Model / Mock Exam",
    }
    title = exam_labels.get(exam_type, exam_type.title())

    if exam_type in ("entrance", "remedial"):
        # Use | separator: stream|entrance|natural
        buttons = [
            [InlineKeyboardButton("🔬 Natural Science",
                                  callback_data=f"stream|{exam_type}|natural")],
            [InlineKeyboardButton("📚 Social Science",
                                  callback_data=f"stream|{exam_type}|social")],
            [InlineKeyboardButton("⬅️ Back", callback_data="main_menu")],
        ]
        await query.edit_message_text(
            f"*{title}*\n\nChoose your stream:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif exam_type in ("exit", "coc"):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM departments WHERE exam_type=?", (exam_type,))
            depts = [dict(r) for r in await cur.fetchall()]
        # Use | separator: dept|exit|computer_science
        buttons = [
            [InlineKeyboardButton(
                f"{d['emoji']} {d['dept_name']}",
                callback_data=f"dept|{exam_type}|{d['dept_key']}"
            )]
            for d in depts
        ]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        label = "department" if exam_type == "exit" else "field"
        await query.edit_message_text(
            f"*{title}*\n\nChoose your {label}:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif exam_type == "driving":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM subjects WHERE exam_type='driving'")
            subjects = [dict(r) for r in await cur.fetchall()]
        buttons = [
            [InlineKeyboardButton(
                f"{s['emoji']} {s['subject_name']}",
                callback_data=f"direct_subject_{exam_type}|general|{s['subject_key']}"
            )]
            for s in subjects
        ]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        await query.edit_message_text(
            f"*{title}*\n\nChoose a topic:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    else:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM subjects WHERE exam_type=?", (exam_type,))
            subjects = [dict(r) for r in await cur.fetchall()]
        buttons = [
            [InlineKeyboardButton(
                f"{s['emoji']} {s['subject_name']}",
                callback_data=f"direct_subject_{exam_type}|{s.get('stream','')}|{s['subject_key']}"
            )]
            for s in subjects
        ]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
        await query.edit_message_text(
            f"*{title}*\n\nChoose a subject:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )


# ── Stream selection handler ────────────────────────────────────────────────────

async def stream_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: stream|<exam_type>|<stream>  (pipe-separated)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")   # ["stream", "entrance", "natural"]
    if len(parts) < 3:
        await query.edit_message_text("⚠️ Invalid stream selection.")
        return

    _, exam_type, stream = parts[0], parts[1], parts[2]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects WHERE exam_type=? AND stream=?", (exam_type, stream))
        subjects = [dict(r) for r in await cur.fetchall()]

    if not subjects:
        await query.edit_message_text(
            "😕 *No subjects found*\n\nNo subjects uploaded for this stream yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data=f"exam_{exam_type}")]
            ])
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"{s['emoji']} {s['subject_name']}",
            callback_data=f"direct_subject_{exam_type}|{stream}|{s['subject_key']}"
        )]
        for s in subjects
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"exam_{exam_type}")])

    stream_label = "Natural Science 🔬" if stream == "natural" else "Social Science 📚"
    await query.edit_message_text(
        f"*{stream_label}*\n\nChoose a subject:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ── Department selection handler ────────────────────────────────────────────────

async def dept_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: dept|<exam_type>|<dept_key>  (pipe-separated — safe with computer_science)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("|")   # ["dept", "exit", "computer_science"]
    if len(parts) < 3:
        await query.edit_message_text("⚠️ Invalid department selection.")
        return

    _, exam_type, dept_key = parts[0], parts[1], parts[2]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects WHERE exam_type=? AND stream=?", (exam_type, dept_key))
        subjects = [dict(r) for r in await cur.fetchall()]

    if not subjects:
        await query.edit_message_text(
            "😕 *No subjects found*\n\nNo subjects uploaded for this department yet.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data=f"exam_{exam_type}")]
            ])
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"{s['emoji']} {s['subject_name']}",
            callback_data=f"direct_subject_{exam_type}|{dept_key}|{s['subject_key']}"
        )]
        for s in subjects
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data=f"exam_{exam_type}")])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT dept_name, emoji FROM departments WHERE dept_key=?", (dept_key,))
        row = await cur.fetchone()
    dept_label = f"{row[1]} {row[0]}" if row else dept_key

    await query.edit_message_text(
        f"*{dept_label}*\n\nChoose a subject:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )