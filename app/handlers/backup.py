"""
app/handlers/backup.py
══════════════════════
Full database backup and restore system.

Backup format: JSON (auto-zipped when large) containing:
  meta, questions, subjects, departments,
  users, exam_sessions, payments,
  giveaway_codes, giveaway_uses,
  bank_accounts, free_subject_usage

Admin callbacks handled here (registered in main.py):
  admin_backup_menu       → backup/restore menu
  bkp_full                → generate full backup
  bkp_questions           → questions-only backup
  bkp_users               → users+progress backup
  bkp_restore_menu        → prompt admin to send file
  bkp_do_restore_merge    → run merge restore
  bkp_do_restore_replace  → run replace restore

File upload handled by backup_file_handler()
  called from admin_file_handler when waiting_for='backup_restore_file'
"""

import io
import json
import zipfile
import datetime

import aiosqlite
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import DATABASE_PATH
from app.utils.access import is_any_admin
from app.keyboards.admin_menu import admin_back_keyboard

BACKUP_VERSION = "2.1"


# ───────────────────────────── helpers ──────────────────────────────────────

async def _rows(db, table: str) -> list:
    db.row_factory = aiosqlite.Row
    cur = await db.execute(f"SELECT * FROM {table}")
    return [dict(r) for r in await cur.fetchall()]


async def _table_exists(db, table: str) -> bool:
    cur = await db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return bool(await cur.fetchone())


async def _count(db, table: str, where: str = "") -> int:
    sql = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
    return (await (await db.execute(sql)).fetchone())[0]


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _ts() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")


# ──────────────────────────── export ────────────────────────────────────────

async def build_full_backup() -> dict:
    tables = [
        "questions", "subjects", "departments",
        "users", "exam_sessions", "payments",
        "giveaway_codes", "giveaway_uses",
        "bank_accounts", "free_subject_usage",
    ]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        data = {}
        for t in tables:
            data[t] = await _rows(db, t) if await _table_exists(db, t) else []

    return {
        "meta": {
            "version": BACKUP_VERSION,
            "type": "full",
            "created_at": _now_iso(),
            "bot": "EthiopianExamBot",
            "total_questions": len(data["questions"]),
            "total_users": len(data["users"]),
            "total_sessions": len(data["exam_sessions"]),
        },
        **data,
    }


async def build_questions_backup() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        questions   = await _rows(db, "questions")
        subjects    = await _rows(db, "subjects")
        departments = await _rows(db, "departments")

    return {
        "meta": {
            "version": BACKUP_VERSION,
            "type": "questions_only",
            "created_at": _now_iso(),
            "bot": "EthiopianExamBot",
            "total_questions": len(questions),
        },
        "questions": questions,
        "subjects": subjects,
        "departments": departments,
        "users": [],
        "exam_sessions": [],
    }


async def build_users_backup() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        raw_users = await _rows(db, "users")
        sessions  = await _rows(db, "exam_sessions")
        usage     = await _rows(db, "free_subject_usage") if await _table_exists(db, "free_subject_usage") else []

    # Strip admin flags for portability
    users = [{k: v for k, v in u.items() if k != "is_admin"} for u in raw_users]

    return {
        "meta": {
            "version": BACKUP_VERSION,
            "type": "users_progress",
            "created_at": _now_iso(),
            "bot": "EthiopianExamBot",
            "total_users": len(users),
            "total_sessions": len(sessions),
        },
        "questions": [],
        "subjects": [],
        "departments": [],
        "users": users,
        "exam_sessions": sessions,
        "free_subject_usage": usage,
    }


def _to_bytes(payload: dict) -> tuple[bytes, str]:
    """Return (file_bytes, extension). Zips automatically when > 20 KB."""
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    if len(raw) <= 20_000:
        return raw, "json"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup.json", raw.decode("utf-8"))
    return buf.getvalue(), "zip"


# ──────────────────────────── import ────────────────────────────────────────

async def _restore_table_questions(db, rows, replace):
    if replace:
        await db.execute("DELETE FROM questions")
    n = 0
    for q in rows:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO questions "
                "(exam_type,stream,subject,year,question_text,"
                "option_a,option_b,option_c,option_d,"
                "correct_answer,explanation,reference) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (q.get("exam_type"), q.get("stream"), q.get("subject"),
                 q.get("year"), q.get("question_text"),
                 q.get("option_a"), q.get("option_b"),
                 q.get("option_c"), q.get("option_d"),
                 q.get("correct_answer"), q.get("explanation"),
                 q.get("reference")))
            n += 1
        except Exception:
            pass
    return n


async def _restore_table_subjects(db, rows, replace):
    if replace:
        await db.execute("DELETE FROM subjects")
    n = 0
    for s in rows:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO subjects "
                "(exam_type,stream,subject_key,subject_name,emoji) "
                "VALUES (?,?,?,?,?)",
                (s.get("exam_type"), s.get("stream"),
                 s.get("subject_key"), s.get("subject_name"),
                 s.get("emoji", "📘")))
            n += 1
        except Exception:
            pass
    return n


