"""
app/handlers/subscription.py

Handles the full subscription flow:
  /subscribe → pick exam type → stream/dept (if needed) → bank info →
  "I've Paid" → send receipt photo → admin notified with approve/reject buttons.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import receipt_action_keyboard
from config import DATABASE_PATH, ADMIN_ID
import aiosqlite

logger = logging.getLogger(__name__)

EXAM_TYPES = ["entrance", "exit", "coc", "driving", "remedial", "mock"]

STREAMS = ["Natural", "Social"]

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def check_subscription(
    telegram_id: int,
    exam_type: str,
    stream: str | None = None,
    dept: str | None = None,
) -> bool:
    """Return True if the user has an active subscription for the given exam."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await db.execute_fetchone(
            """
            SELECT id FROM subscriptions
            WHERE telegram_id = ?
              AND exam_type    = ?
              AND (stream = ? OR stream IS NULL OR ? IS NULL)
              AND (dept   = ? OR dept   IS NULL OR ? IS NULL)
              AND is_active = 1
              AND expiry_at  > datetime('now')
            """,
            (telegram_id, exam_type, stream, stream, dept, dept),
        )
        return row is not None


async def _get_bank_accounts(db: aiosqlite.Connection) -> list[dict]:
    db.row_factory = aiosqlite.Row
    cursor = await db.execute(
        "SELECT bank_name, account_number, account_holder FROM bank_accounts WHERE is_active=1"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


def _exam_type_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(et.capitalize(), callback_data=f"sub_exam_{et}")]
        for et in EXAM_TYPES
    ]
    return InlineKeyboardMarkup(buttons)


def _stream_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(s, callback_data=f"sub_stream_{s.lower()}")]
        for s in STREAMS
    ]
    return InlineKeyboardMarkup(buttons)


