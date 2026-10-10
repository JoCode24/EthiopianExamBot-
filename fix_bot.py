import os

def w(path, content):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"OK: {path}")


# ── app/database/db.py ────────────────────────────────────
w("app/database/db.py", '''import aiosqlite
import os
from config import DATABASE_PATH
from app.utils.logger import logger


async def init_db():
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                exam_type TEXT,
                stream TEXT,
                department TEXT,
                is_subscribed INTEGER DEFAULT 0,
                subscription_expiry TEXT,
                free_access_expiry TEXT,
                is_admin INTEGER DEFAULT 0,
                referral_code TEXT UNIQUE,
                referred_by TEXT,
                referral_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime(\'now\')),
                last_active TEXT DEFAULT (datetime(\'now\'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                exam_type TEXT,
                stream TEXT,
                subject TEXT,
                year INTEGER,
                score INTEGER DEFAULT 0,
                total INTEGER DEFAULT 0,
                completed INTEGER DEFAULT 0,
                started_at TEXT DEFAULT (datetime(\'now\')),
                finished_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL,
                stream TEXT,
                subject TEXT NOT NULL,
                year INTEGER,
                question_text TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT NOT NULL,
                option_d TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                reference TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                method TEXT,
                status TEXT DEFAULT \'pending\',
                transaction_ref TEXT,
                created_at TEXT DEFAULT (datetime(\'now\'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL,
                stream TEXT,
                subject_key TEXT NOT NULL UNIQUE,
                subject_name TEXT NOT NULL,
                emoji TEXT DEFAULT \'📘\'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dept_key TEXT NOT NULL UNIQUE,
                dept_name TEXT NOT NULL,
                emoji TEXT DEFAULT \'🏛\'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                duration_days INTEGER NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                created_by INTEGER,
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime(\'now\'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                telegram_id INTEGER NOT NULL,
                used_at TEXT DEFAULT (datetime(\'now\'))
            )
        """)

        await db.commit()
        await seed_default_subjects(db)
        logger.info("Database initialized.")


async def seed_default_subjects(db):
    cursor = await db.execute("SELECT COUNT(*) FROM subjects")
    if (await cursor.fetchone())[0] > 0:
        return
    await db.executemany(
        "INSERT OR IGNORE INTO subjects (exam_type,stream,subject_key,subject_name,emoji) VALUES (?,?,?,?,?)",
        [
            ("entrance","natural","math","Mathematics","🧮"),
            ("entrance","natural","chemistry","Chemistry","⚗️"),
            ("entrance","natural","biology","Biology","🔬"),
            ("entrance","natural","physics","Physics","⚡"),
            ("entrance","natural","english","English","🌍"),
            ("entrance","social","english","English","🌍"),
            ("entrance","social","history","History","📜"),
            ("entrance","social","geography","Geography","🗺️"),
            ("entrance","social","civics","Civics","⚖️"),
            ("entrance","social","economics","Economics","💰"),
        ]
    )
    await db.executemany(
        "INSERT OR IGNORE INTO departments (dept_key,dept_name,emoji) VALUES (?,?,?)",
        [
            ("computer_science","Computer Science","💻"),
            ("accounting","Accounting and Finance","📊"),
            ("law","Law","⚖️"),
            ("medicine","Medicine","🏥"),
            ("engineering","Engineering","⚙️"),
            ("business","Business Management","💼"),
            ("agriculture","Agriculture","🌾"),
            ("education","Education","📖"),
        ]
    )
    await db.commit()


def get_db():
    os.makedirs("data", exist_ok=True)
    return aiosqlite.connect(DATABASE_PATH)
''')


# ── app/keyboards/admin_menu.py ───────────────────────────
w("app/keyboards/admin_menu.py", '''from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Question (Manual)", callback_data="admin_add_question")],
        [InlineKeyboardButton("📄 Upload Question File", callback_data="admin_upload_file")],
        [InlineKeyboardButton("✏️ Edit Question", callback_data="admin_edit_question")],
        [InlineKeyboardButton("🗑️ Delete Question", callback_data="admin_delete_question")],
        [InlineKeyboardButton("📚 Manage Subjects", callback_data="admin_manage_subjects")],
        [InlineKeyboardButton("🏛 Manage Departments", callback_data="admin_manage_depts")],
        [InlineKeyboardButton("👥 View Users", callback_data="admin_view_users")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("❓ View Questions", callback_data="admin_view_questions")],
        [InlineKeyboardButton("💳 Grant Subscription", callback_data="admin_grant_sub")],
        [InlineKeyboardButton("🎁 Giveaway Free Access", callback_data="admin_giveaway")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Close Panel", callback_data="admin_close")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_exam_type_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎓 Entrance Exam", callback_data="aq_type_entrance")],
        [InlineKeyboardButton("🏛 Exit Exam", callback_data="aq_type_exit")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_stream_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔬 Natural Science", callback_data="aq_stream_natural")],
        [InlineKeyboardButton("📚 Social Science", callback_data="aq_stream_social")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_subject_keyboard(subjects, prefix="aq_subject_"):
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(
            f"{s[\'emoji\']} {s[\'subject_name\']}",
            callback_data=f"{prefix}{s[\'subject_key\']}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def build_dept_keyboard(depts, prefix="aq_subject_"):
    keyboard = []
    for d in depts:
        keyboard.append([InlineKeyboardButton(
            f"{d[\'emoji\']} {d[\'dept_name\']}",
            callback_data=f"{prefix}{d[\'dept_key\']}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def admin_confirm_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="aq_confirm_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel_question")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]]
    return InlineKeyboardMarkup(keyboard)


def admin_cancel_keyboard():
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel_question")]]
    return InlineKeyboardMarkup(keyboard)


def manage_subjects_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Subject", callback_data="admin_add_subject")],
        [InlineKeyboardButton("✏️ Edit Subject", callback_data="admin_edit_subject")],
        [InlineKeyboardButton("🗑️ Delete Subject", callback_data="admin_delete_subject")],
        [InlineKeyboardButton("📋 View All Subjects", callback_data="admin_list_subjects")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def manage_depts_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add Department", callback_data="admin_add_dept")],
        [InlineKeyboardButton("✏️ Edit Department", callback_data="admin_edit_dept")],
        [InlineKeyboardButton("🗑️ Delete Department", callback_data="admin_delete_dept")],
        [InlineKeyboardButton("📋 View All Departments", callback_data="admin_list_depts")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def giveaway_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎁 Create Giveaway Code", callback_data="admin_create_giveaway")],
        [InlineKeyboardButton("📋 View Active Codes", callback_data="admin_list_giveaways")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)
''')