async def _restore_table_departments(db, rows, replace):
    if replace:
        await db.execute("DELETE FROM departments")
    n = 0
    for d in rows:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO departments "
                "(exam_type,dept_key,dept_name,emoji) VALUES (?,?,?,?)",
                (d.get("exam_type", "exit"), d.get("dept_key"),
                 d.get("dept_name"), d.get("emoji", "🏛️")))
            n += 1
        except Exception:
            pass
    return n


async def _restore_table_users(db, rows):
    """Always MERGE users — never clears the table."""
    n = 0
    for u in rows:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO users "
                "(telegram_id,username,full_name,exam_type,stream,department,"
                "referral_code,referred_by,referral_count,"
                "streak_days,last_exam_date,created_at,last_active) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (u.get("telegram_id"), u.get("username"), u.get("full_name"),
                 u.get("exam_type"), u.get("stream"), u.get("department"),
                 u.get("referral_code"), u.get("referred_by"),
                 u.get("referral_count", 0), u.get("streak_days", 0),
                 u.get("last_exam_date"), u.get("created_at"),
                 u.get("last_active")))
            n += 1
        except Exception:
            pass
    return n


async def _restore_table_sessions(db, rows, replace):
    if replace:
        await db.execute("DELETE FROM exam_sessions")
    n = 0
    for s in rows:
        try:
            await db.execute(
                "INSERT OR IGNORE INTO exam_sessions "
                "(telegram_id,exam_type,stream,subject,year,"
                "score,total,completed,started_at,finished_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (s.get("telegram_id"), s.get("exam_type"), s.get("stream"),
                 s.get("subject"), s.get("year"),
                 s.get("score", 0), s.get("total", 0), s.get("completed", 0),
                 s.get("started_at"), s.get("finished_at")))
            n += 1
        except Exception:
            pass
    return n


async def restore_from_payload(payload: dict, mode: str = "merge") -> dict:
    """
    Restore database from backup dict.
    mode='merge'   → INSERT OR IGNORE (keeps existing data)
    mode='replace' → clears questions/sessions first, then inserts
    Users are ALWAYS merged regardless of mode.
    Returns count summary dict.
    """
    replace = (mode == "replace")
    summary = {}
    async with aiosqlite.connect(DATABASE_PATH) as db:
        summary["questions"]    = await _restore_table_questions(db, payload.get("questions", []), replace)
        summary["subjects"]     = await _restore_table_subjects(db, payload.get("subjects", []), replace)
        summary["departments"]  = await _restore_table_departments(db, payload.get("departments", []), replace)
        summary["users"]        = await _restore_table_users(db, payload.get("users", []))
        summary["exam_sessions"] = await _restore_table_sessions(db, payload.get("exam_sessions", []), replace)
        await db.commit()
    return summary


# ──────────────────────────── telegram handlers ──────────────────────────────