def _dept_keyboard(stream: str) -> InlineKeyboardMarkup:
    natural_depts = ["Biology", "Chemistry", "Physics", "Math", "Agriculture"]
    social_depts  = ["History", "Geography", "Economics", "Civic", "Business"]
    depts = natural_depts if stream == "natural" else social_depts
    buttons = [
        [InlineKeyboardButton(d, callback_data=f"sub_dept_{d.lower()}")]
        for d in depts
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# /subscribe
# ---------------------------------------------------------------------------

async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: /subscribe command or 'subscribe' callback."""
    # Support both command and callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send = query.edit_message_text
    else:
        send = update.message.reply_text

    await send(
        "📚 *Choose an exam type to subscribe to:*",
        parse_mode="Markdown",
        reply_markup=_exam_type_keyboard(),
    )


# ---------------------------------------------------------------------------
# Step 1 — exam type selected
# ---------------------------------------------------------------------------

async def sub_exam_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    exam_type = query.data.replace("sub_exam_", "")
    context.user_data["sub_exam_type"] = exam_type
    context.user_data["sub_stream"] = None
    context.user_data["sub_dept"] = None

    if exam_type in ("entrance", "exit"):
        await query.edit_message_text(
            f"📖 You chose *{exam_type.capitalize()}* exam.\n\nSelect your stream:",
            parse_mode="Markdown",
            reply_markup=_stream_keyboard(),
        )
    else:
        # Skip stream/dept, go straight to bank info
        await _show_bank_info(query, context, exam_type, None, None)


# ---------------------------------------------------------------------------
# Step 2a — stream selected (entrance/exit only)
# ---------------------------------------------------------------------------

async def sub_stream_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    stream = query.data.replace("sub_stream_", "")
    context.user_data["sub_stream"] = stream

    exam_type = context.user_data.get("sub_exam_type", "entrance")
    await query.edit_message_text(
        f"🏫 Stream: *{stream.capitalize()}*\n\nNow select your department:",
        parse_mode="Markdown",
        reply_markup=_dept_keyboard(stream),
    )


# ---------------------------------------------------------------------------
# Step 2b — dept selected
# ---------------------------------------------------------------------------

async def sub_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    dept = query.data.replace("sub_dept_", "")
    context.user_data["sub_dept"] = dept

    exam_type = context.user_data.get("sub_exam_type")
    stream    = context.user_data.get("sub_stream")
    await _show_bank_info(query, context, exam_type, stream, dept)


# ---------------------------------------------------------------------------
# Step 3 — show bank accounts + "I've Paid" button
# ---------------------------------------------------------------------------

async def _show_bank_info(query, context, exam_type, stream, dept):
    telegram_id = query.from_user.id

    # Check existing active subscription
    if await check_subscription(telegram_id, exam_type, stream, dept):
        label = exam_type.capitalize()
        if stream:
            label += f" / {stream.capitalize()}"
        if dept:
            label += f" / {dept.capitalize()}"
        await query.edit_message_text(
            f"ℹ️ You already have an active subscription for *{label}*.\n\n"
            "You can renew it by paying again. Continue to see payment details.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Continue to payment", callback_data=f"pay_{exam_type}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sub")],
            ]),
        )
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        accounts = await _get_bank_accounts(db)

    if not accounts:
        await query.edit_message_text(
            "⚠️ No bank accounts configured. Please contact admin.",
        )
        return

    lines = ["💳 *Bank Payment Details*\n"]
    for acc in accounts:
        lines.append(
            f"🏦 *{acc['bank_name']}*\n"
            f"Account: `{acc['account_number']}`\n"
            f"Holder: {acc['account_holder']}\n"
        )
    lines.append("\nAfter transferring, tap the button below.")

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ I've Paid", callback_data=f"pay_{exam_type}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sub")],
    ])

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# Step 4 — "I've Paid" tapped → ask for receipt photo
# ---------------------------------------------------------------------------

async def pay_bank_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Store exam_type from button data as well (handles renew path)
    exam_type = query.data.replace("pay_", "")
    context.user_data["sub_exam_type"] = exam_type
    context.user_data["waiting_for"] = "receipt_photo"

    await query.edit_message_text(
        "📸 Please send a *photo* of your payment receipt.\n"
        "Make sure the transaction details are clearly visible.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 4 alt — "send_receipt" callback (from menu)
# ---------------------------------------------------------------------------

async def send_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for"] = "receipt_photo"

    await query.edit_message_text(
        "📸 Please send a *photo* of your payment receipt.",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Step 5 — receipt photo received
# ---------------------------------------------------------------------------

async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("waiting_for") != "receipt_photo":
        return  # Not waiting for a receipt right now

    if not update.message.photo:
        await update.message.reply_text("⚠️ Please send a *photo*, not a file or document.")
        return

    # Always use the highest-resolution photo (last item in the list)
    file_id    = update.message.photo[-1].file_id
    telegram_id = update.effective_user.id

    exam_type = context.user_data.get("sub_exam_type", "unknown")
    stream    = context.user_data.get("sub_stream")
    dept      = context.user_data.get("sub_dept")

    # Save receipt to DB
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO payment_receipts
                (telegram_id, file_id, exam_type, stream, dept, status, submitted_at)
            VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))
            """,
            (telegram_id, file_id, exam_type, stream, dept),
        )
        payment_id = cursor.lastrowid
        await db.commit()

    # Confirm to user
    context.user_data["waiting_for"] = None
    await update.message.reply_text(
        "✅ Receipt received! Your subscription request is *pending admin review*.\n"
        "You will be notified once approved.",
        parse_mode="Markdown",
    )

    # Notify admin
    user = update.effective_user
    username_part = f"@{user.username}" if user.username else "(no username)"
    full_name     = user.full_name or "(no name)"

    exam_label = exam_type.capitalize()
    if stream:
        exam_label += f" / {stream.capitalize()}"
    if dept:
        exam_label += f" / {dept.capitalize()}"

    caption = (
        f"📥 *New Payment Receipt*\n\n"
        f"👤 {full_name} {username_part}\n"
        f"🆔 `{telegram_id}`\n"
        f"📚 Exam: *{exam_label}*\n"
        f"🧾 Receipt ID: `{payment_id}`"
    )

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=receipt_action_keyboard(payment_id, telegram_id, exam_type, stream, dept),
        )
    except Exception as e:
        logger.error("Failed to notify admin about receipt %s: %s", payment_id, e)