# ── app/handlers/admin.py ─────────────────────────────────
w("app/handlers/admin.py", '''from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import (
    admin_main_keyboard, admin_exam_type_keyboard, admin_stream_keyboard,
    admin_confirm_keyboard, admin_back_keyboard, admin_cancel_keyboard,
    build_subject_keyboard, build_dept_keyboard,
    manage_subjects_keyboard, manage_depts_keyboard,
    giveaway_keyboard,
)
from app.utils.logger import logger
from app.utils.question_parser import parse_questions_from_text
from config import ADMIN_ID, DATABASE_PATH
import aiosqlite
import random
import string


def is_admin(uid):
    return uid == ADMIN_ID


def gen_code(length=8):
    return \'\'.join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def get_subjects(exam_type, stream):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects WHERE exam_type=? AND stream=? ORDER BY subject_name",
            (exam_type, stream))
        return [dict(r) for r in await cur.fetchall()]


async def get_depts():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM departments ORDER BY dept_name")
        return [dict(r) for r in await cur.fetchall()]


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text(
        "🔧 *Admin Panel*\n\nChoose an action:",
        parse_mode="Markdown",
        reply_markup=admin_main_keyboard())


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not is_admin(query.from_user.id):
        await query.edit_message_text("Unauthorized.")
        return

    if data == "admin_back":
        await query.edit_message_text(
            "🔧 *Admin Panel*\n\nChoose an action:",
            parse_mode="Markdown", reply_markup=admin_main_keyboard())

    elif data == "admin_close":
        await query.edit_message_text("Admin panel closed.")

    elif data == "admin_view_users":
        await show_users(query)

    elif data == "admin_stats":
        await show_stats(query)

    elif data == "admin_view_questions":
        await show_questions(query)

    elif data == "admin_manage_subjects":
        await query.edit_message_text(
            "📚 *Manage Subjects*",
            parse_mode="Markdown", reply_markup=manage_subjects_keyboard())

    elif data == "admin_manage_depts":
        await query.edit_message_text(
            "🏛 *Manage Departments*",
            parse_mode="Markdown", reply_markup=manage_depts_keyboard())

    elif data == "admin_list_subjects":
        await list_subjects(query)

    elif data == "admin_list_depts":
        await list_depts(query)

    elif data == "admin_add_subject":
        context.user_data["waiting_for"] = "new_subject_info"
        await query.edit_message_text(
            "📚 *Add Subject*\n\n"
            "Send in this exact format:\n"
            "exam_type|stream|key|name|emoji\n\n"
            "Examples:\n"
            "entrance|natural|physics|Physics|⚡\n"
            "entrance|social|history|History|📜\n"
            "exit|exit|nursing|Nursing|🩺\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_edit_subject":
        context.user_data["waiting_for"] = "edit_subject_info"
        await query.edit_message_text(
            "✏️ *Edit Subject*\n\n"
            "Send in this format:\n"
            "old_key|new_name|new_emoji\n\n"
            "Example:\n"
            "physics|Physics Advanced|⚡\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_delete_subject":
        context.user_data["waiting_for"] = "delete_subject_key"
        await query.edit_message_text(
            "🗑️ *Delete Subject*\n\n"
            "Send the subject key to delete.\n"
            "Example: physics\n\n"
            "First view subjects to find the key.\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_add_dept":
        context.user_data["waiting_for"] = "new_dept_info"
        await query.edit_message_text(
            "🏛 *Add Department*\n\n"
            "Send in this format:\n"
            "key|name|emoji\n\n"
            "Example: nursing|Nursing|🩺\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_edit_dept":
        context.user_data["waiting_for"] = "edit_dept_info"
        await query.edit_message_text(
            "✏️ *Edit Department*\n\n"
            "Send in this format:\n"
            "old_key|new_name|new_emoji\n\n"
            "Example: law|Ethiopian Law|⚖️\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_delete_dept":
        context.user_data["waiting_for"] = "delete_dept_key"
        await query.edit_message_text(
            "🗑️ *Delete Department*\n\n"
            "Send the department key to delete.\n"
            "Example: law\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_add_question":
        context.user_data.clear()
        await query.edit_message_text(
            "➕ *Add Question*\n\nStep 1: Choose exam type:",
            parse_mode="Markdown", reply_markup=admin_exam_type_keyboard())

    elif data == "admin_edit_question":
        context.user_data["waiting_for"] = "edit_question_id"
        await query.edit_message_text(
            "✏️ *Edit Question*\n\n"
            "First use View Questions to find the question ID.\n"
            "Then send the question ID number.\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_delete_question":
        context.user_data["waiting_for"] = "delete_question_id"
        await query.edit_message_text(
            "🗑️ *Delete Question*\n\n"
            "Send the question ID to delete.\n"
            "Use View Questions to find the ID.\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_upload_file":
        context.user_data["waiting_for"] = "question_file"
        await query.edit_message_text(
            "📄 *Upload Question File*\n\n"
            "Send a .txt file using this format:\n\n"
            "Q: Question text\n"
            "A) Option A\n"
            "B) Option B\n"
            "C) Option C\n"
            "D) Option D\n"
            "Answer: B\n"
            "Explanation: reason\n"
            "Reference: Grade 12 Book Ch.1\n"
            "Year: 2023\n\n"
            "Separate each question with a blank line.",
            parse_mode="Markdown")

    elif data == "admin_grant_sub":
        context.user_data["waiting_for"] = "grant_sub_id"
        await query.edit_message_text(
            "💳 *Grant Subscription*\n\n"
            "Send: telegram_id|days\n"
            "Example: 123456789|30\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_giveaway":
        await query.edit_message_text(
            "🎁 *Giveaway Free Access*",
            parse_mode="Markdown", reply_markup=giveaway_keyboard())

    elif data == "admin_create_giveaway":
        context.user_data["waiting_for"] = "giveaway_info"
        await query.edit_message_text(
            "🎁 *Create Giveaway Code*\n\n"
            "Send in this format:\n"
            "days|max_uses\n\n"
            "Examples:\n"
            "7|100   (7 days, 100 students)\n"
            "30|1    (30 days, 1 student)\n"
            "3|500   (3 days, 500 students)\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_list_giveaways":
        await list_giveaways(query)

    elif data == "admin_broadcast":
        context.user_data["waiting_for"] = "broadcast_msg"
        await query.edit_message_text(
            "📢 *Broadcast*\n\nType message for ALL users.\nType /cancel to abort.",
            parse_mode="Markdown")

    elif data == "admin_cancel_question":
        context.user_data.clear()
        await query.edit_message_text("Cancelled.", reply_markup=admin_main_keyboard())

    elif data.startswith("aq_subject_"):
        subject = data.replace("aq_subject_", "")
        context.user_data["aq_subject"] = subject
        context.user_data["aq_subject_label"] = subject.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            f"Subject: {context.user_data[\'aq_subject_label\']}\n\n"
            "Now type the question text:\n"
            "Type /cancel to abort.")

    elif data == "edit_q_field_question":
        context.user_data["edit_field"] = "question_text"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new question text:")

    elif data == "edit_q_field_a":
        context.user_data["edit_field"] = "option_a"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new Option A:")

    elif data == "edit_q_field_b":
        context.user_data["edit_field"] = "option_b"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new Option B:")

    elif data == "edit_q_field_c":
        context.user_data["edit_field"] = "option_c"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new Option C:")

    elif data == "edit_q_field_d":
        context.user_data["edit_field"] = "option_d"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new Option D:")

    elif data == "edit_q_field_answer":
        context.user_data["edit_field"] = "correct_answer"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send new correct answer: A, B, C, or D")

    elif data == "edit_q_field_explanation":
        context.user_data["edit_field"] = "explanation"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new explanation:")

    elif data == "edit_q_field_reference":
        context.user_data["edit_field"] = "reference"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new reference:")

    elif data == "edit_q_field_year":
        context.user_data["edit_field"] = "year"
        context.user_data["waiting_for"] = "edit_q_value"
        await query.edit_message_text("Send the new year (number) or none:")


async def admin_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not is_admin(query.from_user.id):
        return

    has_upload = bool(context.user_data.get("parsed_questions"))

    if data == "aq_type_entrance":
        if has_upload:
            context.user_data["upload_exam_type"] = "entrance"
        else:
            context.user_data["aq_exam_type"] = "entrance"
        await query.edit_message_text("Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_type_exit":
        depts = await get_depts()
        if has_upload:
            context.user_data["upload_exam_type"] = "exit"
            context.user_data["upload_stream"] = "exit"
            await query.edit_message_text(
                "Choose department:",
                reply_markup=build_dept_keyboard(depts, prefix="upload_subject_"))
        else:
            context.user_data["aq_exam_type"] = "exit"
            context.user_data["aq_stream"] = "exit"
            await query.edit_message_text(
                "Choose department:",
                reply_markup=build_dept_keyboard(depts))

    elif data == "aq_stream_natural":
        subjects = await get_subjects("entrance", "natural")
        if has_upload:
            context.user_data["upload_stream"] = "natural"
            await query.edit_message_text(
                "Choose subject:",
                reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            context.user_data["aq_stream"] = "natural"
            await query.edit_message_text(
                "Choose subject:",
                reply_markup=build_subject_keyboard(subjects))

    elif data == "aq_stream_social":
        subjects = await get_subjects("entrance", "social")
        if has_upload:
            context.user_data["upload_stream"] = "social"
            await query.edit_message_text(
                "Choose subject:",
                reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            context.user_data["aq_stream"] = "social"
            await query.edit_message_text(
                "Choose subject:",
                reply_markup=build_subject_keyboard(subjects))

    elif data.startswith("upload_subject_"):
        subject = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream = context.user_data.get("upload_stream", "natural")
        await query.edit_message_text(
            f"Ready to save {len(parsed)} questions\n"
            f"Subject: {subject.replace(\'_\', \' \').title()}\n"
            f"Exam: {exam_type.title()} Stream: {stream.title()}\n\nConfirm?",
            reply_markup=admin_confirm_keyboard())

    elif data == "aq_confirm_save":
        if context.user_data.get("parsed_questions"):
            await save_bulk_questions(query, context)
        else:
            await save_question_from_context(query, context)


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    waiting = context.user_data.get("waiting_for")
    if not waiting:
        return
    text = update.message.text.strip()

    if text == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("Cancelled.", reply_markup=admin_main_keyboard())
        return

    simple_steps = {
        "aq_question_text": ("aq_option_a", "OK. Type Option A:"),
        "aq_option_a":      ("aq_option_b", "OK. Type Option B:"),
        "aq_option_b":      ("aq_option_c", "OK. Type Option C:"),
        "aq_option_c":      ("aq_option_d", "OK. Type Option D:"),
    }

    if waiting in simple_steps:
        context.user_data[waiting] = text
        nxt, msg = simple_steps[waiting]
        context.user_data["waiting_for"] = nxt
        await update.message.reply_text(msg)

    elif waiting == "aq_option_d":
        context.user_data["aq_option_d"] = text
        context.user_data["waiting_for"] = "aq_correct_answer"
        await update.message.reply_text("Correct answer letter: A, B, C, or D")

    elif waiting == "aq_correct_answer":
        if text.upper() not in ["A","B","C","D"]:
            await update.message.reply_text("Must be A, B, C, or D. Try again:")
            return
        context.user_data["aq_correct_answer"] = text.upper()
        context.user_data["waiting_for"] = "aq_explanation"
        await update.message.reply_text("Type the explanation:")

    elif waiting == "aq_explanation":
        context.user_data["aq_explanation"] = text
        context.user_data["waiting_for"] = "aq_reference"
        await update.message.reply_text("Type reference or type none:")

    elif waiting == "aq_reference":
        context.user_data["aq_reference"] = "" if text.lower() == "none" else text
        context.user_data["waiting_for"] = "aq_year"
        await update.message.reply_text("Type exam year (e.g. 2023) or none:")

    elif waiting == "aq_year":
        try:
            context.user_data["aq_year"] = int(text) if text.lower() != "none" else None
        except ValueError:
            context.user_data["aq_year"] = None
        context.user_data["waiting_for"] = None
        d = context.user_data
        preview = (
            "QUESTION PREVIEW\n\n"
            f"Subject: {d.get(\'aq_subject_label\')}\n"
            f"Exam: {d.get(\'aq_exam_type\', \'\').title()} "
            f"Stream: {d.get(\'aq_stream\', \'\').title()}\n"
            f"Year: {d.get(\'aq_year\') or \'N/A\'}\n\n"
            f"Q: {d.get(\'aq_question_text\')}\n\n"
            f"A) {d.get(\'aq_option_a\')}\n"
            f"B) {d.get(\'aq_option_b\')}\n"
            f"C) {d.get(\'aq_option_c\')}\n"
            f"D) {d.get(\'aq_option_d\')}\n\n"
            f"Answer: {d.get(\'aq_correct_answer\')}\n"
            f"Explanation: {d.get(\'aq_explanation\')}\n"
            f"Reference: {d.get(\'aq_reference\') or \'N/A\'}"
        )
        await update.message.reply_text(preview, reply_markup=admin_confirm_keyboard())

    elif waiting == "grant_sub_id":
        parts = text.split("|")
        if len(parts) != 2:
            await update.message.reply_text("Wrong format. Use: telegram_id|days\nExample: 123456789|30")
            return
        try:
            tid = int(parts[0].strip())
            days = int(parts[1].strip())
        except ValueError:
            await update.message.reply_text("Both values must be numbers.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(
                    f"User {tid} not found. They must /start first.",
                    reply_markup=admin_back_keyboard())
                context.user_data.clear()
                return
            await db.execute(
                f"UPDATE users SET is_subscribed=1, "
                f"subscription_expiry=datetime(\'now\',\'+{days} days\') "
                f"WHERE telegram_id=?", (tid,))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text(
            f"Subscription granted to {row[0] or tid} for {days} days.",
            reply_markup=admin_back_keyboard())
        try:
            await context.bot.send_message(
                chat_id=tid,
                text=f"Your subscription is activated! {days} days full access. Good luck!")
        except Exception:
            pass

    elif waiting == "broadcast_msg":
        context.user_data.clear()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT telegram_id FROM users")
            users = await cur.fetchall()
        sent = failed = 0
        for (uid,) in users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"Broadcast done. Sent: {sent} Failed: {failed}",
            reply_markup=admin_back_keyboard())

    elif waiting == "new_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 5:
            await update.message.reply_text(
                "Wrong format. Use: exam_type|stream|key|name|emoji\n\n"
                "Example: entrance|natural|physics|Physics|⚡")
            return
        exam_type, stream, key, name, emoji = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO subjects (exam_type,stream,subject_key,subject_name,emoji) "
                    "VALUES (?,?,?,?,?)",
                    (exam_type, stream, key, name, emoji))
                await db.commit()
                await update.message.reply_text(
                    f"Subject {name} added successfully!",
                    reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(
                    f"Error: {e}\nMaybe that key already exists. Use a unique key.",
                    reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Wrong format. Use: old_key|new_name|new_emoji")
            return
        old_key, new_name, new_emoji = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id FROM subjects WHERE subject_key=?", (old_key,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(
                    f"Subject with key \'{old_key}\' not found. Check your subject keys.",
                    reply_markup=admin_back_keyboard())
                context.user_data.clear()
                return
            await db.execute(
                "UPDATE subjects SET subject_name=?, emoji=? WHERE subject_key=?",
                (new_name, new_emoji, old_key))
            await db.commit()
        await update.message.reply_text(
            f"Subject updated to {new_name} {new_emoji}",
            reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_subject_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT subject_name FROM subjects WHERE subject_key=?", (text,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(
                    f"Subject key \'{text}\' not found.",
                    reply_markup=admin_back_keyboard())
                context.user_data.clear()
                return
            await db.execute("DELETE FROM subjects WHERE subject_key=?", (text,))
            await db.commit()
        await update.message.reply_text(
            f"Subject {row[0]} deleted.",
            reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "new_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Wrong format. Use: key|name|emoji")
            return
        key, name, emoji = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO departments (dept_key,dept_name,emoji) VALUES (?,?,?)",
                    (key, name, emoji))
                await db.commit()
                await update.message.reply_text(
                    f"Department {name} added!",
                    reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(
                    f"Error: {e}",
                    reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Wrong format. Use: old_key|new_name|new_emoji")
            return
        old_key, new_name, new_emoji = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id FROM departments WHERE dept_key=?", (old_key,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(f"Department \'{old_key}\' not found.")
                context.user_data.clear()
                return
            await db.execute(
                "UPDATE departments SET dept_name=?, emoji=? WHERE dept_key=?",
                (new_name, new_emoji, old_key))
            await db.commit()
        await update.message.reply_text(
            f"Department updated to {new_name} {new_emoji}",
            reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_dept_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT dept_name FROM departments WHERE dept_key=?", (text,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(f"Department key \'{text}\' not found.")
                context.user_data.clear()
                return
            await db.execute("DELETE FROM departments WHERE dept_key=?", (text,))
            await db.commit()
        await update.message.reply_text(
            f"Department {row[0]} deleted.",
            reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_question_id":
        try:
            qid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number. Try again:")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM questions WHERE id=?", (qid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(
                    f"Question ID {qid} not found.",
                    reply_markup=admin_back_keyboard())
                context.user_data.clear()
                return
            q = dict(row)
        context.user_data["edit_question_id"] = qid
        context.user_data["waiting_for"] = None
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        preview = (
            f"ID: {q[\'id\']} | Subject: {q[\'subject\']} | Year: {q.get(\'year\') or \'N/A\'}\n\n"
            f"Q: {q[\'question_text\']}\n\n"
            f"A) {q[\'option_a\']}\n"
            f"B) {q[\'option_b\']}\n"
            f"C) {q[\'option_c\']}\n"
            f"D) {q[\'option_d\']}\n\n"
            f"Answer: {q[\'correct_answer\']}\n"
            f"Explanation: {q.get(\'explanation\',\'\')}\n"
            f"Reference: {q.get(\'reference\',\'\')}"
        )
        edit_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Edit Question Text", callback_data="edit_q_field_question")],
            [InlineKeyboardButton("Edit Option A", callback_data="edit_q_field_a"),
             InlineKeyboardButton("Edit Option B", callback_data="edit_q_field_b")],
            [InlineKeyboardButton("Edit Option C", callback_data="edit_q_field_c"),
             InlineKeyboardButton("Edit Option D", callback_data="edit_q_field_d")],
            [InlineKeyboardButton("Edit Answer", callback_data="edit_q_field_answer")],
            [InlineKeyboardButton("Edit Explanation", callback_data="edit_q_field_explanation")],
            [InlineKeyboardButton("Edit Reference", callback_data="edit_q_field_reference")],
            [InlineKeyboardButton("Edit Year", callback_data="edit_q_field_year")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
        ])
        await update.message.reply_text(preview, reply_markup=edit_kb)

    elif waiting == "edit_q_value":
        qid = context.user_data.get("edit_question_id")
        field = context.user_data.get("edit_field")
        if not qid or not field:
            await update.message.reply_text("Session expired. Try again.")
            context.user_data.clear()
            return
        value = text.upper() if field == "correct_answer" else text
        if field == "correct_answer" and value not in ["A","B","C","D"]:
            await update.message.reply_text("Must be A, B, C, or D. Try again:")
            return
        if field == "year":
            try:
                value = int(text) if text.lower() != "none" else None
            except ValueError:
                value = None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                f"UPDATE questions SET {field}=? WHERE id=?", (value, qid))
            await db.commit()
        context.user_data["waiting_for"] = None
        await update.message.reply_text(
            f"Question {qid} updated! Field \'{field}\' changed.",
            reply_markup=admin_back_keyboard())

    elif waiting == "delete_question_id":
        try:
            qid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number. Try again:")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT subject FROM questions WHERE id=?", (qid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(f"Question ID {qid} not found.")
                context.user_data.clear()
                return
            await db.execute("DELETE FROM questions WHERE id=?", (qid,))
            await db.commit()
        await update.message.reply_text(
            f"Question {qid} deleted from {row[0]}.",
            reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "giveaway_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("Wrong format. Use: days|max_uses\nExample: 7|100")
            return
        try:
            days = int(parts[0])
            max_uses = int(parts[1])
        except ValueError:
            await update.message.reply_text("Both must be numbers.")
            return
        code = gen_code()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO giveaway_codes (code,duration_days,max_uses,created_by) "
                "VALUES (?,?,?,?)",
                (code, days, max_uses, update.effective_user.id))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text(
            f"Giveaway Code Created!\n\n"
            f"Code: {code}\n"
            f"Duration: {days} days free access\n"
            f"Max Uses: {max_uses} students\n\n"
            f"Share this code with students.\n"
            f"They use /redeem {code} in the bot.",
            reply_markup=admin_back_keyboard())
        logger.info(f"Giveaway code created: {code} {days}days {max_uses}uses")


async def admin_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if context.user_data.get("waiting_for") != "question_file":
        return
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Please send a .txt file only.")
        return
    await update.message.reply_text("Reading your file...")
    file = await context.bot.get_file(doc.file_id)
    content = bytes(await file.download_as_bytearray()).decode("utf-8", errors="ignore")
    parsed = parse_questions_from_text(content)
    if not parsed:
        await update.message.reply_text(
            "No valid questions found. Check the format.",
            reply_markup=admin_back_keyboard())
        return
    context.user_data["parsed_questions"] = parsed
    context.user_data["waiting_for"] = "upload_exam_type"
    await update.message.reply_text(
        f"Found {len(parsed)} questions! Choose exam type:",
        reply_markup=admin_exam_type_keyboard())


async def save_bulk_questions(query, context):
    parsed = context.user_data.get("parsed_questions", [])
    exam_type = context.user_data.get("upload_exam_type", "entrance")
    stream = context.user_data.get("upload_stream", "natural")
    subject = context.user_data.get("upload_subject", "")
    saved = failed = 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for q in parsed:
            try:
                await db.execute(
                    "INSERT INTO questions "
                    "(exam_type,stream,subject,year,question_text,"
                    "option_a,option_b,option_c,option_d,"
                    "correct_answer,explanation,reference) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exam_type, stream, subject, q.get("year"),
                     q.get("question_text"), q.get("option_a"),
                     q.get("option_b"), q.get("option_c"), q.get("option_d"),
                     q.get("correct_answer"), q.get("explanation",""),
                     q.get("reference","")))
                saved += 1
            except Exception:
                failed += 1
        await db.commit()
    context.user_data.clear()
    logger.info(f"Bulk upload: {saved} saved to {subject}")
    await query.edit_message_text(
        f"Upload complete! Saved: {saved} Failed: {failed}\n"
        f"Subject: {subject.replace(\'_\', \' \').title()}",
        reply_markup=admin_back_keyboard())


async def save_question_from_context(query, context):
    d = context.user_data
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO questions "
                "(exam_type,stream,subject,year,question_text,"
                "option_a,option_b,option_c,option_d,"
                "correct_answer,explanation,reference) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (d.get("aq_exam_type"), d.get("aq_stream"),
                 d.get("aq_subject"), d.get("aq_year"),
                 d.get("aq_question_text"), d.get("aq_option_a"),
                 d.get("aq_option_b"), d.get("aq_option_c"),
                 d.get("aq_option_d"), d.get("aq_correct_answer"),
                 d.get("aq_explanation",""), d.get("aq_reference","")))
            await db.commit()
        context.user_data.clear()
        await query.edit_message_text(
            "Question saved successfully!", reply_markup=admin_main_keyboard())
        logger.info(f"Manual question: {d.get(\'aq_subject\')}")
    except Exception as e:
        await query.edit_message_text(str(e), reply_markup=admin_main_keyboard())


async def show_users(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        sub = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        today = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(last_active)=date(\'now\')")).fetchone())[0]
        new = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(created_at)=date(\'now\')")).fetchone())[0]
        cur = await db.execute(
            "SELECT telegram_id,full_name,is_subscribed,free_access_expiry "
            "FROM users ORDER BY created_at DESC LIMIT 10")
        recent = await cur.fetchall()
    lines = ""
    for r in recent:
        tag = "[SUB]" if r[2] else ("[FREE]" if r[3] else "[BASIC]")
        lines += f"{tag} {r[1] or \'Unknown\'} ({r[0]})\n"
    await query.edit_message_text(
        f"Users\n\nTotal: {total} Sub: {sub} Free: {total-sub}\n"
        f"Active today: {today} New today: {new}\n\nRecent:\n{lines}",
        reply_markup=admin_back_keyboard())


async def show_stats(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        exams = (await (await db.execute(
            "SELECT COUNT(*) FROM exam_sessions WHERE completed=1")).fetchone())[0]
        today_count = (await (await db.execute(
            "SELECT COUNT(*) FROM exam_sessions WHERE completed=1 "
            "AND date(finished_at)=date(\'now\')")).fetchone())[0]
        row = await (await db.execute(
            "SELECT AVG(CAST(score AS FLOAT)/total*100) "
            "FROM exam_sessions WHERE completed=1 AND total>0")).fetchone()
        avg = row[0] if row[0] else 0
        qcount = (await (await db.execute(
            "SELECT COUNT(*) FROM questions")).fetchone())[0]
        cur = await db.execute(
            "SELECT subject,COUNT(*) FROM exam_sessions WHERE completed=1 "
            "GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 5")
        pop = await cur.fetchall()
    pop_text = "\n".join(
        f"  {p[0].replace(\'_\',\' \').title()}: {p[1]}" for p in pop) or "None yet"
    await query.edit_message_text(
        f"Statistics\n\nTotal Exams: {exams} Today: {today_count}\n"
        f"Avg Score: {avg:.1f}% Questions: {qcount}\n\nPopular:\n{pop_text}",
        reply_markup=admin_back_keyboard())


async def show_questions(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id, subject, year, question_text FROM questions "
            "ORDER BY subject, year DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No questions yet.", reply_markup=admin_back_keyboard())
        return
    text = "Questions (showing up to 30)\n\n"
    for r in rows:
        yr = str(r[2]) if r[2] else "N/A"
        q_short = r[3][:40] + "..." if len(r[3]) > 40 else r[3]
        text += f"ID:{r[0]} [{r[1]}] {yr}\n{q_short}\n\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_subjects(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT exam_type,stream,subject_key,subject_name,emoji "
            "FROM subjects ORDER BY exam_type,stream,subject_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No subjects yet.", reply_markup=admin_back_keyboard())
        return
    text = "All Subjects\n\n"
    for r in rows:
        text += f"{r[4]} {r[3]} ({r[0]}/{r[1]}) key={r[2]}\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_depts(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT dept_key,dept_name,emoji FROM departments ORDER BY dept_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No departments yet.", reply_markup=admin_back_keyboard())
        return
    text = "All Departments\n\n"
    for r in rows:
        text += f"{r[2]} {r[1]} key={r[0]}\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_giveaways(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT code,duration_days,max_uses,used_count,created_at "
            "FROM giveaway_codes ORDER BY created_at DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No giveaway codes yet.", reply_markup=admin_back_keyboard())
        return
    text = "Active Giveaway Codes\n\n"
    for r in rows:
        text += f"Code: {r[0]}\n{r[3]}/{r[1]} uses | {r[1]} days\nCreated: {r[4][:10]}\n\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())
''')


