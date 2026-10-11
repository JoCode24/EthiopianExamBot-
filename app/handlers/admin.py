from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import (
    admin_main_keyboard, admin_back_keyboard, admin_confirm_keyboard,
    admin_exam_type_keyboard, admin_stream_keyboard,
    build_subject_keyboard, build_dept_keyboard,
    manage_subjects_keyboard, manage_depts_keyboard,
    manage_admins_keyboard, giveaway_keyboard, receipt_action_keyboard,
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


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    if not await is_any_admin(uid):
        await query.edit_message_text("⛔ Unauthorized.")
        return
    role = await get_admin_role(uid)
    is_super = (role == "super")

    if data == "admin_back":
        await query.edit_message_text(
            "🛡️ *Admin Panel*",
            parse_mode="Markdown",
            reply_markup=admin_main_keyboard(role or "super"))
    elif data == "admin_close":
        await query.edit_message_text("✅ Panel closed.")
    elif data == "admin_view_users":
        await show_users(query)
    elif data == "admin_stats":
        if not is_super:
            await query.edit_message_text("⛔ No permission.", reply_markup=admin_back_keyboard())
            return
        await show_stats(query)
    elif data == "admin_view_questions":
        await show_questions(query)
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
            "➕ *Add Sub Admin*\n\nSend the Telegram ID of the person.\nThey must have started the bot first.\n\nType /cancel to abort.",
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
            "Examples:\n"
            "`entrance|natural|physics|Physics|⚡`\n"
            "`driving|general|parking|Parking Rules|🚗`\n\n"
            "Type /cancel to abort.", parse_mode="Markdown")
    elif data == "admin_edit_subject":
        context.user_data["waiting_for"] = "edit_subject_info"
        await query.edit_message_text(
            "✏️ *Edit Subject*\n\nFormat: `old_key|new_name|new_emoji`\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_delete_subject":
        context.user_data["waiting_for"] = "delete_subject_key"
        await query.edit_message_text(
            "🗑️ *Delete Subject*\n\nSend the subject key to delete.\nUse View Questions to find keys.\n\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_list_subjects":
        await list_subjects(query)
    elif data == "admin_add_dept":
        context.user_data["waiting_for"] = "new_dept_info"
        await query.edit_message_text(
            "➕ *Add Department*\n\n"
            "Format: `exam_type|key|name|emoji`\n\n"
            "Examples:\n"
            "`exit|nursing|Nursing|🩺`\n"
            "`coc|coc_welding|Welding|🔧`\n\n"
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
            "Separate each question with a blank line.\n"
            "Send the `.txt` file now:",
            parse_mode="Markdown")
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
            "Examples:\n"
            "`7|100`  = 7 days free, up to 100 students\n"
            "`30|1`   = 30 days, 1 student only\n\n"
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
    elif data.startswith("aq_subject_"):
        subject = data.replace("aq_subject_", "")
        context.user_data["aq_subject"] = subject
        context.user_data["aq_subject_label"] = subject.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            "📝 Subject: " + context.user_data["aq_subject_label"] + "\n\nType the question text:\nType /cancel to abort.")
    elif data.startswith("aq_dept_"):
        dept = data.replace("aq_dept_", "")
        context.user_data["aq_stream"] = dept
        context.user_data["aq_subject"] = dept
        context.user_data["aq_subject_label"] = dept.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            "📝 Department: *" + dept.replace("_", " ").title() + "*\n\nType the question text:\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data.startswith("edit_q_field_"):
        field = data.replace("edit_q_field_", "")
        context.user_data["edit_field"] = field
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


async def admin_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    if not await is_any_admin(uid):
        return
    has_upload = bool(context.user_data.get("parsed_questions"))

    if data == "aq_type_entrance":
        context.user_data["aq_exam_type"] = "entrance"
        if has_upload:
            context.user_data["upload_exam_type"] = "entrance"
        await query.edit_message_text("📚 Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_type_exit":
        context.user_data["aq_exam_type"] = "exit"
        if has_upload:
            context.user_data["upload_exam_type"] = "exit"
        depts = await get_depts("exit")
        if not depts:
            await query.edit_message_text(
                "⚠️ No Exit Exam departments found.\n\n"
                "Add departments first:\n"
                "Admin Panel → Manage Departments → Add Department\n\n"
                "Format: exam_type|key|name|emoji\n"
                "Example: exit|nursing|Nursing",
                reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("🏛️ Choose department:", reply_markup=build_dept_keyboard(depts))

    elif data == "aq_type_coc":
        context.user_data["aq_exam_type"] = "coc"
        if has_upload:
            context.user_data["upload_exam_type"] = "coc"
        depts = await get_depts("coc")
        if not depts:
            await query.edit_message_text(
                "⚠️ No CoC departments found.\n\n"
                "Add departments first:\n"
                "Admin Panel → Manage Departments → Add Department\n\n"
                "Format: exam_type|key|name|emoji\n"
                "Example: coc|coc_electrical|Electrical",
                reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("📋 Choose CoC department:", reply_markup=build_dept_keyboard(depts))

    elif data == "aq_type_driving":
        context.user_data["aq_exam_type"] = "driving"
        context.user_data["aq_stream"] = "general"
        if has_upload:
            context.user_data["upload_exam_type"] = "driving"
            context.user_data["upload_stream"] = "general"
        subjects = await get_subjects("driving", "general")
        if not subjects:
            await query.edit_message_text(
                "⚠️ No Driving subjects found.\n\n"
                "Add subjects first:\n"
                "Admin Panel → Manage Subjects → Add Subject\n\n"
                "Format: exam_type|stream|key|name|emoji\n"
                "Example: driving|general|traffic_rules|Traffic Rules",
                reply_markup=admin_back_keyboard())
            return
        prefix = "upload_subject_" if has_upload else "aq_subject_"
        await query.edit_message_text("🚗 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix=prefix))

    elif data == "aq_type_remedial":
        context.user_data["aq_exam_type"] = "remedial"
        if has_upload:
            context.user_data["upload_exam_type"] = "remedial"
        await query.edit_message_text("📝 Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_stream_natural":
        exam_type = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "natural"
        subjects = await get_subjects(exam_type, "natural")
        if has_upload:
            context.user_data["upload_stream"] = "natural"
            await query.edit_message_text(
                "🔬 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "🔬 Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data == "aq_stream_social":
        exam_type = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "social"
        subjects = await get_subjects(exam_type, "social")
        if has_upload:
            context.user_data["upload_stream"] = "social"
            await query.edit_message_text(
                "📚 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "📚 Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data.startswith("aq_dept_"):
        dept = data.replace("aq_dept_", "")
        exam_type = context.user_data.get("aq_exam_type", "exit")
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
            context.user_data["aq_stream"] = dept
            context.user_data["aq_subject"] = dept
            context.user_data["aq_subject_label"] = dept.replace("_", " ").title()
            context.user_data["waiting_for"] = "aq_question_text"
            await query.edit_message_text(
                "📝 Department: " + dept.replace("_", " ").title() + "\n\nType the question text:\nType /cancel to abort.")

    elif data.startswith("upload_subject_"):
        subject = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream = context.user_data.get("upload_stream", "natural")
        await query.edit_message_text(
            "✅ Ready to save " + str(len(parsed)) + " questions\n\n"
            "Subject: " + subject.replace("_", " ").title() + "\n"
            "Exam: " + exam_type.title() + " / " + stream + "\n\nConfirm?",
            reply_markup=admin_confirm_keyboard())

    elif data == "aq_confirm_save":
        if context.user_data.get("parsed_questions"):
            await save_bulk_questions(query, context)
        else:
            await save_question_from_context(query, context)


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
        context.user_data["aq_option_d"] = text
        context.user_data["waiting_for"] = "aq_correct_answer"
        await update.message.reply_text("✅ OK. Correct answer: *A*, *B*, *C*, or *D*?", parse_mode="Markdown")

    elif waiting == "aq_correct_answer":
        if text.upper() not in ["A", "B", "C", "D"]:
            await update.message.reply_text("⚠️ Must be A, B, C, or D. Try again:")
            return
        context.user_data["aq_correct_answer"] = text.upper()
        context.user_data["waiting_for"] = "aq_explanation"
        await update.message.reply_text("✅ OK. Type the *explanation*:", parse_mode="Markdown")

    elif waiting == "aq_explanation":
        context.user_data["aq_explanation"] = text
        context.user_data["waiting_for"] = "aq_reference"
        await update.message.reply_text("✅ OK. Type *reference* or type `none`:", parse_mode="Markdown")

    elif waiting == "aq_reference":
        context.user_data["aq_reference"] = "" if text.lower() == "none" else text
        context.user_data["waiting_for"] = "aq_year"
        await update.message.reply_text("✅ OK. Type *exam year* (e.g. 2023) or `none`:", parse_mode="Markdown")

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
                await update.message.reply_text(
                    "⚠️ User not found. They must /start the bot first.")
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
        if stream:
            label += " / " + stream.title()
        if dept:
            label += " / " + dept.replace("_", " ").title()
        await update.message.reply_text(
            "✅ *Subscription granted!*\n\nUser: " + str(row[0] or tid) + "\nAccess: " + label + "\nDuration: " + str(days) + " days",
            parse_mode="Markdown", reply_markup=admin_back_keyboard())
        try:
            await context.bot.send_message(
                chat_id=tid,
                text="🎉 Your subscription is activated!\n\nAccess: " + label + "\nDuration: " + str(days) + " days\n\nStart practicing now! Send /start")
        except Exception:
            pass

    elif waiting == "broadcast_msg":
        context.user_data.clear()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT telegram_id FROM users")
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
                "⚠️ Wrong format.\nUse: `exam_type|stream|key|name|emoji`\n\nExample: `entrance|natural|physics|Physics|⚡`",
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
        try:
            tid = int(text)
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
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("⚠️ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM admin_users WHERE telegram_id=?", (tid,))
            await db.commit()
        await update.message.reply_text("✅ Admin removed: " + str(tid), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_question_id":
        try:
            qid = int(text)
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
        context.user_data["waiting_for"] = None
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
            try:
                value = int(text) if text.lower() != "none" else None
            except ValueError:
                value = None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("UPDATE questions SET " + field + "=? WHERE id=?", (value, qid))
            await db.commit()
        context.user_data["waiting_for"] = None
        await update.message.reply_text("✅ Question " + str(qid) + " updated!", reply_markup=admin_back_keyboard())

    elif waiting == "delete_question_id":
        try:
            qid = int(text)
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

    elif waiting == "giveaway_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("⚠️ Format: `days|max_uses`\n\nExample: `7|100`", parse_mode="Markdown")
            return
        try:
            days, max_uses = int(parts[0]), int(parts[1])
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
            "🎁 *Giveaway Code Created!*\n\nCode: `" + code + "`\nDuration: " + str(days) + " days free access\nMax Uses: " + str(max_uses) + " students\n\nStudents redeem with: `/redeem " + code + "`",
            parse_mode="Markdown", reply_markup=admin_back_keyboard())

    elif waiting == "edit_bank_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("⚠️ Format: `bank_name|account_number|account_name`", parse_mode="Markdown")
            return
        bank_name, acc_num, acc_name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO bank_accounts (bank_name,account_number,account_name) VALUES (?,?,?) "
                "ON CONFLICT(bank_name) DO UPDATE SET account_number=excluded.account_number, account_name=excluded.account_name",
                (bank_name, acc_num, acc_name))
            await db.commit()
        await update.message.reply_text(
            "✅ *Bank updated!*\n" + bank_name + ": " + acc_num + " / " + acc_name,
            parse_mode="Markdown", reply_markup=admin_back_keyboard())
        context.user_data.clear()


async def admin_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_any_admin(uid):
        return
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
            "```\nQ: Question text\nA) ...\nB) ...\nC) ...\nD) ...\nAnswer: B\nExplanation: ...\n```\n\nSeparate questions with a blank line.",
            parse_mode="Markdown")
        return
    context.user_data["parsed_questions"] = parsed
    context.user_data["waiting_for"]      = "upload_exam_type"
    await update.message.reply_text(
        "✅ *Found " + str(len(parsed)) + " questions!*\n\nStep 1: Choose exam type:",
        parse_mode="Markdown",
        reply_markup=admin_exam_type_keyboard())


async def save_bulk_questions(query, context):
    parsed    = context.user_data.get("parsed_questions", [])
    exam_type = context.user_data.get("upload_exam_type", "entrance")
    stream    = context.user_data.get("upload_stream", "natural")
    subject   = context.user_data.get("upload_subject", "")

    if exam_type in ("exit", "coc") and not stream:
        await query.edit_message_text(
            "⚠️ Department not set. Please start upload again.",
            reply_markup=admin_back_keyboard())
        context.user_data.clear()
        return

    saved = failed = 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for q in parsed:
            try:
                cur = await db.execute(
                    "SELECT id FROM questions WHERE exam_type=? AND stream=? AND subject=? AND question_text=?",
                    (exam_type, stream, subject, q.get("question_text", "")))
                if await cur.fetchone():
                    failed += 1
                    continue
                await db.execute(
                    "INSERT INTO questions "
                    "(exam_type,stream,subject,year,question_text,"
                    "option_a,option_b,option_c,option_d,correct_answer,explanation,reference) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exam_type, stream, subject, q.get("year"),
                     q.get("question_text"), q.get("option_a"), q.get("option_b"),
                     q.get("option_c"), q.get("option_d"),
                     (q.get("correct_answer") or "").upper(),
                     q.get("explanation", ""), q.get("reference", "")))
                saved += 1
            except Exception as e:
                logger.error(f"save_bulk_questions row error: {e}")
                failed += 1
        await db.commit()

    logger.info(f"Bulk upload: exam={exam_type} stream={stream} subject={subject} saved={saved} failed={failed}")
    context.user_data.clear()
    await query.edit_message_text(
        "✅ Upload Complete!\n\n"
        "Exam: " + exam_type.title() + " / " + stream + "\n"
        "Subject: " + subject.replace("_", " ").title() + "\n"
        "Saved: " + str(saved) + "\n"
        "Skipped (duplicates/errors): " + str(failed),
        reply_markup=admin_back_keyboard())


async def save_question_from_context(query, context):
    d = context.user_data
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO questions "
                "(exam_type,stream,subject,year,question_text,"
                "option_a,option_b,option_c,option_d,correct_answer,explanation,reference) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (d.get("aq_exam_type"), d.get("aq_stream"), d.get("aq_subject"),
                 d.get("aq_year"), d.get("aq_question_text"),
                 d.get("aq_option_a"), d.get("aq_option_b"),
                 d.get("aq_option_c"), d.get("aq_option_d"),
                 d.get("aq_correct_answer"),
                 d.get("aq_explanation", ""), d.get("aq_reference", "")))
            await db.commit()
        context.user_data.clear()
        await query.edit_message_text("✅ *Question saved successfully!*", parse_mode="Markdown",
                                       reply_markup=admin_main_keyboard())
    except Exception as e:
        await query.edit_message_text("⚠️ Error: " + str(e), reply_markup=admin_main_keyboard())


# ── Display helpers ───────────────────────────────────────────────────────────

async def show_users(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total   = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        sub     = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        today   = (await (await db.execute("SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')")).fetchone())[0]
        new_today = (await (await db.execute("SELECT COUNT(*) FROM users WHERE date(created_at)=date('now')")).fetchone())[0]
        cur = await db.execute(
            "SELECT telegram_id,full_name,is_subscribed,subscribed_exam_type "
            "FROM users ORDER BY created_at DESC LIMIT 15")
        recent = await cur.fetchall()
    lines = ""
    for r in recent:
        tag = "💳[" + str(r[3] or "") + "]" if r[2] else "🆓[FREE]"
        lines += tag + " " + str(r[1] or "Unknown") + " (" + str(r[0]) + ")\n"
    await query.edit_message_text(
        "👥 *USERS*\n\n"
        "Total: " + str(total) + "\n"
        "Subscribed: " + str(sub) + "\n"
        "Free: " + str(total - sub) + "\n"
        "Active today: " + str(today) + "\n"
        "New today: " + str(new_today) + "\n\n"
        "Recent 15:\n" + lines,
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def show_stats(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        exams   = (await (await db.execute("SELECT COUNT(*) FROM exam_sessions WHERE completed=1")).fetchone())[0]
        qcount  = (await (await db.execute("SELECT COUNT(*) FROM questions")).fetchone())[0]
        row     = await (await db.execute(
            "SELECT AVG(CAST(score AS FLOAT)/total*100) FROM exam_sessions WHERE completed=1 AND total>0")).fetchone()
        avg     = row[0] if row[0] else 0
        pending = (await (await db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")).fetchone())[0]
        cur     = await db.execute(
            "SELECT subject,COUNT(*) FROM exam_sessions WHERE completed=1 "
            "GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 5")
        pop     = await cur.fetchall()
    pop_text = "\n".join("  " + (p[0] or "?").replace("_", " ").title() + ": " + str(p[1]) for p in pop)
    await query.edit_message_text(
        "📊 *STATISTICS*\n\n"
        "Total exams taken: " + str(exams) + "\n"
        "Questions in DB: " + str(qcount) + "\n"
        "Avg score: " + str(round(avg, 1)) + "%\n"
        "Pending receipts: " + str(pending) + "\n\n"
        "Top subjects:\n" + pop_text,
        parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def show_questions(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id,exam_type,stream,subject,year FROM questions ORDER BY id DESC LIMIT 20")
        rows = await cur.fetchall()
        total = (await (await db.execute("SELECT COUNT(*) FROM questions")).fetchone())[0]
    if not rows:
        await query.edit_message_text("📚 No questions in database.", reply_markup=admin_back_keyboard())
        return
    text = "📚 *Questions* (last 20 of " + str(total) + ")\n\n"
    for r in rows:
        text += "ID:" + str(r[0]) + " [" + str(r[1]) + "/" + str(r[2] or "") + "] " + str(r[3] or "") + " " + str(r[4] or "") + "\n"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_subjects(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT exam_type,stream,subject_key,subject_name,emoji FROM subjects ORDER BY exam_type,stream,subject_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("📚 No subjects found.", reply_markup=admin_back_keyboard())
        return
    text = "📚 *SUBJECTS*\n\n"
    for r in rows:
        text += str(r[4] or "") + " " + str(r[3]) + " [" + str(r[2]) + "]\n  " + str(r[0]) + "/" + str(r[1] or "") + "\n"
    await query.edit_message_text(text[:4000], parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_depts(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT exam_type,dept_key,dept_name,emoji FROM departments ORDER BY exam_type,dept_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("🏛️ No departments found.", reply_markup=admin_back_keyboard())
        return
    text = "🏛️ *DEPARTMENTS*\n\n"
    for r in rows:
        text += str(r[3] or "") + " " + str(r[2]) + " [" + str(r[1]) + "]\n  " + str(r[0]) + "\n"
    await query.edit_message_text(text[:4000], parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_admins(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT telegram_id,full_name,role FROM admin_users ORDER BY role,full_name")
        rows = await cur.fetchall()
    text = "👮 *ADMINS*\n\n"
    text += "🔑 SUPER: ID " + str(ADMIN_ID) + "\n\n"
    for r in rows:
        text += ("🛡️ " if r[2] == "super" else "👤 ") + str(r[1] or "Unknown") + " (" + str(r[0]) + ")\n"
    if not rows:
        text += "No sub-admins added yet."
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def list_giveaways(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT code,duration_days,max_uses,used_count,created_at "
            "FROM giveaway_codes ORDER BY created_at DESC LIMIT 10")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("🎁 No giveaway codes.", reply_markup=admin_back_keyboard())
        return
    text = "🎁 *GIVEAWAY CODES*\n\n"
    for r in rows:
        text += "`" + str(r[0]) + "` | " + str(r[1]) + " days | " + str(r[3]) + "/" + str(r[2]) + " used\n"
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def show_pending_receipts(query, context):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT p.id,p.telegram_id,p.bank,p.exam_type,p.stream,p.dept,"
            "p.created_at,p.receipt_file_id,u.full_name "
            "FROM payments p LEFT JOIN users u ON p.telegram_id=u.telegram_id "
            "WHERE p.status='pending' ORDER BY p.created_at ASC LIMIT 5")
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("✅ No pending receipts.", reply_markup=admin_back_keyboard())
        return
    for p in rows:
        label = str(p["exam_type"] or "")
        if p["stream"] and p["stream"] not in ("general", ""):
            label += "/" + str(p["stream"])
        if p["dept"]:
            label += "/" + str(p["dept"]).replace("_", " ").title()
        caption = (
            "PENDING RECEIPT\n\n"
            "User: " + str(p["full_name"] or "Unknown") + "\n"
            "ID: " + str(p["telegram_id"]) + "\n"
            "Bank: " + str(p["bank"]) + "\n"
            "Exam: " + label + "\n"
            "Date: " + str(p["created_at"])[:10]
        )
        kb = receipt_action_keyboard(
            p["id"], p["telegram_id"],
            p["exam_type"] or "",
            p["stream"] or "",
            p["dept"] or "")
        try:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=p["receipt_file_id"],
                caption=caption,
                reply_markup=kb)
        except Exception:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=caption,
                reply_markup=kb)


async def approve_receipt(query, context, data):
    # FIXED: split on '|' not '_' to handle dept keys like 'computer_science'
    parts       = data.replace("rcpt_ok_", "").split("|")
    if len(parts) < 2:
        return
    payment_id  = int(parts[0])
    telegram_id = int(parts[1])
    exam_type   = parts[2] if len(parts) > 2 else "entrance"
    stream      = parts[3] if len(parts) > 3 and parts[3] not in ("", "None") else ""
    dept        = parts[4] if len(parts) > 4 and parts[4] not in ("", "None") else ""

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE payments SET status='approved', reviewed_by=? WHERE id=?",
            (query.from_user.id, payment_id))
        await db.execute(
            "UPDATE users SET is_subscribed=1, "
            "subscription_expiry=datetime('now','+30 days'), "
            "subscribed_exam_type=?, subscribed_stream=?, subscribed_dept=? "
            "WHERE telegram_id=?",
            (exam_type, stream, dept, telegram_id))
        await db.commit()

    label = exam_type.title()
    if stream and stream not in ("general", ""):
        label += " / " + stream.title()
    if dept:
        label += " / " + dept.replace("_", " ").title()

    try:
        await query.edit_message_caption(
            "✅ APPROVED — Subscription activated.\n\n"
            "Access: " + label + "\nDuration: 30 days")
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="🎉 *Payment Approved!*\n\n"
            "Your subscription is now active.\n\n"
            "✅ Access: " + label + "\n"
            "📅 Duration: 30 days\n\n"
            "Start practicing now! Send /start",
            parse_mode="Markdown")
    except Exception:
        pass


async def reject_receipt(query, context, data):
    parts       = data.replace("rcpt_no_", "").split("|")
    if len(parts) < 2:
        return
    payment_id  = int(parts[0])
    telegram_id = int(parts[1])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE payments SET status='rejected', reviewed_by=? WHERE id=?",
            (query.from_user.id, payment_id))
        await db.commit()

    try:
        await query.edit_message_caption("❌ REJECTED.")
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="❌ *Payment Not Approved*\n\n"
            "Your payment receipt was not approved.\n\n"
            "Please make sure you:\n"
            "• Sent the correct amount\n"
            "• Screenshot shows your name & transaction\n\n"
            "Contact admin: @John_3_13 for help.",
            parse_mode="Markdown")
    except Exception:
        pass