async def backup_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show backup/restore menu. Triggered by admin_backup_menu callback."""
    query = update.callback_query
    await query.answer()
    if not await is_any_admin(query.from_user.id):
        await query.edit_message_text("⛔ Unauthorized.")
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        q = await _count(db, "questions")
        u = await _count(db, "users")
        s = await _count(db, "exam_sessions", "completed=1")

    await query.edit_message_text(
        "💾 *Backup & Restore*\n\n"
        f"📊 *Current database:*\n"
        f"  ❓ Questions: *{q:,}*\n"
        f"  👥 Users: *{u:,}*\n"
        f"  📊 Completed exams: *{s:,}*\n\n"
        "Choose an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Full Backup (all data)",     callback_data="bkp_full")],
            [InlineKeyboardButton("❓ Questions + Subjects only",  callback_data="bkp_questions")],
            [InlineKeyboardButton("👥 Users & Progress only",      callback_data="bkp_users")],
            [InlineKeyboardButton("📥 Restore from Backup File",   callback_data="bkp_restore_menu")],
            [InlineKeyboardButton("🔙 Back to Admin",              callback_data="admin_back")],
        ]))


async def backup_trigger_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send the backup file. callback: bkp_full | bkp_questions | bkp_users"""
    query = update.callback_query
    await query.answer()
    if not await is_any_admin(query.from_user.id):
        return

    btype = query.data
    await query.edit_message_text("⏳ Generating backup…")

    try:
        if btype == "bkp_full":
            payload = await build_full_backup()
            label = "full"
        elif btype == "bkp_questions":
            payload = await build_questions_backup()
            label = "questions"
        else:
            payload = await build_users_backup()
            label = "users_progress"

        raw, ext = _to_bytes(payload)
        fname = f"ethioexam_{label}_{_ts()}.{ext}"
        meta  = payload["meta"]

        caption = (
            f"💾 *{label.replace('_',' ').title()} Backup*\n\n"
            f"📅 Date: `{meta['created_at'][:10]}`\n"
            f"❓ Questions: *{meta.get('total_questions','—')}*\n"
            f"👥 Users: *{meta.get('total_users','—')}*\n"
            f"📦 Format: `{ext.upper()}`\n\n"
            "_Keep this file safe. Send it back here to restore._"
        )

        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=InputFile(io.BytesIO(raw), filename=fname),
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
        )
        await query.edit_message_text(
            "✅ *Backup sent above!*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Backup Menu", callback_data="admin_backup_menu")],
                [InlineKeyboardButton("🔙 Admin",       callback_data="admin_back")],
            ]))
    except Exception as e:
        await query.edit_message_text(
            f"❌ Backup failed:\n`{str(e)[:300]}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_back_keyboard())


async def backup_restore_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to upload a backup file."""
    query = update.callback_query
    await query.answer()
    if not await is_any_admin(query.from_user.id):
        return
    context.user_data["waiting_for"] = "backup_restore_file"
    await query.edit_message_text(
        "📥 *Restore from Backup*\n\n"
        "Send the `.json` or `.zip` backup file now.\n\n"
        "⚠️ *Two restore modes:*\n"
        "• *Merge* — adds new records, keeps existing ones (safe)\n"
        "• *Replace* — wipes questions & sessions first (clean import)\n\n"
        "📌 Users are always merged — accounts are never deleted.\n\n"
        "Type /cancel to abort.",
        parse_mode=ParseMode.MARKDOWN)


async def backup_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receives the .json or .zip backup file from the admin.
    Called from admin_file_handler when waiting_for == 'backup_restore_file'.
    """
    if not await is_any_admin(update.effective_user.id):
        return
    doc = update.message.document
    if not doc:
        await update.message.reply_text("⚠️ Please send a file (.json or .zip).")
        return
    fname = (doc.file_name or "").lower()
    if not fname.endswith(".json") and not fname.endswith(".zip"):
        await update.message.reply_text("⚠️ Only .json or .zip backup files are accepted.")
        return

    await update.message.reply_text("⏳ Reading backup file…")
    try:
        tg_file = await doc.get_file()
        raw = bytes(await tg_file.download_as_bytearray())

        if fname.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                payload = json.loads(zf.read(zf.namelist()[0]).decode("utf-8"))
        else:
            payload = json.loads(raw.decode("utf-8"))

        meta = payload.get("meta", {})
        q  = len(payload.get("questions", []))
        u  = len(payload.get("users", []))
        s  = len(payload.get("exam_sessions", []))
        sb = len(payload.get("subjects", []))
        dp = len(payload.get("departments", []))

        context.user_data["restore_payload"] = payload
        context.user_data["waiting_for"] = None

        await update.message.reply_text(
            "📋 *Backup File Summary*\n\n"
            f"🔖 Version: `{meta.get('version','?')}`\n"
            f"📅 Created: `{meta.get('created_at','?')[:19]}`\n"
            f"📦 Type: `{meta.get('type','full')}`\n\n"
            f"  ❓ Questions: *{q:,}*\n"
            f"  📚 Subjects: *{sb}*\n"
            f"  🏛️ Departments: *{dp}*\n"
            f"  👥 Users: *{u:,}*\n"
            f"  📊 Exam Sessions: *{s:,}*\n\n"
            "Choose restore mode:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔀 Merge  (safe — keep existing)",
                                      callback_data="bkp_do_restore_merge")],
                [InlineKeyboardButton("♻️ Replace (clears questions & sessions first)",
                                      callback_data="bkp_do_restore_replace")],
                [InlineKeyboardButton("❌ Cancel", callback_data="admin_back")],
            ]))
    except json.JSONDecodeError:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Invalid file — could not parse JSON.\n"
            "Make sure you are sending a valid EthioExam backup file.",
            reply_markup=admin_back_keyboard())
    except Exception as e:
        context.user_data.clear()
        await update.message.reply_text(
            f"❌ Error reading file:\n`{str(e)[:300]}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_back_keyboard())


async def backup_do_restore_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the restore after admin picks merge or replace."""
    query = update.callback_query
    await query.answer()
    if not await is_any_admin(query.from_user.id):
        return

    mode    = "merge" if query.data == "bkp_do_restore_merge" else "replace"
    payload = context.user_data.pop("restore_payload", None)
    if not payload:
        await query.edit_message_text(
            "⚠️ No backup data found. Please upload the file again.",
            reply_markup=admin_back_keyboard())
        return

    await query.edit_message_text(f"⏳ Restoring database ({mode} mode)…")
    try:
        summary = await restore_from_payload(payload, mode=mode)
        lines = "\n".join(
            f"  • {k.replace('_',' ').title()}: *{v}* imported"
            for k, v in summary.items())
        await query.edit_message_text(
            f"✅ *Restore Complete!*\n\nMode: `{mode}`\n\n{lines}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💾 Backup Menu", callback_data="admin_backup_menu")],
                [InlineKeyboardButton("🔙 Admin",       callback_data="admin_back")],
            ]))
    except Exception as e:
        await query.edit_message_text(
            f"❌ Restore failed:\n`{str(e)[:300]}`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_back_keyboard())