# ── app/handlers/user_features.py ────────────────────────
w("app/handlers/user_features.py", '''from telegram import Update
from telegram.ext import ContextTypes
from config import DATABASE_PATH
from app.keyboards.main_menu import back_to_main_keyboard
from app.utils.logger import logger
import aiosqlite
import random
import string


def gen_referral_code(length=7):
    return \'\'.join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def ensure_referral_code(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT referral_code FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        if row and row[0]:
            return row[0]
        code = gen_referral_code()
        await db.execute(
            "UPDATE users SET referral_code=? WHERE telegram_id=?", (code, telegram_id))
        await db.commit()
        return code


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text(
            "Usage: /redeem CODE\n\nEnter the code you received.\n"
            "Example: /redeem ABC12345")
        return

    code = args[0].strip().upper()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT * FROM giveaway_codes WHERE code=?", (code,))
        gc = await cur.fetchone()

        if not gc:
            await update.message.reply_text(
                "Invalid code. Please check and try again.")
            return

        gc_id, gc_code, duration_days, max_uses, used_count, created_by, expires_at, created_at = gc

        if used_count >= max_uses:
            await update.message.reply_text(
                "This code has reached its maximum uses. Contact admin for a new code.")
            return

        cur2 = await db.execute(
            "SELECT id FROM giveaway_uses WHERE code=? AND telegram_id=?",
            (code, user.id))
        already_used = await cur2.fetchone()
        if already_used:
            await update.message.reply_text(
                "You have already used this code.")
            return

        await db.execute(
            "UPDATE giveaway_codes SET used_count=used_count+1 WHERE code=?", (code,))
        await db.execute(
            "INSERT INTO giveaway_uses (code,telegram_id) VALUES (?,?)",
            (code, user.id))
        await db.execute(
            f"UPDATE users SET free_access_expiry=datetime(\'now\',\'+{duration_days} days\') "
            f"WHERE telegram_id=?", (user.id,))
        await db.commit()

    await update.message.reply_text(
        f"Code redeemed successfully!\n\n"
        f"You now have {duration_days} days of FREE access to all exams.\n\n"
        f"Start practicing now! Send /start",
        reply_markup=back_to_main_keyboard())
    logger.info(f"User {user.id} redeemed giveaway code {code}")


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    code = await ensure_referral_code(user.id)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT referral_count FROM users WHERE telegram_id=?", (user.id,))
        row = await cur.fetchone()
        count = row[0] if row else 0

    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start=ref_{code}"

    await update.message.reply_text(
        f"Your Referral Code: {code}\n\n"
        f"Your Referral Link:\n{referral_link}\n\n"
        f"Friends referred: {count}\n\n"
        f"For every 3 friends who join using your code,\n"
        f"you get 7 days free access!\n\n"
        f"Share your link and start earning free access!",
        reply_markup=back_to_main_keyboard())


async def handle_referral_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if args and args[0].startswith("ref_"):
        referrer_code = args[0].replace("ref_", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT telegram_id, referral_count FROM users WHERE referral_code=?",
                (referrer_code,))
            referrer = await cur.fetchone()

            if referrer and referrer[0] != user.id:
                cur2 = await db.execute(
                    "SELECT referred_by FROM users WHERE telegram_id=?", (user.id,))
                me = await cur2.fetchone()

                if me and not me[0]:
                    await db.execute(
                        "UPDATE users SET referred_by=? WHERE telegram_id=?",
                        (referrer_code, user.id))
                    new_count = referrer[1] + 1
                    await db.execute(
                        "UPDATE users SET referral_count=? WHERE telegram_id=?",
                        (new_count, referrer[0]))

                    if new_count % 3 == 0:
                        await db.execute(
                            "UPDATE users SET free_access_expiry=CASE "
                            "WHEN free_access_expiry IS NULL OR free_access_expiry < datetime(\'now\') "
                            "THEN datetime(\'now\',\'+7 days\') "
                            "ELSE datetime(free_access_expiry,\'+7 days\') END "
                            "WHERE telegram_id=?", (referrer[0],))
                        try:
                            await context.bot.send_message(
                                chat_id=referrer[0],
                                text=f"You earned 7 days free access! "
                                     f"You have now referred {new_count} friends. Keep sharing!")
                        except Exception:
                            pass

                    await db.commit()
''')


