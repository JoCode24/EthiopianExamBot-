"""
app/handlers/subscription.py

Handles the full subscription flow:
  /subscribe → pick exam type → stream/dept (if needed) → bank info →
  "I've Paid" → send receipt photo → admin notified with approve/reject buttons.

Supports multiple active subscriptions per user.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import receipt_action_keyboard
from config import DATABASE_PATH, ADMIN_ID
import aiosqlite

logger = logging.getLogger(__name__)

EXAM_TYPES = ["entrance", "exit", "coc", "driving", "remedial", "mock"]
STREAMS    = ["Natural", "Social"]


# ─────────────────────── Helpers ─────────────────────────────────────────────

async def check_subscription(
    telegram_id: int,
    exam_type: str,
    stream: str | None = None,
    dept: str | None = None,
) -> bool:
    """Return True if the user has an active subscription for the given exam."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            """
            SELECT id FROM subscriptions
            WHERE telegram_id = ?
              AND exam_type   = ?
              AND (stream = ? OR stream IS NULL OR ? IS NULL)
              AND (dept   = ? OR dept   IS NULL OR ? IS NULL)
              AND is_active = 1
              AND expiry_at > datetime('now')
            """,
            (telegram_id, exam_type, stream, stream, dept, dept),
        )
        row = await cur.fetchone()
        return row is not None


async def _get_bank_accounts() -> list[dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT bank_name, account_number, account_holder "
            "FROM bank_accounts WHERE is_active=1"
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


def _exam_type_keyboard() -> InlineKeyboardMarkup:
    labels = {
        "entrance": "🎓 የዩኒቨርሲቲ መግቢያ ፈተና",
        "exit":     "🏛️ የመውጫ ፈተና (Exit Exam)",
        "coc":      "🏅 CoC ፈተና",
        "driving":  "🚗 የመኪና ፈቃድ ፈተና",
        "remedial": "📝 የማሟያ ፈተና (Remedial)",
        "mock":     "📋 የሞዴል ፈተና (Mock)",
    }
    buttons = [
        [InlineKeyboardButton(labels[et], callback_data=f"sub_exam_{et}")]
        for et in EXAM_TYPES
    ]
    buttons.append([InlineKeyboardButton("❌ ሰርዝ", callback_data="cancel_sub")])
    return InlineKeyboardMarkup(buttons)


def _stream_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔬 የተፈጥሮ ሳይንስ", callback_data="sub_stream_natural")],
        [InlineKeyboardButton("📚 ማህበራዊ ሳይንስ",  callback_data="sub_stream_social")],
        [InlineKeyboardButton("❌ ሰርዝ",           callback_data="cancel_sub")],
    ])


async def _dept_keyboard_from_db(exam_type: str, stream) -> InlineKeyboardMarkup:
    """Build dept keyboard from the departments table (for exit / coc)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT dept_key, dept_name, emoji FROM departments "
            "WHERE exam_type=? ORDER BY dept_name",
            (exam_type,)
        )
        depts = [dict(r) for r in await cur.fetchall()]

    if not depts:
        # Fallback hardcoded lists per exam type
        exit_depts = [
            ("nursing","Nursing","🩺"),("medicine","Medicine","⚕️"),
            ("pharmacy","Pharmacy","💊"),("engineering","Engineering","⚙️"),
            ("accounting","Accounting","📊"),("law","Law","⚖️"),
        ]
        coc_depts = [
            ("coc_electrical","Electrical","⚡"),("coc_construction","Construction","🏗️"),
            ("coc_it","IT","💻"),("coc_welding","Welding","🔧"),
            ("coc_auto","Automotive","🚗"),("coc_textile","Textile","🧵"),
        ]
        if exam_type == "coc":
            depts_raw = coc_depts
        else:
            depts_raw = exit_depts
        depts = [{"dept_key": k, "dept_name": n, "emoji": e} for k, n, e in depts_raw]

    buttons = [
        [InlineKeyboardButton(
            f"{d.get('emoji','🏛️')} {d['dept_name']}",
            callback_data=f"sub_dept_{d['dept_key']}"
        )]
        for d in depts
    ]
    buttons.append([InlineKeyboardButton("❌ ሰርዝ", callback_data="cancel_sub")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────── Cancel subscription flow ────────────────────────────

async def cancel_sub_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # Clear any pending subscription state
    for key in ("sub_exam_type", "sub_stream", "sub_dept", "waiting_for"):
        context.user_data.pop(key, None)
    await query.edit_message_text(
        "❌ *ምዝገባ ተሰርዟል።*\n\nወደ ዋናው ምናሌ ለመመለስ /start ብለው ያስገቡ።",
        parse_mode="Markdown",
    )


# ─────────────────────── /subscribe entry ────────────────────────────────────

async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send = query.edit_message_text
    else:
        send = update.message.reply_text

    await send(
        "📚 *ለመመዝገብ የፈተና አይነት ይምረጡ:*\n\n"
        "በአንድ ጊዜ ለብዙ ፈተናዎች መመዝገብ ይቻላል።",
        parse_mode="Markdown",
        reply_markup=_exam_type_keyboard(),
    )


# ─────────────────────── Step 1: exam type ───────────────────────────────────

async def sub_exam_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    exam_type = query.data.replace("sub_exam_", "")
    context.user_data["sub_exam_type"] = exam_type
    context.user_data["sub_stream"]    = None
    context.user_data["sub_dept"]      = None

    _exam_labels = {
        "entrance": "🎓 የዩኒቨርሲቲ መግቢያ ፈተና",
        "exit":     "🏛️ የመውጫ ፈተና",
        "coc":      "🏅 CoC ፈተና",
        "driving":  "🚗 የመኪና ፈቃድ ፈተና",
        "remedial": "📝 (Remedial) የማሟያ ፈተና",
        "mock":     "📋 የሞዴል ፈተና",
    }
    exam_label = _exam_labels.get(exam_type, exam_type.capitalize())

    if exam_type in ("entrance", "remedial"):
        # Stream only (natural / social) → then straight to bank, NO dept step
        await query.edit_message_text(
            f"📖 *{exam_label}*\n\nየትምህርት ዘርፍዎን ይምረጡ:",
            parse_mode="Markdown",
            reply_markup=_stream_keyboard(),
        )
    elif exam_type in ("exit", "coc"):
        # Department only (from DB) → straight to bank, NO stream step
        await query.edit_message_text(
            f"🏛️ *{exam_label}*\n\nክፍሎትን ይምረጡ:",
            parse_mode="Markdown",
            reply_markup=await _dept_keyboard_from_db(exam_type, None),
        )
    else:
        # driving, mock → straight to bank, no selection at all
        await _show_bank_info(query, context, exam_type, None, None)


# ─────────────────────── Step 2a: stream ─────────────────────────────────────

async def sub_stream_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    stream    = query.data.replace("sub_stream_", "")
    exam_type = context.user_data.get("sub_exam_type", "entrance")
    context.user_data["sub_stream"] = stream
    context.user_data["sub_dept"]   = None

    # entrance / remedial: stream is enough → go straight to bank
    await _show_bank_info(query, context, exam_type, stream, None)


# ─────────────────────── Step 2b: dept ───────────────────────────────────────

async def sub_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    dept      = query.data.replace("sub_dept_", "")
    exam_type = context.user_data.get("sub_exam_type")
    context.user_data["sub_dept"]   = dept
    context.user_data["sub_stream"] = None  # exit/coc have no stream

    await _show_bank_info(query, context, exam_type, None, dept)


# ─────────────────────── Step 3: bank info ───────────────────────────────────

async def _show_bank_info(query, context, exam_type, stream, dept):
    telegram_id = query.from_user.id

    exam_label = (exam_type or "").capitalize()
    if stream: exam_label += f" / {stream.capitalize()}"
    if dept:   exam_label += f" / {dept.replace('_',' ').title()}"

    # Show renewal notice if already subscribed (but still allow payment)
    if await check_subscription(telegram_id, exam_type, stream, dept):
        renew_note = (
            f"ℹ️ ለ *{exam_label}* ንቁ የሆነ ምዝገባ አለዎት።\n\n"
            "አሁን ማደስ ይችላሉ — ተደራሽነትዎ በ30 ቀናት ይራዘማል።\n\n"
        )
    else:
        renew_note = ""

    accounts = await _get_bank_accounts()

    if not accounts:
        await query.edit_message_text(
            "⚠️ የባንክ መለያ ገና አልተዋቀረም።\n"
            "ለክፍያ ዝግጅት አስተዳዳሪውን ያነጋግሩ።",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 ተመለስ", callback_data="subscribe")]
            ]),
        )
        return

    lines = [renew_note + "💳 *የክፍያ መረጃ*\n"]
    for acc in accounts:
        name   = acc.get("bank_name", "ባንክ")
        number = acc.get("account_number") or acc.get("account_no", "")
        holder = acc.get("account_holder") or acc.get("account_name", "")
        lines.append(f"🏦 *{name}*\nየሂሳብ ቁጥር: `{number}`\nባለሂሳብ: {holder}\n")

    lines.append(f"📚 ፕላን: *{exam_label}*")
    lines.append("\nከፍያ ከፈሉ በኋላ *ከፍያለሁ* ቁልፍን ተጫኑ ደረሰኝ ያስገቡ።")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ከፍያለሁ — ደረሰኝ ላክ", callback_data=f"pay_{exam_type}")],
            [InlineKeyboardButton("❌ ሰርዝ", callback_data="cancel_sub")],
        ]),
    )


