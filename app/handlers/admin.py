"""
app/handlers/admin.py
─────────────────────
Admin panel: questions, subjects, departments, users, subscriptions,
bulk-delete, referral stats, backup/restore.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import (
    admin_main_keyboard, admin_back_keyboard, admin_confirm_keyboard,
    admin_exam_type_keyboard, admin_stream_keyboard,
    build_subject_keyboard, build_dept_keyboard,
    manage_subjects_keyboard, manage_depts_keyboard,
    manage_admins_keyboard, giveaway_keyboard, receipt_action_keyboard,
    bulk_delete_main_keyboard, bulk_delete_exam_type_keyboard,
    backup_main_keyboard, backup_restore_keyboard,
)
from app.utils.access import is_any_admin, get_admin_role
from app.utils.logger import logger
from app.utils.question_parser import parse_questions_from_text
from config import ADMIN_ID, DATABASE_PATH
import aiosqlite
import random
import string


def gen_code(n=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


async def get_subjects(exam_type, stream):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects "
            "WHERE exam_type=? AND stream=? ORDER BY subject_name",
            (exam_type, stream))
        return [dict(r) for r in await cur.fetchall()]


async def get_depts(exam_type="exit"):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=? ORDER BY dept_name",
            (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


# ─────────────────────── /admin command ──────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_any_admin(uid):
        await update.message.reply_text("⛔ Unauthorized.")
        return
    role = await get_admin_role(uid)
    await update.message.reply_text(
        "🛡️ *Admin Panel*\n\nRole: " + (role or "super").upper(),
        parse_mode="Markdown",
        reply_markup=admin_main_keyboard(role or "super"))


# ─────────────────────── Callback router ─────────────────────────────────────

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid  = query.from_user.id
    if not await is_any_admin(uid):
        await query.edit_message_text("⛔ Unauthorized.")
        return
    role     = await get_admin_role(uid)
    is_super = (role == "super")

    # ── Navigation ────────────────────────────────────────────────────────────
    if data == "admin_back":
        await query.edit_message_text(
            "🛡️ *Admin Panel*",
            parse_mode="Markdown",
            reply_markup=admin_main_keyboard(role or "super"))
    elif data == "admin_close":
        await query.edit_message_text("✅ Panel closed.")

    # ── Basic views ───────────────────────────────────────────────────────────
    elif data == "admin_view_users":
        await show_users(query)
    elif data == "admin_stats":
        if not is_super:
            await query.edit_message_text("⛔ No permission.", reply_markup=admin_back_keyboard())
            return
        await show_stats(query)
    elif data == "admin_view_questions":
        await show_questions(query)
    elif data.startswith("vq_type_"):
        exam_type = data.replace("vq_type_", "")
        await show_questions_by_type(query, exam_type)
    elif data.startswith("vq_stream_"):
        parts = data.replace("vq_stream_", "").split("_", 1)
        if len(parts) == 2:
            await show_questions_list(query, parts[0], parts[1])
    elif data.startswith("vq_dept_"):
        rest      = data.replace("vq_dept_", "")
        first_sep = rest.index("_")
        et        = rest[:first_sep]
        dk        = rest[first_sep + 1:]
        await show_questions_list(query, et, dk)
    elif data.startswith("vq_page_"):
        rest  = data.replace("vq_page_", "")
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            try:   offset = int(parts[1])
            except ValueError: offset = 0
            inner = parts[0]
            sep   = inner.index("_")
            et, st = inner[:sep], inner[sep + 1:]
            await show_questions_list(query, et, st, offset)

    # ── Manage Subjects / Depts / Admins ──────────────────────────────────────
    elif data == "admin_manage_subjects":
        await query.edit_message_text("📚 Manage Subjects", reply_markup=manage_subjects_keyboard())
    elif data == "admin_manage_depts":
        await query.edit_message_text("🏛️ Manage Departments", reply_markup=manage_depts_keyboard())
    elif data == "admin_manage_admins":
        if not is_super:
            await query.edit_message_text("⛔ No permission.", reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("👮 Manage Admins", reply_markup=manage_admins_keyboard())
    elif data == "admin_list_admins":
        await list_admins(query)
    elif data == "admin_add_subadmin":
        if not is_super:
            await query.edit_message_text("⛔ No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "add_subadmin"
        await query.edit_message_text(
            "➕ *Add Sub Admin*\n\nSend the Telegram ID.\nThey must have started the bot.\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_remove_admin":
        if not is_super:
            await query.edit_message_text("⛔ No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "remove_admin"
        await query.edit_message_text(
            "🗑️ *Remove Admin*\n\nSend the Telegram ID of the admin to remove.\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_add_subject":
        context.user_data["waiting_for"] = "new_subject_info"
        await query.edit_message_text(
            "➕ *Add Subject*\n\n"
            "Format: `exam_type|stream|key|name|emoji`\n\n"
            "Example: `entrance|natural|physics|Physics|⚡`\n\n"
            "Type /cancel to abort.", parse_mode="Markdown")
    elif data == "admin_edit_subject":
        context.user_data["waiting_for"] = "edit_subject_info"
        await query.edit_message_text(
            "✏️ *Edit Subject*\n\nFormat: `old_key|new_name|new_emoji`\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_delete_subject":
        context.user_data["waiting_for"] = "delete_subject_key"
        await query.edit_message_text(
            "🗑️ *Delete Subject*\n\nSend the subject key.\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_list_subjects":
        await list_subjects(query)
    elif data == "admin_add_dept":
        context.user_data["waiting_for"] = "new_dept_info"
        await query.edit_message_text(
            "➕ *Add Department*\n\n"
            "Format: `exam_type|key|name|emoji`\n\n"
            "Example: `exit|nursing|Nursing|🩺`\n\n"
            "Type /cancel to abort.", parse_mode="Markdown")
    elif data == "admin_edit_dept":
        context.user_data["waiting_for"] = "edit_dept_info"
        await query.edit_message_text(
            "✏️ *Edit Department*\n\nFormat: `old_key|new_name|new_emoji`\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_delete_dept":
        context.user_data["waiting_for"] = "delete_dept_key"
        await query.edit_message_text(
            "🗑️ *Delete Department*\n\nSend the department key.\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_list_depts":
        await list_depts(query)

    # ── Question management ───────────────────────────────────────────────────
    elif data == "admin_add_question":
        context.user_data.clear()
        await query.edit_message_text(
            "➕ *Add Question*\n\nStep 1: Choose exam type:",
            parse_mode="Markdown",
            reply_markup=admin_exam_type_keyboard())
    elif data == "admin_edit_question":
        context.user_data["waiting_for"] = "edit_question_id"
        await query.edit_message_text(
            "✏️ *Edit Question*\n\nSend the question ID number.\nUse View Questions to find IDs.\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_delete_question":
        context.user_data["waiting_for"] = "delete_question_id"
        await query.edit_message_text(
            "🗑️ *Delete Question*\n\nSend the question ID number.\n\nType /cancel to abort.",
            parse_mode="Markdown")

    # ── Bulk Delete ───────────────────────────────────────────────────────────
    elif data == "admin_bulk_delete":
        await show_bulk_delete_menu(query)
    elif data == "bd_by_type":
        await query.edit_message_text(
            "🗑️🗑️ *Bulk Delete — By Exam Type*\n\nChoose which exam type to delete ALL questions for:",
            parse_mode="Markdown",
            reply_markup=bulk_delete_exam_type_keyboard())
    elif data.startswith("bd_type_"):
        exam_type = data.replace("bd_type_", "")
        context.user_data["bd_exam_type"] = exam_type
        async with aiosqlite.connect(DATABASE_PATH) as db:
            count = (await (await db.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_type=?", (exam_type,))).fetchone())[0]
        await query.edit_message_text(
            f"⚠️ *Confirm Bulk Delete*\n\n"
            f"Delete ALL *{count} questions* for exam type: *{exam_type.title()}*\n\n"
            "This cannot be undone!\n\nType `YES DELETE` to confirm, or /cancel to abort.",
            parse_mode="Markdown")
        context.user_data["waiting_for"] = "bd_confirm_type"
    elif data == "bd_by_subject":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur  = await db.execute("SELECT subject, COUNT(*) FROM questions GROUP BY subject ORDER BY subject")
            rows = await cur.fetchall()
        if not rows:
            await query.edit_message_text("No questions found.", reply_markup=bulk_delete_main_keyboard())
            return
        buttons = []
        for subj, cnt in rows:
            label = (subj or "unknown").replace("_", " ").title()
            buttons.append([InlineKeyboardButton(f"📚 {label} ({cnt})", callback_data=f"bd_subj_{subj}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_bulk_delete")])
        await query.edit_message_text(
            "🗑️🗑️ *Bulk Delete — Choose Subject*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("bd_subj_"):
        subj = data.replace("bd_subj_", "")
        context.user_data["bd_subject"] = subj
        async with aiosqlite.connect(DATABASE_PATH) as db:
            count = (await (await db.execute(
                "SELECT COUNT(*) FROM questions WHERE subject=?", (subj,))).fetchone())[0]
        await query.edit_message_text(
            f"⚠️ Delete ALL *{count} questions* for subject: *{subj.replace('_',' ').title()}*\n\n"
            "Type `YES DELETE` to confirm, or /cancel to abort.",
            parse_mode="Markdown")
        context.user_data["waiting_for"] = "bd_confirm_subject"
    elif data == "bd_by_year":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur  = await db.execute(
                "SELECT year, COUNT(*) FROM questions WHERE year IS NOT NULL GROUP BY year ORDER BY year DESC")
            rows = await cur.fetchall()
        if not rows:
            await query.edit_message_text("No questions with year found.", reply_markup=bulk_delete_main_keyboard())
            return
        buttons = []
        row = []
        for yr, cnt in rows:
            row.append(InlineKeyboardButton(f"📅 {yr} ({cnt})", callback_data=f"bd_year_{yr}"))
            if len(row) == 3:
                buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_bulk_delete")])
        await query.edit_message_text(
            "🗑️🗑️ *Bulk Delete — Choose Year*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("bd_year_"):
        year = data.replace("bd_year_", "")
        context.user_data["bd_year"] = year
        async with aiosqlite.connect(DATABASE_PATH) as db:
            count = (await (await db.execute(
                "SELECT COUNT(*) FROM questions WHERE year=?", (year,))).fetchone())[0]
        await query.edit_message_text(
            f"⚠️ Delete ALL *{count} questions* for year: *{year}*\n\n"
            "Type `YES DELETE` to confirm, or /cancel to abort.",
            parse_mode="Markdown")
        context.user_data["waiting_for"] = "bd_confirm_year"
    elif data == "bd_by_subject_year":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur  = await db.execute("SELECT subject, COUNT(*) FROM questions GROUP BY subject ORDER BY subject")
            rows = await cur.fetchall()
        if not rows:
            await query.edit_message_text("No questions found.", reply_markup=bulk_delete_main_keyboard())
            return
        buttons = [[InlineKeyboardButton(
            f"📚 {(s or 'unknown').replace('_',' ').title()} ({c})", callback_data=f"bd_sy_subj_{s}"
        )] for s, c in rows]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_bulk_delete")])
        await query.edit_message_text(
            "🗑️🗑️ *Subject + Year* — choose subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("bd_sy_subj_"):
        subj = data.replace("bd_sy_subj_", "")
        context.user_data["bd_sy_subject"] = subj
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur  = await db.execute(
                "SELECT year, COUNT(*) FROM questions WHERE subject=? AND year IS NOT NULL "
                "GROUP BY year ORDER BY year DESC", (subj,))
            rows = await cur.fetchall()
        if not rows:
            await query.edit_message_text(
                f"No years found for *{subj.replace('_',' ').title()}*.",
                parse_mode="Markdown", reply_markup=bulk_delete_main_keyboard())
            return
        buttons = []
        row = []
        for yr, cnt in rows:
            row.append(InlineKeyboardButton(f"📅 {yr} ({cnt})", callback_data=f"bd_sy_year_{yr}"))
            if len(row) == 3:
                buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="bd_by_subject_year")])
        await query.edit_message_text(
            f"📚 *{subj.replace('_',' ').title()}* — choose year:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("bd_sy_year_"):
        yr   = data.replace("bd_sy_year_", "")
        subj = context.user_data.get("bd_sy_subject", "")
        context.user_data["bd_year"]    = yr
        context.user_data["bd_subject"] = subj
        async with aiosqlite.connect(DATABASE_PATH) as db:
            count = (await (await db.execute(
                "SELECT COUNT(*) FROM questions WHERE subject=? AND year=?",
                (subj, yr))).fetchone())[0]
        await query.edit_message_text(
            f"⚠️ Delete ALL *{count} questions* for *{subj.replace('_',' ').title()}* / year *{yr}*\n\n"
            "Type `YES DELETE` to confirm, or /cancel to abort.",
            parse_mode="Markdown")
        context.user_data["waiting_for"] = "bd_confirm_subject_year"
    elif data == "bd_all_confirm":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            count = (await (await db.execute("SELECT COUNT(*) FROM questions")).fetchone())[0]
        await query.edit_message_text(
            f"☢️ *DANGER: Delete ALL {count} Questions*\n\n"
            "This is irreversible!\n\nType `YES DELETE ALL` to confirm, or /cancel to abort.",
            parse_mode="Markdown")
        context.user_data["waiting_for"] = "bd_confirm_all"

    # ── Referral Stats ────────────────────────────────────────────────────────
    elif data == "admin_referral_stats":
        await show_referral_stats(query)
    elif data.startswith("admin_ref_page_"):
        page = int(data.replace("admin_ref_page_", ""))
        await show_referral_stats(query, page=page)

    # ── Backup & Restore ──────────────────────────────────────────────────────
    elif data == "admin_backup_menu":
        from app.handlers.backup import backup_menu_handler
        await backup_menu_handler(update, context)
        return
    elif data in ("bkp_full", "bkp_questions", "bkp_users"):
        from app.handlers.backup import backup_trigger_handler
        await backup_trigger_handler(update, context)
        return
    elif data == "bkp_restore_menu":
        from app.handlers.backup import backup_restore_menu_handler
        await backup_restore_menu_handler(update, context)
        return
    elif data in ("bkp_do_restore_merge", "bkp_do_restore_replace"):
        from app.handlers.backup import backup_do_restore_handler
        await backup_do_restore_handler(update, context)
        return

    # ── Upload / upload flow ──────────────────────────────────────────────────
    elif data == "admin_upload_file":
        context.user_data["waiting_for"] = "question_file"
        await query.edit_message_text(
            "📄 *Upload Question File*\n\n"
            "Send a `.txt` file with this format:\n\n"
            "```\n"
            "Q: Question text here\n"
            "A) Option A\n"
            "B) Option B\n"
            "C) Option C\n"
            "D) Option D\n"
            "Answer: B\n"
            "Explanation: Because...\n"
            "Reference: Grade 12 Book\n"
            "Year: 2023\n"
            "```\n\n"
            "Separate each question with a blank line.\nSend the `.txt` file now:",
            parse_mode="Markdown")

    # ── Subscriptions / giveaway ──────────────────────────────────────────────
    elif data == "admin_grant_sub":
        context.user_data["waiting_for"] = "grant_sub_info"
        await query.edit_message_text(
            "💳 *Grant Subscription*\n\n"
            "Format: `telegram_id|days|exam_type|stream_or_dept`\n\n"
            "Examples:\n"
            "`123456789|30|entrance|natural`\n"
            "`123456789|30|exit|medicine`\n"
            "`123456789|30|coc|coc_electrical`\n"
            "`123456789|30|driving|general`\n\n"
            "Type /cancel to abort.", parse_mode="Markdown")
    elif data == "admin_giveaway":
        await query.edit_message_text("🎁 *Giveaway Free Access*", parse_mode="Markdown",
                                       reply_markup=giveaway_keyboard())
    elif data == "admin_create_giveaway":
        context.user_data["waiting_for"] = "giveaway_info"
        await query.edit_message_text(
            "🎁 *Create Giveaway Code*\n\n"
            "Format: `days|max_uses`\n\n"
            "Examples:\n`7|100`  = 7 days, 100 students\n`30|1`  = 30 days, 1 student\n\n"
            "Type /cancel to abort.", parse_mode="Markdown")
    elif data == "admin_list_giveaways":
        await list_giveaways(query)
    elif data == "admin_broadcast":
        context.user_data["waiting_for"] = "broadcast_msg"
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\nType your message to send to ALL users.\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_pending_receipts":
        await show_pending_receipts(query, context)
    elif data == "admin_edit_banks":
        if not is_super:
            await query.edit_message_text("⛔ No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "edit_bank_info"
        await query.edit_message_text(
            "🏦 *Edit Bank Account*\n\n"
            "Format: `bank_name|account_number|account_name`\n\n"
            "Example: `CBE|1000482304102|Yohanes Alemu`\n\n"
            "Type /cancel to abort.", parse_mode="Markdown")
    elif data == "admin_cancel_question":
        context.user_data.clear()
        await query.edit_message_text("❌ Cancelled.", reply_markup=admin_main_keyboard(role or "super"))

    # ── Subject picker (manual question) ──────────────────────────────────────
    elif data.startswith("aq_subject_"):
        subject = data.replace("aq_subject_", "")
        context.user_data["aq_subject"]       = subject
        context.user_data["aq_subject_label"] = subject.replace("_", " ").title()
        context.user_data["waiting_for"]      = "aq_question_text"
        await query.edit_message_text(
            "📝 Subject: " + context.user_data["aq_subject_label"] +
            "\n\nType the question text:\nType /cancel to abort.")

    elif data.startswith("aq_dept_"):
        dept = data.replace("aq_dept_", "")
        exam_type = context.user_data.get("aq_exam_type", "exit")
        has_upload = bool(context.user_data.get("parsed_questions"))
        if has_upload:
            context.user_data["upload_stream"] = dept
            subjects = await get_subjects(exam_type, dept)
            if subjects:
                await query.edit_message_text(
                    "📋 Choose subject for " + dept.replace("_", " ").title() + ":",
                    reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
            else:
                context.user_data["upload_subject"] = dept
                parsed = context.user_data.get("parsed_questions", [])
                await query.edit_message_text(
                    "✅ Ready to save " + str(len(parsed)) + " questions\n"
                    "Department: " + dept.replace("_", " ").title() + "\n"
                    "Exam: " + exam_type.title() + "\n\nConfirm?",
                    reply_markup=admin_confirm_keyboard())
        else:
            context.user_data["aq_stream"]        = dept
            context.user_data["aq_subject"]       = dept
            context.user_data["aq_subject_label"] = dept.replace("_", " ").title()
            context.user_data["waiting_for"]      = "aq_question_text"
            await query.edit_message_text(
                "📝 Department: *" + dept.replace("_", " ").title() + "*\n\nType the question text:\nType /cancel to abort.",
                parse_mode="Markdown")

    elif data.startswith("edit_q_field_"):
        field = data.replace("edit_q_field_", "")
        context.user_data["edit_field"]  = field
        context.user_data["waiting_for"] = "edit_q_value"
        labels = {
            "question_text": "question text", "option_a": "Option A",
            "option_b": "Option B", "option_c": "Option C", "option_d": "Option D",
            "correct_answer": "correct answer (A/B/C/D)",
            "explanation": "explanation", "reference": "reference",
            "year": "year (number or type none)",
        }
        await query.edit_message_text("✏️ Send the new " + labels.get(field, field) + ":")

    elif data.startswith("rcpt_ok_"):
        await approve_receipt(query, context, data)
    elif data.startswith("rcpt_no_"):
        await reject_receipt(query, context, data)


# ─────────────────────── Upload handler (upload flow callbacks) ──────────────

async def admin_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid  = query.from_user.id
    if not await is_any_admin(uid):
        return
    has_upload = bool(context.user_data.get("parsed_questions"))

    if data == "aq_type_entrance":
        context.user_data["aq_exam_type"] = "entrance"
        if has_upload: context.user_data["upload_exam_type"] = "entrance"
        await query.edit_message_text("📚 Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_type_exit":
        context.user_data["aq_exam_type"] = "exit"
        if has_upload: context.user_data["upload_exam_type"] = "exit"
        depts = await get_depts("exit")
        if not depts:
            await query.edit_message_text(
                "⚠️ No Exit Exam departments found.\n\n"
                "Add departments first:\nAdmin Panel → Manage Departments\n\n"
                "Format: `exit|key|name|emoji`\nExample: `exit|nursing|Nursing|🩺`",
                parse_mode="Markdown", reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("🏛️ Choose department:", reply_markup=build_dept_keyboard(depts))

    elif data == "aq_type_coc":
        context.user_data["aq_exam_type"] = "coc"
        if has_upload: context.user_data["upload_exam_type"] = "coc"
        depts = await get_depts("coc")
        if not depts:
            await query.edit_message_text(
                "⚠️ No CoC departments found.\n\n"
                "Add departments first via Manage Departments.\n"
                "Format: `coc|key|name|emoji`\nExample: `coc|coc_electrical|Electrical|⚡`",
                parse_mode="Markdown", reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("📋 Choose CoC department:", reply_markup=build_dept_keyboard(depts))

    elif data == "aq_type_driving":
        context.user_data["aq_exam_type"] = "driving"
        context.user_data["aq_stream"]    = "general"
        if has_upload:
            context.user_data["upload_exam_type"] = "driving"
            context.user_data["upload_stream"]    = "general"
        subjects = await get_subjects("driving", "general")
        if not subjects:
            await query.edit_message_text(
                "⚠️ No Driving subjects found.\n\n"
                "Add subjects first via Manage Subjects.\n"
                "Format: `driving|general|key|name|emoji`",
                parse_mode="Markdown", reply_markup=admin_back_keyboard())
            return
        prefix = "upload_subject_" if has_upload else "aq_subject_"
        await query.edit_message_text("🚗 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix=prefix))

    elif data == "aq_type_remedial":
        context.user_data["aq_exam_type"] = "remedial"
        if has_upload: context.user_data["upload_exam_type"] = "remedial"
        await query.edit_message_text("📝 Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_type_mock":
        context.user_data["aq_exam_type"] = "mock"
        if has_upload: context.user_data["upload_exam_type"] = "mock"
        exit_depts = await get_depts("exit")
        coc_depts  = await get_depts("coc")
        buttons = []
        if exit_depts:
            buttons.append([InlineKeyboardButton("── 🎓 Exit Exam Departments ──", callback_data="aq_mock_stream_noop")])
            row = []
            for d in exit_depts:
                row.append(InlineKeyboardButton(f"{d['emoji']} {d['dept_name']}", callback_data=f"aq_mock_dept_{d['dept_key']}"))
                if len(row) == 2: buttons.append(row); row = []
            if row: buttons.append(row)
        if coc_depts:
            buttons.append([InlineKeyboardButton("── 🏅 CoC Departments ──", callback_data="aq_mock_stream_noop")])
            row = []
            for d in coc_depts:
                row.append(InlineKeyboardButton(f"{d['emoji']} {d['dept_name']}", callback_data=f"aq_mock_dept_{d['dept_key']}"))
                if len(row) == 2: buttons.append(row); row = []
            if row: buttons.append(row)
        buttons.append([InlineKeyboardButton("📋 General / Mixed Subjects", callback_data="aq_mock_dept_general")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
        await query.edit_message_text(
            "📋 *Model / Mock Exam Upload*\n\nChoose a department:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "aq_mock_stream_noop":
        await query.answer("Select a department below.", show_alert=False)
        return

    elif data.startswith("aq_mock_stream_"):
        stream     = data.replace("aq_mock_stream_", "")
        has_upload = bool(context.user_data.get("parsed_questions"))
        context.user_data["aq_stream"] = stream
        if has_upload: context.user_data["upload_stream"] = stream
        subjects = await get_subjects("mock", stream)
        if not subjects:
            await query.edit_message_text(
                f"⚠️ No mock subjects found for stream *{stream}*.\n\nAdd subjects first.",
                parse_mode="Markdown", reply_markup=admin_back_keyboard())
            return
        prefix = "upload_subject_" if has_upload else "aq_subject_"
        await query.edit_message_text("📋 Mock — Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix=prefix))

    elif data.startswith("aq_mock_dept_"):
        dept_key   = data.replace("aq_mock_dept_", "")
        has_upload = bool(context.user_data.get("parsed_questions"))
        context.user_data["aq_stream"] = dept_key
        if has_upload: context.user_data["upload_stream"] = dept_key

        if dept_key == "general":
            dept_label = "General / Mixed"
        else:
            async with aiosqlite.connect(DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row
                cur      = await db.execute("SELECT dept_name, emoji FROM departments WHERE dept_key=?", (dept_key,))
                dept_row = await cur.fetchone()
            dept_label = f"{dept_row['emoji']} {dept_row['dept_name']}" if dept_row else dept_key.replace("_", " ").title()

        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur        = await db.execute(
                "SELECT * FROM subjects WHERE exam_type='mock' AND stream=? ORDER BY subject_name", (dept_key,))
            mock_subjs = [dict(r) for r in await cur.fetchall()]
            cur2       = await db.execute(
                "SELECT * FROM subjects WHERE stream=? AND exam_type IN ('exit','coc') ORDER BY subject_name", (dept_key,))
            dept_subjs = [dict(r) for r in await cur2.fetchall()]

        combined   = mock_subjs[:]
        seen_names = {s["subject_name"] for s in mock_subjs}
        for s in dept_subjs:
            if s["subject_name"] not in seen_names:
                combined.append(s); seen_names.add(s["subject_name"])

        prefix = "upload_subject_" if has_upload else "aq_subject_"
        if not combined:
            if has_upload:
                context.user_data["upload_subject"] = dept_key
                parsed = context.user_data.get("parsed_questions", [])
                await query.edit_message_text(
                    f"✅ Ready to save *{len(parsed)} questions*\n\n"
                    f"📋 Department: *{dept_label}*\n📚 Exam: Mock\n\nConfirm?",
                    parse_mode="Markdown", reply_markup=admin_confirm_keyboard())
            else:
                context.user_data["aq_subject"]       = dept_key
                context.user_data["aq_subject_label"] = dept_label
                context.user_data["waiting_for"]      = "aq_question_text"
                await query.edit_message_text(
                    f"📝 *Mock — {dept_label}*\n\nType the question text:\nType /cancel to abort.",
                    parse_mode="Markdown")
            return

        buttons = []
        row     = []
        for s in combined:
            row.append(InlineKeyboardButton(
                f"{s.get('emoji','📘')} {s['subject_name']}",
                callback_data=f"{prefix}{s['subject_key']}"))
            if len(row) == 2: buttons.append(row); row = []
        if row: buttons.append(row)
        buttons.append([InlineKeyboardButton(f"📂 All of {dept_label}", callback_data=f"{prefix}{dept_key}")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="aq_type_mock")])
        await query.edit_message_text(
            f"📋 *Mock Upload — {dept_label}*\n\nChoose subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "aq_stream_natural":
        exam_type  = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "natural"
        subjects   = await get_subjects(exam_type, "natural")
        if has_upload:
            context.user_data["upload_stream"] = "natural"
            await query.edit_message_text("🔬 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text("🔬 Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data == "aq_stream_social":
        exam_type  = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "social"
        subjects   = await get_subjects(exam_type, "social")
        if has_upload:
            context.user_data["upload_stream"] = "social"
            await query.edit_message_text("📚 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text("📚 Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data.startswith("upload_subject_"):
        subject   = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed    = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream    = context.user_data.get("upload_stream", "natural")
        # Ask for year before confirming
        context.user_data["waiting_for"] = "upload_year"
        await query.edit_message_text(
            "📅 *Enter the exam year for these " + str(len(parsed)) + " questions*\n\n"
            "Examples: `2015`, `2016`, `2017` (Ethiopian Calendar)\n"
            "Or type `skip` to save without a year.\n\n"
            "Subject: *" + subject.replace("_", " ").title() + "*\n"
            "Exam: *" + exam_type.title() + " / " + stream + "*",
            parse_mode="Markdown"
        )

    elif data == "aq_confirm_save":
        if context.user_data.get("parsed_questions"):
            await save_bulk_questions(query, context)
        else:
            await save_question_from_context(query, context)


# ─────────────────────── Text handler ────────────────────────────────────────

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_any_admin(uid):
        return
    waiting = context.user_data.get("waiting_for")
    if not waiting:
        return
    text = update.message.text.strip()
    role = await get_admin_role(uid)

    if text == "/cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled.", reply_markup=admin_main_keyboard(role or "super"))
        return

    simple_steps = {
        "aq_question_text": ("aq_option_a", "✅ OK. Type *Option A*:"),
        "aq_option_a":      ("aq_option_b", "✅ OK. Type *Option B*:"),
        "aq_option_b":      ("aq_option_c", "✅ OK. Type *Option C*:"),
        "aq_option_c":      ("aq_option_d", "✅ OK. Type *Option D*:"),
    }

    if waiting in simple_steps:
        context.user_data[waiting] = text
        nxt, msg = simple_steps[waiting]
        context.user_data["waiting_for"] = nxt
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif waiting == "aq_option_d":
        context.user_data["aq_option_d"]   = text
        context.user_data["waiting_for"]   = "aq_correct_answer"
        await update.message.reply_text("✅ OK. Correct answer: *A*, *B*, *C*, or *D*?", parse_mode="Markdown")

    elif waiting == "aq_correct_answer":
        if text.upper() not in ["A", "B", "C", "D"]:
            await update.message.reply_text("⚠️ Must be A, B, C, or D. Try again:")
            return
        context.user_data["aq_correct_answer"] = text.upper()
        context.user_data["waiting_for"]       = "aq_explanation"
        await update.message.reply_text("✅ OK. Type the *explanation*:", parse_mode="Markdown")

    elif waiting == "aq_explanation":
        context.user_data["aq_explanation"] = text
        context.user_data["waiting_for"]    = "aq_reference"
        await update.message.reply_text("✅ OK. Type *reference* or type `none`:", parse_mode="Markdown")

    elif waiting == "aq_reference":
        context.user_data["aq_reference"]  = "" if text.lower() == "none" else text
        context.user_data["waiting_for"]   = "aq_year"
        await update.message.reply_text("✅ OK. Type *exam year* (e.g. 2023) or `none`:", parse_mode="Markdown")

    elif waiting == "upload_year":
        # Year for bulk question upload
        if text.lower() == "skip":
            context.user_data["upload_year"] = None
        else:
            try:
                yr = int(text)
                if not (1900 <= yr <= 2100):
                    await update.message.reply_text(
                        "⚠️ Please enter a valid year (e.g. `2015`) or type `skip`.",
                        parse_mode="Markdown")
                    return
                context.user_data["upload_year"] = yr
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Not a valid year. Enter a number like `2016` or type `skip`.",
                    parse_mode="Markdown")
                return
        context.user_data["waiting_for"] = None
        # Show confirmation
        parsed    = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream    = context.user_data.get("upload_stream", "natural")
        subject   = context.user_data.get("upload_subject", "")
        yr_label  = str(context.user_data.get("upload_year") or "No year")
        await update.message.reply_text(
            "✅ *Ready to save!*\n\n"
            "Questions: *" + str(len(parsed)) + "*\n"
            "Exam: *" + exam_type.title() + "*\n"
            "Stream / Dept: *" + stream + "*\n"
            "Subject: *" + subject.replace("_", " ").title() + "*\n"
            "Year: *" + yr_label + "*\n\n"
            "Confirm save?",
            parse_mode="Markdown",
            reply_markup=admin_confirm_keyboard())

    elif waiting == "aq_year":
        try:
            context.user_data["aq_year"] = int(text) if text.lower() != "none" else None
        except ValueError:
            context.user_data["aq_year"] = None
        context.user_data["waiting_for"] = None
        d = context.user_data
        preview = (
            "📋 *QUESTION PREVIEW*\n\n"
            "Subject: " + str(d.get("aq_subject_label")) + "\n"
            "Exam: " + str(d.get("aq_exam_type", "")).title() + "\n"
            "Stream: " + str(d.get("aq_stream", "")).title() + "\n"
            "Year: " + str(d.get("aq_year") or "N/A") + "\n\n"
            "Q: " + str(d.get("aq_question_text")) + "\n\n"
            "A) " + str(d.get("aq_option_a")) + "\n"
            "B) " + str(d.get("aq_option_b")) + "\n"
            "C) " + str(d.get("aq_option_c")) + "\n"
            "D) " + str(d.get("aq_option_d")) + "\n\n"
            "✅ Answer: *" + str(d.get("aq_correct_answer")) + "*\n"
            "💡 Explanation: " + str(d.get("aq_explanation")) + "\n"
            "📖 Reference: " + str(d.get("aq_reference") or "N/A")
        )
        await update.message.reply_text(preview, parse_mode="Markdown", reply_markup=admin_confirm_keyboard())

    elif waiting == "grant_sub_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 4:
            await update.message.reply_text(
                "⚠️ Wrong format.\nUse: `telegram_id|days|exam_type|stream_or_dept`\n\n"
                "Example: `123456789|30|entrance|natural`", parse_mode="Markdown")
            return
        try:
            tid  = int(parts[0])
            days = int(parts[1])
        except ValueError:
            await update.message.reply_text("⚠️ ID and days must be numbers.")
            return
        exam_type      = parts[2].strip()
        stream_or_dept = parts[3].strip()
        stream = stream_or_dept if exam_type in ("entrance", "remedial", "driving") else ""
        dept   = stream_or_dept if exam_type in ("exit", "coc") else ""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("⚠️ User not found. They must /start the bot first.")
                context.user_data.clear()
                return
            await db.execute(
                "UPDATE users SET is_subscribed=1, "
                "subscription_expiry=datetime('now','+" + str(days) + " days'), "
                "subscribed_exam_type=?, subscribed_stream=?, subscribed_dept=? "
                "WHERE telegram_id=?",
                (exam_type, stream, dept, tid))
            await db.commit()
        context.user_data.clear()
        label = exam_type.title()
        if stream: label += " / " + stream.title()
        if dept:   label += " / " + dept.replace("_", " ").title()
        await update.message.reply_text(
            "✅ *Subscription granted!*\n\nUser: " + str(row[0] or tid) +
            "\nAccess: " + label + "\nDuration: " + str(days) + " days",
            parse_mode="Markdown", reply_markup=admin_back_keyboard())
        try:
            await context.bot.send_message(
                chat_id=tid,
                text="🎉 Your subscription is activated!\n\nAccess: " + label +
                     "\nDuration: " + str(days) + " days\n\nStart practicing now! Send /start")
        except Exception:
            pass

    elif waiting == "broadcast_msg":
        context.user_data.clear()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur   = await db.execute("SELECT telegram_id FROM users")
            users = await cur.fetchall()
        sent = failed = 0
        for (u,) in users:
            try:
                await context.bot.send_message(chat_id=u, text=text)
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            "📢 *Broadcast done.*\n\nSent: " + str(sent) + "\nFailed: " + str(failed),
            parse_mode="Markdown", reply_markup=admin_back_keyboard())

    elif waiting == "new_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) not in [4, 5]:
            await update.message.reply_text(
                "⚠️ Format: `exam_type|stream|key|name|emoji`\n\nExample: `entrance|natural|physics|Physics|⚡`",
                parse_mode="Markdown")
            return
        exam_type_s, stream_s, key_s, name_s = parts[0], parts[1], parts[2], parts[3]
        emoji_s = parts[4] if len(parts) == 5 else "📘"
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO subjects (exam_type,stream,subject_key,subject_name,emoji) VALUES (?,?,?,?,?)",
                    (exam_type_s, stream_s, key_s, name_s, emoji_s))
                await db.commit()
                await update.message.reply_text("✅ Subject added: *" + name_s + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text("⚠️ Error: " + str(e), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Format: `old_key|new_name|new_emoji`", parse_mode="Markdown")
            return
        old_key, new_name = parts[0], parts[1]
        new_emoji = parts[2] if len(parts) >= 3 else None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            if not await (await db.execute("SELECT id FROM subjects WHERE subject_key=?", (old_key,))).fetchone():
                await update.message.reply_text("⚠️ Key not found: " + old_key)
                context.user_data.clear()
                return
            if new_emoji:
                await db.execute("UPDATE subjects SET subject_name=?, emoji=? WHERE subject_key=?", (new_name, new_emoji, old_key))
            else:
                await db.execute("UPDATE subjects SET subject_name=? WHERE subject_key=?", (new_name, old_key))
            await db.commit()
        await update.message.reply_text("✅ Subject updated: *" + new_name + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_subject_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            row = await (await db.execute("SELECT subject_name FROM subjects WHERE subject_key=?", (text,))).fetchone()
            if not row:
                await update.message.reply_text("⚠️ Key not found: " + text)
                context.user_data.clear()
                return
            await db.execute("DELETE FROM subjects WHERE subject_key=?", (text,))
            await db.commit()
        await update.message.reply_text("✅ Subject deleted: *" + row[0] + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "new_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) not in [3, 4]:
            await update.message.reply_text(
                "⚠️ Format: `exam_type|key|name|emoji`\n\nExample: `coc|coc_welding|Welding|🔧`",
                parse_mode="Markdown")
            return
        et, k, n = parts[0], parts[1], parts[2]
        em = parts[3] if len(parts) == 4 else "🏛️"
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute("INSERT INTO departments (exam_type,dept_key,dept_name,emoji) VALUES (?,?,?,?)", (et, k, n, em))
                await db.commit()
                await update.message.reply_text("✅ Department added: *" + n + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text("⚠️ Error: " + str(e), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            await update.message.reply_text("⚠️ Format: `old_key|new_name|new_emoji`", parse_mode="Markdown")
            return
        old_key, new_name = parts[0], parts[1]
        new_emoji = parts[2] if len(parts) >= 3 else None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            if not await (await db.execute("SELECT id FROM departments WHERE dept_key=?", (old_key,))).fetchone():
                await update.message.reply_text("⚠️ Key not found: " + old_key)
                context.user_data.clear()
                return
            if new_emoji:
                await db.execute("UPDATE departments SET dept_name=?, emoji=? WHERE dept_key=?", (new_name, new_emoji, old_key))
            else:
                await db.execute("UPDATE departments SET dept_name=? WHERE dept_key=?", (new_name, old_key))
            await db.commit()
        await update.message.reply_text("✅ Department updated: *" + new_name + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_dept_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            row = await (await db.execute("SELECT dept_name FROM departments WHERE dept_key=?", (text,))).fetchone()
            if not row:
                await update.message.reply_text("⚠️ Key not found: " + text)
                context.user_data.clear()
                return
            await db.execute("DELETE FROM departments WHERE dept_key=?", (text,))
            await db.commit()
        await update.message.reply_text("✅ Department deleted: *" + row[0] + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "add_subadmin":
        try:   tid = int(text)
        except ValueError:
            await update.message.reply_text("⚠️ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            row = await (await db.execute("SELECT full_name FROM users WHERE telegram_id=?", (tid,))).fetchone()
            if not row:
                await update.message.reply_text("⚠️ User not found. They must /start first.")
                context.user_data.clear()
                return
            try:
                await db.execute(
                    "INSERT INTO admin_users (telegram_id,full_name,role,added_by) VALUES (?,?,'sub',?)",
                    (tid, row[0], uid))
                await db.commit()
                await update.message.reply_text("✅ Sub admin added: *" + str(row[0] or tid) + "*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
                try:
                    await context.bot.send_message(chat_id=tid, text="🛡️ You have been added as a Sub Admin.\nUse /admin to access the admin panel.")
                except Exception:
                    pass
            except Exception as e:
                await update.message.reply_text("⚠️ Error: " + str(e))
        context.user_data.clear()

    elif waiting == "remove_admin":
        try:   tid = int(text)
        except ValueError:
            await update.message.reply_text("⚠️ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM admin_users WHERE telegram_id=?", (tid,))
            await db.commit()
        await update.message.reply_text("✅ Admin removed: " + str(tid), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_question_id":
        try:   qid = int(text)
        except ValueError:
            await update.message.reply_text("⚠️ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            row = await (await db.execute("SELECT * FROM questions WHERE id=?", (qid,))).fetchone()
        if not row:
            await update.message.reply_text("⚠️ Question ID " + str(qid) + " not found.")
            context.user_data.clear()
            return
        q = dict(row)
        context.user_data["edit_question_id"] = qid
        context.user_data["waiting_for"]      = None
        preview = (
            "ID:" + str(q["id"]) + "  Subject:" + str(q["subject"]) + "  Year:" + str(q.get("year") or "N/A") + "\n\n"
            "Q: " + str(q["question_text"]) + "\n\n"
            "A) " + str(q["option_a"]) + "\nB) " + str(q["option_b"]) + "\n"
            "C) " + str(q["option_c"]) + "\nD) " + str(q["option_d"]) + "\n\n"
            "Answer: " + str(q["correct_answer"])
        )
        edit_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Edit Question", callback_data="edit_q_field_question_text")],
            [InlineKeyboardButton("Edit A", callback_data="edit_q_field_option_a"),
             InlineKeyboardButton("Edit B", callback_data="edit_q_field_option_b")],
            [InlineKeyboardButton("Edit C", callback_data="edit_q_field_option_c"),
             InlineKeyboardButton("Edit D", callback_data="edit_q_field_option_d")],
            [InlineKeyboardButton("Edit Answer", callback_data="edit_q_field_correct_answer")],
            [InlineKeyboardButton("Edit Explanation", callback_data="edit_q_field_explanation")],
            [InlineKeyboardButton("Edit Reference", callback_data="edit_q_field_reference")],
            [InlineKeyboardButton("Edit Year", callback_data="edit_q_field_year")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
        ])
        await update.message.reply_text(preview, reply_markup=edit_kb)

    elif waiting == "edit_q_value":
        qid   = context.user_data.get("edit_question_id")
        field = context.user_data.get("edit_field")
        if not qid or not field:
            await update.message.reply_text("⚠️ Session expired.")
            context.user_data.clear()
            return
        value = text
        if field == "correct_answer":
            value = text.upper()
            if value not in ["A", "B", "C", "D"]:
                await update.message.reply_text("⚠️ Must be A, B, C, or D.")
                return
        if field == "year":
            try:   value = int(text) if text.lower() != "none" else None
            except ValueError: value = None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("UPDATE questions SET " + field + "=? WHERE id=?", (value, qid))
            await db.commit()
        context.user_data["waiting_for"] = None
        await update.message.reply_text("✅ Question " + str(qid) + " updated!", reply_markup=admin_back_keyboard())

    elif waiting == "delete_question_id":
        try:   qid = int(text)
        except ValueError:
            await update.message.reply_text("⚠️ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            row = await (await db.execute("SELECT subject FROM questions WHERE id=?", (qid,))).fetchone()
            if not row:
                await update.message.reply_text("⚠️ Not found: " + str(qid))
                context.user_data.clear()
                return
            await db.execute("DELETE FROM questions WHERE id=?", (qid,))
            await db.commit()
        await update.message.reply_text("✅ Question " + str(qid) + " deleted.", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    # ── Bulk Delete Confirmations ─────────────────────────────────────────────
    elif waiting == "bd_confirm_type":
        if text.strip() != "YES DELETE":
            await update.message.reply_text("❌ Cancelled. Type exactly `YES DELETE`.", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            context.user_data.clear()
            return
        exam_type = context.user_data.get("bd_exam_type", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("DELETE FROM questions WHERE exam_type=?", (exam_type,))
            await db.commit()
            deleted = cur.rowcount
        await update.message.reply_text(f"✅ Deleted *{deleted} questions* for type *{exam_type.title()}*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "bd_confirm_subject":
        if text.strip() != "YES DELETE":
            await update.message.reply_text("❌ Cancelled. Type exactly `YES DELETE`.", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            context.user_data.clear()
            return
        subj = context.user_data.get("bd_subject", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("DELETE FROM questions WHERE subject=?", (subj,))
            await db.commit()
            deleted = cur.rowcount
        await update.message.reply_text(f"✅ Deleted *{deleted} questions* for subject *{subj.replace('_',' ').title()}*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "bd_confirm_year":
        if text.strip() != "YES DELETE":
            await update.message.reply_text("❌ Cancelled. Type exactly `YES DELETE`.", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            context.user_data.clear()
            return
        yr = context.user_data.get("bd_year", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("DELETE FROM questions WHERE year=?", (yr,))
            await db.commit()
            deleted = cur.rowcount
        await update.message.reply_text(f"✅ Deleted *{deleted} questions* for year *{yr}*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "bd_confirm_subject_year":
        if text.strip() != "YES DELETE":
            await update.message.reply_text("❌ Cancelled. Type exactly `YES DELETE`.", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            context.user_data.clear()
            return
        subj = context.user_data.get("bd_subject", "")
        yr   = context.user_data.get("bd_year", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("DELETE FROM questions WHERE subject=? AND year=?", (subj, yr))
            await db.commit()
            deleted = cur.rowcount
        await update.message.reply_text(f"✅ Deleted *{deleted} questions* for *{subj.replace('_',' ').title()}* / *{yr}*", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "bd_confirm_all":
        if text.strip() != "YES DELETE ALL":
            await update.message.reply_text("❌ Cancelled. Type exactly `YES DELETE ALL`.", parse_mode="Markdown", reply_markup=admin_back_keyboard())
            context.user_data.clear()
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("DELETE FROM questions")
            await db.commit()
            deleted = cur.rowcount
        await update.message.reply_text(f"☢️ Deleted ALL *{deleted} questions* from the database.", parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "giveaway_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("⚠️ Format: `days|max_uses`\n\nExample: `7|100`", parse_mode="Markdown")
            return
        try:   days, max_uses = int(parts[0]), int(parts[1])
        except ValueError:
            await update.message.reply_text("⚠️ Both must be numbers.")
            return
        code = gen_code()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO giveaway_codes (code,duration_days,max_uses,created_by) VALUES (?,?,?,?)",
                (code, days, max_uses, uid))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text(
            "🎁 *Giveaway Code Created!*\n\nCode: `" + code + "`\nDuration: " + str(days) +
            " days\nMax Uses: " + str(max_uses) + "\n\nStudents redeem with: `/redeem " + code + "`",
            parse_mode="Markdown", reply_markup=admin_back_keyboard())

    elif waiting == "edit_bank_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text(
                "⚠️ Format: `bank_name|account_number|account_holder`\n\n"
                "Example: `CBE|1000482304102|Yohanes Alemu`",
                parse_mode="Markdown")
            return
        bank_name, acc_num, acc_holder = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Try insert; if bank already exists update it
            existing = await (await db.execute(
                "SELECT id FROM bank_accounts WHERE bank_name=?", (bank_name,))).fetchone()
            if existing:
                await db.execute(
                    "UPDATE bank_accounts SET account_number=?, account_holder=?, is_active=1 "
                    "WHERE bank_name=?",
                    (acc_num, acc_holder, bank_name))
            else:
                await db.execute(
                    "INSERT INTO bank_accounts (bank_name, account_number, account_holder, is_active) "
                    "VALUES (?,?,?,1)",
                    (bank_name, acc_num, acc_holder))
            await db.commit()
        await update.message.reply_text(
            "✅ *Bank saved!*\n\n"
            "🏦 " + bank_name + "\n"
            "Account: `" + acc_num + "`\n"
            "Holder: " + acc_holder,
            parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()


# ─────────────────────── File handler ────────────────────────────────────────

async def admin_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_any_admin(uid):
        return

    # ── Route backup restore file ─────────────────────────────────────────────
    if context.user_data.get("waiting_for") == "backup_restore_file":
        from app.handlers.backup import backup_file_handler
        await backup_file_handler(update, context)
        return

    # ── Normal question file upload ───────────────────────────────────────────
    if context.user_data.get("waiting_for") != "question_file":
        return
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".txt"):
        await update.message.reply_text("⚠️ Please send a `.txt` file only.", parse_mode="Markdown")
        return
    await update.message.reply_text("⏳ Reading file...")
    file    = await context.bot.get_file(doc.file_id)
    content = bytes(await file.download_as_bytearray()).decode("utf-8", errors="ignore")
    parsed  = parse_questions_from_text(content)
    if not parsed:
        await update.message.reply_text(
            "⚠️ *No valid questions found.*\n\nCheck the format:\n\n"
            "```\nQ: Question text\nA) ...\nB) ...\nC) ...\nD) ...\nAnswer: B\nExplanation: ...\n```\n\n"
            "Separate questions with a blank line.",
            parse_mode="Markdown")
        return
    context.user_data["parsed_questions"] = parsed
    context.user_data["waiting_for"]      = "upload_exam_type"
    await update.message.reply_text(
        "✅ *Found " + str(len(parsed)) + " questions!*\n\nStep 1: Choose exam type:",
        parse_mode="Markdown",
        reply_markup=admin_exam_type_keyboard())


# ─────────────────────── Save helpers ────────────────────────────────────────

async def save_bulk_questions(query, context):
    parsed    = context.user_data.get("parsed_questions", [])
    exam_type = context.user_data.get("upload_exam_type", "entrance")
    stream    = context.user_data.get("upload_stream", "natural")
    subject   = context.user_data.get("upload_subject", "")
    year      = context.user_data.get("upload_year")  # int or None — set by upload_year handler

    if not parsed:
        await query.edit_message_text("⚠️ No questions to save. Start upload again.", reply_markup=admin_back_keyboard())
        context.user_data.clear()
        return

    saved = failed = 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for q in parsed:
            try:
                await db.execute(
                    "INSERT INTO questions "
                    "(exam_type,stream,subject,question_text,option_a,option_b,option_c,option_d,"
                    "correct_answer,explanation,reference,year) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exam_type, stream, subject or q.get("subject", ""),
                     q["question_text"], q["option_a"], q["option_b"],
                     q["option_c"], q["option_d"], q["correct_answer"],
                     q.get("explanation", ""), q.get("reference", ""),
                     year if year is not None else q.get("year")))
                saved += 1
            except Exception as e:
                logger.error(f"save_bulk_questions error: {e}")
                failed += 1
        await db.commit()

    yr_label = str(year) if year else "No year"
    context.user_data.clear()
    await query.edit_message_text(
        f"✅ *Upload Complete!*\n\n"
        f"✅ Saved: *{saved}*\n"
        f"❌ Failed: *{failed}*\n\n"
        f"Exam: *{exam_type.title()}*\n"
        f"Stream / Dept: *{stream}*\n"
        f"Subject: *{subject.replace(chr(95),' ').title()}*\n"
        f"Year: *{yr_label}*",
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def save_question_from_context(query, context):
    d         = context.user_data
    exam_type = d.get("aq_exam_type", "entrance")
    stream    = d.get("aq_stream", "natural")
    subject   = d.get("aq_subject", "")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO questions "
            "(exam_type,stream,subject,question_text,option_a,option_b,option_c,option_d,"
            "correct_answer,explanation,reference,year) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (exam_type, stream, subject,
             d.get("aq_question_text"), d.get("aq_option_a"), d.get("aq_option_b"),
             d.get("aq_option_c"), d.get("aq_option_d"), d.get("aq_correct_answer"),
             d.get("aq_explanation", ""), d.get("aq_reference", ""), d.get("aq_year")))
        await db.commit()
    context.user_data.clear()
    await query.edit_message_text("✅ *Question saved!*", parse_mode="Markdown", reply_markup=admin_back_keyboard())


# ─────────────────────── View helpers ────────────────────────────────────────

async def show_questions(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur  = await db.execute("SELECT exam_type, COUNT(*) FROM questions GROUP BY exam_type ORDER BY exam_type")
        rows = await cur.fetchall()
        total = sum(r[1] for r in rows)
    if not rows:
        await query.edit_message_text("❓ No questions in DB yet.", reply_markup=admin_back_keyboard())
        return
    buttons = [[InlineKeyboardButton(
        f"📂 {et.title()} ({cnt})", callback_data=f"vq_type_{et}"
    )] for et, cnt in rows]
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    await query.edit_message_text(
        f"❓ *Questions* — Total: *{total}*\n\nChoose exam type:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons))


async def show_questions_by_type(query, exam_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if exam_type in ("entrance", "remedial"):
            cur  = await db.execute(
                "SELECT stream, COUNT(*) FROM questions WHERE exam_type=? GROUP BY stream", (exam_type,))
            rows = await cur.fetchall()
            buttons = [[InlineKeyboardButton(
                f"{'🔬' if s == 'natural' else '📚'} {s.title()} ({c})",
                callback_data=f"vq_stream_{exam_type}_{s}"
            )] for s, c in rows]
        elif exam_type in ("exit", "coc"):
            cur  = await db.execute(
                "SELECT stream, COUNT(*) FROM questions WHERE exam_type=? GROUP BY stream", (exam_type,))
            rows = await cur.fetchall()
            buttons = [[InlineKeyboardButton(
                f"🏛️ {s.replace('_',' ').title()} ({c})",
                callback_data=f"vq_dept_{exam_type}_{s}"
            )] for s, c in rows]
        else:
            await show_questions_list(query, exam_type, "general")
            return
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_view_questions")])
    await query.edit_message_text(
        f"📂 *{exam_type.title()} Exam* — choose stream/dept:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons))


async def show_questions_list(query, exam_type, stream, offset=0, page_size=10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = (await (await db.execute(
            "SELECT COUNT(*) FROM questions WHERE exam_type=? AND stream=?",
            (exam_type, stream))).fetchone())[0]
        cur  = await db.execute(
            "SELECT id, question_text, correct_answer, year FROM questions "
            "WHERE exam_type=? AND stream=? ORDER BY id LIMIT ? OFFSET ?",
            (exam_type, stream, page_size, offset))
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("No questions found.", reply_markup=admin_back_keyboard())
        return
    lines = [f"📋 *{exam_type.title()} / {stream.replace('_',' ').title()}* — {total} total\n"]
    for r in rows:
        qt = (r["question_text"] or "")[:50].replace("*", "").replace("_", "")
        yr = f" [{r['year']}]" if r.get("year") else ""
        lines.append(f"`ID:{r['id']}`{yr} ✅{r['correct_answer']} — {qt}…")
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"vq_page_{exam_type}_{stream}_{offset - page_size}"))
    if offset + page_size < total:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"vq_page_{exam_type}_{stream}_{offset + page_size}"))
    keyboard = []
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"vq_type_{exam_type}")])
    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard))


async def show_users(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        total     = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        subscribed= (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        cur       = await db.execute("SELECT * FROM users ORDER BY id DESC LIMIT 10")
        rows      = [dict(r) for r in await cur.fetchall()]
    lines = [f"👥 *Users*\n\nTotal: *{total}*  |  Subscribed: *{subscribed}*\n\n*Latest 10:*\n"]
    for r in rows:
        name = (r.get("full_name") or r.get("username") or "Unknown")[:20]
        sub  = "💎" if r.get("is_subscribed") else "🆓"
        lines.append(f"{sub} {name} `({r['telegram_id']})`")
    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def show_stats(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total_q = (await (await db.execute("SELECT COUNT(*) FROM questions")).fetchone())[0]
        total_u = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        total_s = (await (await db.execute("SELECT COUNT(*) FROM exam_sessions WHERE completed=1")).fetchone())[0]
        sub_u   = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        cur     = await db.execute(
            "SELECT exam_type, COUNT(*) FROM questions GROUP BY exam_type ORDER BY exam_type")
        type_counts = {r[0]: r[1] for r in await cur.fetchall()}
    type_lines = "\n".join(f"  • {et.title()}: {c}" for et, c in type_counts.items())
    await query.edit_message_text(
        f"📊 *Bot Statistics*\n\n"
        f"❓ Questions: *{total_q}*\n{type_lines}\n\n"
        f"👥 Total Users: *{total_u}*\n"
        f"💎 Subscribed: *{sub_u}*\n"
        f"📝 Exams taken: *{total_s}*",
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def list_admins(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute("SELECT * FROM admin_users ORDER BY role, id")
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("No sub admins added yet.", reply_markup=admin_back_keyboard())
        return
    lines = ["👮 *Admin List*\n"]
    for r in rows:
        name = r.get("full_name") or str(r["telegram_id"])
        lines.append(f"• {name} `({r['telegram_id']})` — {r['role']}")
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_subjects(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute("SELECT * FROM subjects ORDER BY exam_type, stream, subject_name")
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("No subjects yet.", reply_markup=admin_back_keyboard())
        return
    lines = [f"📚 *Subjects ({len(rows)} total)*\n"]
    for r in rows:
        lines.append(f"{r.get('emoji','📘')} `{r['subject_key']}` — {r['subject_name']} ({r['exam_type']}/{r['stream']})")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n… (truncated)"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_depts(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute("SELECT * FROM departments ORDER BY exam_type, dept_name")
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("No departments yet.", reply_markup=admin_back_keyboard())
        return
    lines = [f"🏛️ *Departments ({len(rows)} total)*\n"]
    for r in rows:
        lines.append(f"{r.get('emoji','🏛️')} `{r['dept_key']}` — {r['dept_name']} ({r['exam_type']})")
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_giveaways(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur  = await db.execute(
            "SELECT code, duration_days, max_uses, used_count FROM giveaway_codes ORDER BY id DESC LIMIT 20")
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("No giveaway codes yet.", reply_markup=admin_back_keyboard())
        return
    lines = ["🎁 *Active Giveaway Codes*\n"]
    for r in rows:
        lines.append(f"`{r['code']}` — {r['duration_days']}d | Used: {r['used_count']}/{r['max_uses']}")
    await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def show_pending_receipts(query, context):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT pr.*, u.full_name, u.username
               FROM payment_receipts pr
               LEFT JOIN users u ON pr.telegram_id = u.telegram_id
               WHERE pr.status = 'pending'
               ORDER BY pr.submitted_at DESC LIMIT 20""")
        rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        await query.edit_message_text(
            "✅ No pending receipts at this time.",
            reply_markup=admin_back_keyboard())
        return

    # Send each receipt as a new message so photos are visible
    for r in rows:
        exam_type = r.get("exam_type") or ""
        stream    = r.get("stream")    or ""
        dept      = r.get("dept")      or ""
        label     = exam_type.title()
        if stream: label += " / " + stream.title()
        if dept:   label += " / " + dept.replace("_", " ").title()

        full_name = r.get("full_name") or ""
        username  = ("@" + r["username"]) if r.get("username") else ""
        user_line = (full_name + " " + username).strip() or str(r["telegram_id"])

        caption = (
            f"🧾 *Payment Receipt #{r['id']}*\n\n"
            f"👤 {user_line}\n"
            f"🆔 `{r['telegram_id']}`\n"
            f"📚 Plan: *{label}*\n"
            f"🕐 Submitted: {str(r.get('submitted_at',''))[:16]}"
        )
        kb = receipt_action_keyboard(r["id"], r["telegram_id"], exam_type, stream, dept)
        try:
            if r.get("file_id"):
                await context.bot.send_photo(
                    chat_id=query.from_user.id,
                    photo=r["file_id"],
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=kb)
            else:
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=caption + "\n\n⚠️ No photo attached.",
                    parse_mode="Markdown",
                    reply_markup=kb)
        except Exception as e:
            logger.error(f"show_pending_receipts row {r['id']}: {e}")

    await query.edit_message_text(
        f"🧾 *{len(rows)} pending receipt(s)* shown above ☝️",
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def approve_receipt(query, context, data):
    # data format: rcpt_ok_{payment_id}|{telegram_id}|{exam_type}|{stream}|{dept}
    rest    = data[len("rcpt_ok_"):]
    parts   = rest.split("|")
    if len(parts) < 5:
        await query.edit_message_text("⚠️ Malformed receipt data.")
        return
    payment_id  = parts[0]
    telegram_id = int(parts[1])
    exam_type   = parts[2]
    stream      = parts[3]
    dept        = parts[4]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check it's still pending
        row = await (await db.execute(
            "SELECT status FROM payment_receipts WHERE id=?", (payment_id,))).fetchone()
        if not row:
            await query.edit_message_text("⚠️ Receipt not found.")
            return
        if row[0] != "pending":
            await query.edit_message_text(f"ℹ️ Already {row[0]}.")
            return

        # Grant 30-day subscription — also insert into multi-subscriptions table
        await db.execute(
            "UPDATE users SET is_subscribed=1, "
            "subscription_expiry=datetime('now','+30 days'), "
            "subscribed_exam_type=?, subscribed_stream=?, subscribed_dept=? "
            "WHERE telegram_id=?",
            (exam_type, stream, dept, telegram_id))
        await db.execute(
            "INSERT INTO subscriptions "
            "(telegram_id, exam_type, stream, dept, expiry_at, is_active) "
            "VALUES (?, ?, ?, ?, datetime('now','+30 days'), 1)",
            (telegram_id, exam_type, stream or None, dept or None))
        await db.execute(
            "UPDATE payment_receipts SET status='approved', reviewed_at=datetime('now') WHERE id=?",
            (payment_id,))
        await db.commit()

    label = exam_type.title()
    if stream: label += " / " + stream.title()
    if dept:   label += " / " + dept.replace("_", " ").title()

    await query.edit_message_text(
        f"✅ *Approved!*\n\nUser `{telegram_id}` subscribed to: *{label}*",
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=f"🎉 *Your subscription is approved!*\n\n"
                 f"✅ Access: *{label}*\n"
                 f"📅 Duration: *{days} days*\n\n"
                 f"Start practicing now! Send /start",
            parse_mode="Markdown")
    except Exception:
        pass


async def reject_receipt(query, context, data):
    # data format: rcpt_no_{payment_id}|{telegram_id}
    rest    = data[len("rcpt_no_"):]
    parts   = rest.split("|")
    if len(parts) < 2:
        await query.edit_message_text("⚠️ Malformed receipt data.")
        return
    payment_id  = parts[0]
    telegram_id = int(parts[1])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        row = await (await db.execute(
            "SELECT status FROM payment_receipts WHERE id=?", (payment_id,))).fetchone()
        if not row:
            await query.edit_message_text("⚠️ Receipt not found.")
            return
        if row[0] != "pending":
            await query.edit_message_text(f"ℹ️ Already {row[0]}.")
            return
        await db.execute(
            "UPDATE payment_receipts SET status='rejected', reviewed_at=datetime('now') WHERE id=?",
            (payment_id,))
        await db.commit()

    await query.edit_message_text(
        f"❌ *Receipt rejected.*\n\nUser `{telegram_id}` has been notified.",
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="❌ *Your payment receipt was rejected.*\n\n"
                 "Please resend a clear screenshot of your bank transfer.\n"
                 "Contact admin if you need help.",
            parse_mode="Markdown")
    except Exception:
        pass


# ─────────────────────── Bulk Delete main view ───────────────────────────────

async def show_bulk_delete_menu(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total      = (await (await db.execute("SELECT COUNT(*) FROM questions")).fetchone())[0]
        cur        = await db.execute("SELECT exam_type, COUNT(*) FROM questions GROUP BY exam_type ORDER BY exam_type")
        type_counts = {r[0]: r[1] for r in await cur.fetchall()}
    type_lines = "\n".join(f"  • {et.title()}: {cnt}" for et, cnt in type_counts.items()) or "  (no questions)"
    await query.edit_message_text(
        f"🗑️🗑️ *Bulk Delete Questions*\n\n"
        f"Total questions: *{total}*\n\nBy type:\n{type_lines}\n\n"
        "Choose a delete option:",
        parse_mode="Markdown",
        reply_markup=bulk_delete_main_keyboard())


# ─────────────────────── Referral Stats ──────────────────────────────────────

async def show_referral_stats(query, page: int = 0):
    page_size = 10
    offset    = page * page_size
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("""
            SELECT
                u.telegram_id, u.full_name, u.username,
                u.referral_count,
                COUNT(r.telegram_id)                            AS actual_referred,
                SUM(CASE WHEN r.is_subscribed=1 THEN 1 ELSE 0 END) AS referred_subscribed
            FROM users u
            LEFT JOIN users r ON r.referred_by = u.referral_code
            WHERE u.referral_count > 0
               OR EXISTS (SELECT 1 FROM users r2 WHERE r2.referred_by = u.referral_code)
            GROUP BY u.telegram_id
            ORDER BY actual_referred DESC, referred_subscribed DESC
            LIMIT ? OFFSET ?
        """, (page_size + 1, offset))
        rows = [dict(r) for r in await cur.fetchall()]

        total_users     = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        total_sub       = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        total_referrers = (await (await db.execute(
            "SELECT COUNT(DISTINCT referred_by) FROM users WHERE referred_by IS NOT NULL")).fetchone())[0]

    has_more = len(rows) > page_size
    rows     = rows[:page_size]

    if not rows:
        await query.edit_message_text(
            f"🔗 *Referral Stats*\n\n"
            f"👥 Total users: *{total_users}*  |  💎 Subscribed: *{total_sub}*\n\n"
            "No referrals recorded yet.",
            parse_mode="Markdown",
            reply_markup=admin_back_keyboard())
        return

    medals = ["🥇", "🥈", "🥉"]
    lines  = []
    for i, r in enumerate(rows):
        rank       = medals[i] if i < 3 else f"{offset + i + 1}."
        name       = (r.get("full_name") or r.get("username") or "Unknown")[:20]
        referred   = r.get("actual_referred") or 0
        subscribed = r.get("referred_subscribed") or 0
        lines.append(f"{rank} *{name}*\n   👥 Referred: {referred}  |  💎 Subscribed: {subscribed}")

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"admin_ref_page_{page - 1}"))
    if has_more:
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_ref_page_{page + 1}"))

    keyboard = []
    if nav_buttons: keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")])

    await query.edit_message_text(
        f"🔗 *Referral Stats*\n\n"
        f"👥 Total users: *{total_users}*  |  💎 Subscribed: *{total_sub}*\n"
        f"🔗 Active referrers: *{total_referrers}*\n\n"
        + "\n\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard))