# ── app/handlers/start.py ─────────────────────────────────
w("app/handlers/start.py", '''from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import get_db
from app.keyboards.main_menu import (
    main_menu_keyboard, stream_keyboard,
    exit_department_keyboard, back_to_main_keyboard,
)
from app.utils.logger import logger
from app.handlers.user_features import handle_referral_start, ensure_referral_code
from config import ADMIN_ID
import aiosqlite
from config import DATABASE_PATH


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id=?", (user.id,))
        existing = await cur.fetchone()

        if not existing:
            is_admin = 1 if user.id == ADMIN_ID else 0
            await db.execute(
                "INSERT INTO users (telegram_id,username,full_name,is_admin) VALUES (?,?,?,?)",
                (user.id, user.username, user.full_name, is_admin))
            await db.commit()
            logger.info(f"New user: {user.full_name} ({user.id})")
            await handle_referral_start(update, context)
        else:
            await db.execute(
                "UPDATE users SET last_active=datetime(\'now\') WHERE telegram_id=?",
                (user.id,))
            await db.commit()

    await ensure_referral_code(user.id)

    welcome_text = (
        f"Welcome, {user.first_name}!\n\n"
        "Ethiopian Exam Preparation Bot\n\n"
        "Prepare for:\n"
        "- Ethiopian University Entrance Exam\n"
        "- University Exit Exam\n\n"
        "Practice with real past questions\n"
        "Get instant feedback and explanations\n"
        "Track your progress over time\n\n"
        "Choose an option:"
    )
    await update.message.reply_text(
        welcome_text, reply_markup=main_menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "back_main":
        await query.edit_message_text(
            "Main Menu:", reply_markup=main_menu_keyboard())

    elif data == "exam_type_entrance":
        await query.edit_message_text(
            "Entrance Exam\n\nChoose your stream:",
            reply_markup=stream_keyboard())

    elif data == "exam_type_exit":
        await query.edit_message_text(
            "University Exit Exam\n\nChoose your department:",
            reply_markup=exit_department_keyboard())

    elif data.startswith("stream_"):
        stream = data.replace("stream_", "")
        stream_names = {"natural": "Natural Science", "social": "Social Science"}
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET exam_type=\'entrance\', stream=? WHERE telegram_id=?",
                (stream, user.id))
            await db.commit()
        await query.edit_message_text(
            f"Stream selected: {stream_names.get(stream, stream)}\n\n"
            "Profile saved. You can now start practicing!",
            reply_markup=back_to_main_keyboard())

    elif data.startswith("dept_"):
        dept = data.replace("dept_", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET exam_type=\'exit\', department=? WHERE telegram_id=?",
                (dept, user.id))
            await db.commit()
        await query.edit_message_text(
            f"Department selected: {dept.replace(\'_\',\' \').title()}\n\n"
            "Profile saved. You can now start practicing!",
            reply_markup=back_to_main_keyboard())

    elif data == "my_progress":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT score,total FROM exam_sessions "
                "WHERE telegram_id=? AND completed=1", (user.id,))
            sessions = await cur.fetchall()
            cur2 = await db.execute(
                "SELECT referral_count, referral_code FROM users WHERE telegram_id=?",
                (user.id,))
            urow = await cur2.fetchone()
        if not sessions:
            text = "Your Progress\n\nNo exams completed yet. Start practicing!"
        else:
            total_s = len(sessions)
            avg = sum(s[0] for s in sessions) / total_s
            avg_t = sum(s[1] for s in sessions) / total_s
            pct = (avg/avg_t*100) if avg_t > 0 else 0
            ref_count = urow[0] if urow else 0
            text = (
                f"Your Progress\n\n"
                f"Exams taken: {total_s}\n"
                f"Average score: {avg:.1f}/{avg_t:.0f}\n"
                f"Average %: {pct:.1f}%\n\n"
                f"Friends referred: {ref_count}\n"
                f"Use /referral to see your referral link"
            )
        await query.edit_message_text(text, reply_markup=back_to_main_keyboard())

    elif data == "subscribe":
        await query.edit_message_text(
            "Subscription\n\n"
            "Get full access for 50 ETB/month.\n\n"
            "Payment system coming soon!\n\n"
            "You can also:\n"
            "- Use /redeem CODE for free access\n"
            "- Use /referral to earn free days",
            reply_markup=back_to_main_keyboard())

    elif data == "help":
        await query.edit_message_text(
            "Help\n\n"
            "Commands:\n"
            "/start - Main menu\n"
            "/redeem CODE - Redeem free access code\n"
            "/referral - Get your referral link\n\n"
            "How to use:\n"
            "1. Choose exam type\n"
            "2. Select stream or department\n"
            "3. Start practicing!\n\n"
            "Contact admin for support.",
            reply_markup=back_to_main_keyboard())
''')


