"""
app/handlers/user_features.py
Handles /redeem and /referral commands.
"""
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import aiosqlite
from config import DATABASE_PATH
from app.utils.logger import logger


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/redeem <CODE>"""
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "🎟️ Usage: `/redeem YOUR_CODE`\n\nEnter your giveaway code after /redeem",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    code = args[0].strip().upper()
    tid = update.effective_user.id

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check code exists and is valid
        cur = await db.execute(
            "SELECT id, duration_days, max_uses, used_count FROM giveaway_codes WHERE code=?",
            (code,)
        )
        gc = await cur.fetchone()
        if not gc:
            await update.message.reply_text("❌ Invalid code. Please check and try again.")
            return

        gc_id, duration_days, max_uses, used_count = gc

        if used_count >= max_uses:
            await update.message.reply_text("❌ This code has already been fully redeemed.")
            return

        # Check if user already used this code
        cur2 = await db.execute(
            "SELECT id FROM giveaway_uses WHERE code=? AND telegram_id=?", (code, tid)
        )
        if await cur2.fetchone():
            await update.message.reply_text("⚠️ You've already used this code.")
            return

        # Apply free access
        expiry = (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        await db.execute(
            """UPDATE users SET
               free_access_expiry=CASE
                   WHEN free_access_expiry IS NULL OR free_access_expiry < datetime('now')
                   THEN ?
                   ELSE datetime(free_access_expiry, ?||' days')
               END
               WHERE telegram_id=?""",
            (expiry, str(duration_days), tid)
        )

        # Record usage
        await db.execute(
            "INSERT INTO giveaway_uses (code, telegram_id) VALUES (?,?)", (code, tid)
        )
        await db.execute(
            "UPDATE giveaway_codes SET used_count=used_count+1 WHERE id=?", (gc_id,)
        )
        await db.commit()

    await update.message.reply_text(
        f"🎉 *Code Redeemed Successfully!*\n\n"
        f"✅ You now have *{duration_days} days* of free access!\n\n"
        f"📅 Valid until: `{expiry[:10]}`",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Start Exam", callback_data="main_menu")]
        ])
    )


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/referral — Show user's referral link and stats."""
    tid = update.effective_user.id

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT referral_code, referral_count FROM users WHERE telegram_id=?", (tid,)
        )
        row = await cur.fetchone()

    if not row:
        await update.message.reply_text("Please /start the bot first.")
        return

    ref_code, ref_count = row
    # Use your actual bot username here
    link = f"https://t.me/EthioExamBot?start={ref_code}"

    await update.message.reply_text(
        f"👥 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"📊 Friends referred: *{ref_count}*\n\n"
        f"🎁 Each friend who joins gives you both *+3 free days*!\n\n"
        f"Share the link and help your friends prepare for their exams! 🇪🇹",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ])
    )