# ─────────────────────── Step 4: "I've Paid" ─────────────────────────────────

async def pay_bank_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    exam_type = query.data.replace("pay_", "")
    context.user_data["sub_exam_type"] = exam_type
    context.user_data["waiting_for"]   = "receipt_photo"

    await query.edit_message_text(
        "📸 *አሁን የክፍያ ደረሰኝ ፎቶ ይላኩ።*\n\n"
        "የሂደቱ ዝርዝር በግልጽ የሚታይ ፎቶ ያስገቡ።\n"
        "አስተዳዳሪው ይፈትሸዋል ብዙም ሳይቆይ ያረጋግጣል።",
        parse_mode="Markdown",
    )


async def send_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for"] = "receipt_photo"
    await query.edit_message_text(
        "📸 *የክፍያ ደረሰኝ ፎቶ ይላኩ።*",
        parse_mode="Markdown",
    )


# ─────────────────────── Step 5: receipt photo received ──────────────────────

async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("waiting_for") != "receipt_photo":
        return

    if not update.message or not update.message.photo:
        await update.message.reply_text(
            "⚠️ እባክዎ *ፎቶ* ይላኩ (ፋይል/ሰነድ አይደለም)። እንደገና ይሞክሩ።",
            parse_mode="Markdown",
        )
        return

    # Always use the highest-resolution version
    file_id     = update.message.photo[-1].file_id
    telegram_id = update.effective_user.id
    exam_type   = context.user_data.get("sub_exam_type", "unknown")
    stream      = context.user_data.get("sub_stream")
    dept        = context.user_data.get("sub_dept")

    # Save receipt
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payment_receipts "
            "(telegram_id, file_id, exam_type, stream, dept, status, submitted_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))",
            (telegram_id, file_id, exam_type, stream, dept),
        )
        payment_id = cur.lastrowid
        await db.commit()

    context.user_data["waiting_for"] = None

    # Confirm to user
    exam_label = (exam_type or "").capitalize()
    if stream: exam_label += f" / {stream.capitalize()}"
    if dept:   exam_label += f" / {dept.replace('_',' ').title()}"

    await update.message.reply_text(
        f"✅ *ደረሰኝ ተቀብሏል!*\n\n"
        f"📚 ፕላን: *{exam_label}*\n"
        f"🧾 ደረሰኝ ቁጥር: `{payment_id}`\n\n"
        f"ጥያቄዎ *በአስተዳዳሪ እየታየ ነው።*\n"
        f"ሲፈቀድ ወዲያው ማሳወቂያ ይደርስዎታል። ⏳",
        parse_mode="Markdown",
    )

    # Notify admin with photo + approve/reject buttons
    user          = update.effective_user
    username_part = f"@{user.username}" if user.username else "(username የለም)"
    full_name     = user.full_name or "(ስም የለም)"

    caption = (
        f"📥 *አዲስ የክፍያ ደረሰኝ*\n\n"
        f"👤 {full_name}  {username_part}\n"
        f"🆔 `{telegram_id}`\n"
        f"📚 ፕላን: *{exam_label}*\n"
        f"🧾 ደረሰኝ ቁጥር: `{payment_id}`"
    )

    kb = receipt_action_keyboard(payment_id, telegram_id, exam_type, stream or "", dept or "")

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb,
        )
    except Exception as e:
        logger.error("Failed to notify admin about receipt %s: %s", payment_id, e)
        # Try as text message fallback
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=caption + f"\n\n⚠️ Could not send photo (file_id may have expired).",
                parse_mode="Markdown",
                reply_markup=kb,
            )
        except Exception as e2:
            logger.error("Admin text fallback also failed: %s", e2)