# ── main.py ───────────────────────────────────────────────
w("main.py", '''from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)
from config import BOT_TOKEN
from app.database.db import init_db
from app.exams.engine import seed_sample_questions
from app.handlers.start import start_handler, button_handler
from app.handlers.exam import (
    subject_selection_handler, show_subject_intro, year_select_handler,
    start_exam_handler, answer_handler, next_question_handler, retry_exam_handler,
)
from app.handlers.admin import (
    admin_command, admin_button_handler, admin_text_handler,
    admin_file_handler, admin_upload_handler,
)
from app.handlers.user_features import redeem_command, referral_command
from app.utils.logger import logger


def main():
    logger.info("Starting EthiopianExamBot...")

    async def post_init(application):
        await init_db()
        await seed_sample_questions()
        logger.info("Bot started successfully!")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("referral", referral_command))

    app.add_handler(CallbackQueryHandler(
        admin_upload_handler,
        pattern="^(aq_type_|aq_stream_|upload_subject_|aq_confirm_save)"))
    app.add_handler(CallbackQueryHandler(
        admin_button_handler,
        pattern="^(admin_|aq_subject_|edit_q_field_)"))
    app.add_handler(CallbackQueryHandler(
        subject_selection_handler, pattern="^choose_subject$"))
    app.add_handler(CallbackQueryHandler(
        show_subject_intro, pattern="^subject_"))
    app.add_handler(CallbackQueryHandler(
        year_select_handler, pattern="^examyear_"))
    app.add_handler(CallbackQueryHandler(
        start_exam_handler, pattern="^start_exam_"))
    app.add_handler(CallbackQueryHandler(
        answer_handler, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(
        next_question_handler, pattern="^next_question$"))
    app.add_handler(CallbackQueryHandler(
        retry_exam_handler, pattern="^retry_exam$"))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.Document.TXT, admin_file_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, admin_text_handler))

    logger.info("Handlers registered. Bot is polling...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
''')

print("All files written successfully!")
print("Now run: python main.py")