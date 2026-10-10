"""
app/handlers/subscription.py
Handles subscription selection, bank payment instructions,
and receipt photo submission.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import aiosqlite
from config import DATABASE_PATH, SUBSCRIPTION_PRICE_ETB, SUBSCRIPTION_DAYS
from app.utils.logger import logger


async def _get_banks():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bank_accounts WHERE is_active=1")
        return [dict(r) for r in await cur.fetchall()]


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point: show exam type selection. Callback: subscribe"""
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton("🎓 Entrance Exam", callback_data="sub_exam_entrance")],
        [InlineKeyboardButton("📋 Exit Exam",     callback_data="sub_exam_exit")],
        [InlineKeyboardButton("📚 Remedial Exam", callback_data="sub_exam_remedial")],
        [InlineKeyboardButton("🚗 Driving License", callback_data="sub_exam_driving")],
        [InlineKeyboardButton("🏅 COC Exam",      callback_data="sub_exam_coc")],
        [InlineKeyboardButton("⬅️ Back",          callback_data="main_menu")],
    ]
    await query.edit_message_text(
        f"💎 *Subscribe — {SUBSCRIPTION_PRICE_ETB} ETB / {SUBSCRIPTION_DAYS} days*\n\n"
        "Choose the exam you're preparing for:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def sub_exam_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: sub_exam_<exam_type>"""
    query = update.callback_query
    await query.answer()

    exam_type = query.data.replace("sub_exam_", "")
    context.user_data["sub_exam_type"] = exam_type

    if exam_type in ("entrance", "remedial"):
        buttons = [
            [InlineKeyboardButton("🔬 Natural Science", callback_data="sub_stream_natural")],
            [InlineKeyboardButton("📚 Social Science",  callback_data="sub_stream_social")],
            [InlineKeyboardButton("⬅️ Back",            callback_data="subscribe")],
        ]
        await query.edit_message_text(
            f"📚 *{exam_type.title()} Exam*\n\nChoose your stream:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif exam_type in ("exit", "coc"):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM departments WHERE exam_type=?", (exam_type,))
            depts = [dict(r) for r in await cur.fetchall()]

        buttons = [
            [InlineKeyboardButton(
                f"{d['emoji']} {d['dept_name']}",
                callback_data=f"sub_dept_{d['dept_key']}"
            )]
            for d in depts
        ]
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="subscribe")])

        label = "Department" if exam_type == "exit" else "Field"
        await query.edit_message_text(
            f"📋 *{exam_type.title()} Exam*\n\nChoose your {label}:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    else:
        # driving / other — no stream needed
        context.user_data["sub_stream"] = "general"
        context.user_data["sub_dept"] = "general"
        await _show_banks(query, context)


async def sub_stream_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: sub_stream_<stream>"""
    query = update.callback_query
    await query.answer()

    stream = query.data.replace("sub_stream_", "")
    context.user_data["sub_stream"] = stream
    context.user_data["sub_dept"] = ""
    await _show_banks(query, context)


async def sub_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: sub_dept_<dept_key>"""
    query = update.callback_query
    await query.answer()

    dept = query.data.replace("sub_dept_", "")
    context.user_data["sub_dept"] = dept
    context.user_data["sub_stream"] = dept  # store in both for compatibility
    await _show_banks(query, context)


async def _show_banks(query, context: ContextTypes.DEFAULT_TYPE):
    banks = await _get_banks()

    exam_type = context.user_data.get("sub_exam_type", "")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")

    if not banks:
        await query.edit_message_text(
            "⚠️ No payment banks configured yet. Contact admin.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="subscribe")]
            ])
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"🏦 Pay via {b['bank_name']}",
            callback_data=f"pay_{b['bank_name']}"
        )]
        for b in banks
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="subscribe")])

    await query.edit_message_text(
        f"💳 *Payment — {SUBSCRIPTION_PRICE_ETB} ETB*\n\n"
        f"📚 Exam: *{exam_type.title()}*\n"
        f"🔀 Stream/Dept: *{stream or dept or 'General'}*\n\n"
        "Choose your bank to see payment details:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def pay_bank_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: pay_<BankName>"""
    query = update.callback_query
    await query.answer()

    bank_name = query.data.replace("pay_", "")
    context.user_data["pay_bank"] = bank_name

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT account_number, account_name FROM bank_accounts WHERE bank_name=? AND is_active=1",
            (bank_name,)
        )
        row = await cur.fetchone()

    if not row:
        await query.edit_message_text(
            "⚠️ Bank not found. Please choose another.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="subscribe")]
            ])
        )
        return

    acct_no, acct_name = row
    exam_type = context.user_data.get("sub_exam_type", "")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")

    await query.edit_message_text(
        f"🏦 *{bank_name} Payment Instructions*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 Amount: *{SUBSCRIPTION_PRICE_ETB} ETB*\n"
        f"🏦 Bank: *{bank_name}*\n"
        f"📋 Account No: `{acct_no}`\n"
        f"👤 Account Name: *{acct_name}*\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📚 Exam: *{exam_type.title()}*\n"
        f"🔀 Stream/Dept: *{stream or dept or 'General'}*\n\n"
        "✅ After payment, tap below to send your receipt photo.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📸 Send Receipt Photo", callback_data="send_receipt")],
            [InlineKeyboardButton("⬅️ Back", callback_data="subscribe")],
        ])
    )


async def send_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to send receipt. Callback: send_receipt"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📸 *Send Your Receipt*\n\n"
        "Please send a *photo* of your bank transfer receipt now.\n\n"
        "🕐 Admin will review and approve within 24 hours.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="main_menu")]
        ])
    )
    context.user_data["awaiting_receipt"] = True


async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles photo submitted as receipt."""
    if not context.user_data.get("awaiting_receipt"):
        return  # Not awaiting receipt

    context.user_data["awaiting_receipt"] = False

    tid = update.effective_user.id
    full_name = update.effective_user.full_name or ""

    exam_type = context.user_data.get("sub_exam_type", "")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")
    bank = context.user_data.get("pay_bank", "")

    photo = update.message.photo[-1]  # Largest size
    file_id = photo.file_id

    # Save to payments table
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO payments
               (telegram_id, full_name, amount, bank, receipt_file_id, status, exam_type, stream, dept)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (tid, full_name, SUBSCRIPTION_PRICE_ETB, bank, file_id, "pending", exam_type, stream, dept)
        )
        await db.commit()

    await update.message.reply_text(
        "✅ *Receipt Received!*\n\n"
        f"📚 Exam: *{exam_type.title()}*\n"
        f"🔀 Stream/Dept: *{stream or dept or 'General'}*\n"
        f"🏦 Bank: *{bank}*\n\n"
        "🕐 Admin will review your payment within 24 hours.\n"
        "You'll receive a notification once approved! 🎉",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
    )

    # Notify admin
    try:
        from config import ADMIN_ID as ADMIN_TID
        await context.bot.send_photo(
            chat_id=ADMIN_TID,
            photo=file_id,
            caption=(
                f"🔔 *New Payment Receipt*\n\n"
                f"👤 User: {full_name} (`{tid}`)\n"
                f"📚 Exam: {exam_type.title()}\n"
                f"🔀 Stream: {stream or dept or 'General'}\n"
                f"🏦 Bank: {bank}\n"
                f"💰 Amount: {SUBSCRIPTION_PRICE_ETB} ETB"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"Could not notify admin: {e}")