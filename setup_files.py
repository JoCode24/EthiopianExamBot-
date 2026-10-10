import os

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Written: {path}")

# ── app/handlers/admin.py ─────────────────────────────────
write("app/handlers/admin.py", """from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import (
    admin_main_keyboard, admin_exam_type_keyboard, admin_stream_keyboard,
    admin_confirm_keyboard, admin_back_keyboard, admin_cancel_keyboard,
    build_subject_keyboard, build_dept_keyboard,
    manage_subjects_keyboard, manage_depts_keyboard,
)
from app.utils.logger import logger
from app.utils.question_parser import parse_questions_from_text
from config import ADMIN_ID, DATABASE_PATH
import aiosqlite


def is_admin(uid): return uid == ADMIN_ID


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
        "🔧 *Admin Panel*\\n\\nChoose an action:",
        parse_mode="Markdown", reply_markup=admin_main_keyboard()
    )


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not is_admin(query.from_user.id):
        await query.edit_message_text("Unauthorized.")
        return

    if data == "admin_back":
        await query.edit_message_text("🔧 *Admin Panel*\\n\\nChoose an action:",
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
        await query.edit_message_text("📚 *Manage Subjects*\\n\\nChoose an action:",
            parse_mode="Markdown", reply_markup=manage_subjects_keyboard())
    elif data == "admin_manage_depts":
        await query.edit_message_text("🏛 *Manage Departments*\\n\\nChoose an action:",
            parse_mode="Markdown", reply_markup=manage_depts_keyboard())
    elif data == "admin_list_subjects":
        await list_subjects(query)
    elif data == "admin_list_depts":
        await list_depts(query)
    elif data == "admin_add_subject":
        context.user_data["waiting_for"] = "new_subject_info"
        await query.edit_message_text(
            "📚 *Add New Subject*\\n\\n"
            "Send in this format:\\n"
            "exam\\_type|stream|key|name|emoji\\n\\n"
            "Examples:\\n"
            "entrance|natural|physics|Physics|⚡\\n"
            "entrance|social|history|History|📜\\n"
            "exit|exit|nursing|Nursing|🩺\\n\\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_add_dept":
        context.user_data["waiting_for"] = "new_dept_info"
        await query.edit_message_text(
            "🏛 *Add New Department*\\n\\n"
            "Send in this format:\\n"
            "key|name|emoji\\n\\n"
            "Example: nursing|Nursing|🩺\\n\\n"
            "Type /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_add_question":
        context.user_data.clear()
        await query.edit_message_text(
            "➕ *Add Question*\\n\\nStep 1: Choose exam type:",
            parse_mode="Markdown", reply_markup=admin_exam_type_keyboard())
    elif data == "admin_upload_file":
        context.user_data["waiting_for"] = "question_file"
        await query.edit_message_text(
            "📄 *Upload Question File*\\n\\n"
            "Send a .txt file with this format per question:\\n\\n"
            "Q: Question text\\n"
            "A) Option A\\n"
            "B) Option B\\n"
            "C) Option C\\n"
            "D) Option D\\n"
            "Answer: B\\n"
            "Explanation: reason\\n"
            "Reference: book chapter\\n"
            "Year: 2023\\n\\n"
            "Separate questions with a blank line.",
            parse_mode="Markdown")
    elif data == "admin_grant_sub":
        context.user_data["waiting_for"] = "grant_sub_id"
        await query.edit_message_text(
            "💳 *Grant Subscription*\\n\\nSend the user Telegram ID.\\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_broadcast":
        context.user_data["waiting_for"] = "broadcast_msg"
        await query.edit_message_text(
            "📢 *Broadcast*\\n\\nType your message for ALL users.\\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "admin_cancel_question":
        context.user_data.clear()
        await query.edit_message_text("Cancelled.", reply_markup=admin_main_keyboard())
    elif data == "aq_type_entrance":
        context.user_data["aq_exam_type"] = "entrance"
        await query.edit_message_text("Step 2: Choose stream:",
            parse_mode="Markdown", reply_markup=admin_stream_keyboard())
    elif data == "aq_type_exit":
        context.user_data["aq_exam_type"] = "exit"
        context.user_data["aq_stream"] = "exit"
        depts = await get_depts()
        await query.edit_message_text("Step 2: Choose department:",
            parse_mode="Markdown", reply_markup=build_dept_keyboard(depts))
    elif data == "aq_stream_natural":
        context.user_data["aq_stream"] = "natural"
        subjects = await get_subjects("entrance", "natural")
        await query.edit_message_text("Step 3: Choose subject:",
            parse_mode="Markdown", reply_markup=build_subject_keyboard(subjects))
    elif data == "aq_stream_social":
        context.user_data["aq_stream"] = "social"
        subjects = await get_subjects("entrance", "social")
        await query.edit_message_text("Step 3: Choose subject:",
            parse_mode="Markdown", reply_markup=build_subject_keyboard(subjects))
    elif data.startswith("aq_subject_"):
        subject = data.replace("aq_subject_", "")
        context.user_data["aq_subject"] = subject
        context.user_data["aq_subject_label"] = subject.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            f"Subject: *{context.user_data['aq_subject_label']}*\\n\\n"
            "Type the question text:\\nType /cancel to abort.",
            parse_mode="Markdown")
    elif data == "aq_confirm_save":
        if context.user_data.get("parsed_questions"):
            await save_bulk_questions(query, context)
        else:
            await save_question_from_context(query, context)
    elif data.startswith("upload_subject_"):
        subject = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream = context.user_data.get("upload_stream", "natural")
        await query.edit_message_text(
            f"📄 Ready to save *{len(parsed)}* questions\\n\\n"
            f"Subject: *{subject.replace('_',' ').title()}*\\n"
            f"Exam: *{exam_type.title()}* | Stream: *{stream.title()}*\\n\\n"
            f"Confirm?",
            parse_mode="Markdown", reply_markup=admin_confirm_keyboard())
    elif data == "upload_stream_natural":
        context.user_data["upload_stream"] = "natural"
        subjects = await get_subjects("entrance", "natural")
        await query.edit_message_text("Choose subject for uploaded questions:",
            reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
    elif data == "upload_stream_social":
        context.user_data["upload_stream"] = "social"
        subjects = await get_subjects("entrance", "social")
        await query.edit_message_text("Choose subject for uploaded questions:",
            reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))


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

    if waiting == "aq_question_text":
        context.user_data["aq_question_text"] = text
        context.user_data["waiting_for"] = "aq_option_a"
        await update.message.reply_text("✅ Saved. Type *Option A*:", parse_mode="Markdown")
    elif waiting == "aq_option_a":
        context.user_data["aq_option_a"] = text
        context.user_data["waiting_for"] = "aq_option_b"
        await update.message.reply_text("✅ Saved. Type *Option B*:", parse_mode="Markdown")
    elif waiting == "aq_option_b":
        context.user_data["aq_option_b"] = text
        context.user_data["waiting_for"] = "aq_option_c"
        await update.message.reply_text("✅ Saved. Type *Option C*:", parse_mode="Markdown")
    elif waiting == "aq_option_c":
        context.user_data["aq_option_c"] = text
        context.user_data["waiting_for"] = "aq_option_d"
        await update.message.reply_text("✅ Saved. Type *Option D*:", parse_mode="Markdown")
    elif waiting == "aq_option_d":
        context.user_data["aq_option_d"] = text
        context.user_data["waiting_for"] = "aq_correct_answer"
        await update.message.reply_text(
            "✅ Saved. Type correct answer: A, B, C, or D", parse_mode="Markdown")
    elif waiting == "aq_correct_answer":
        if text.upper() not in ["A","B","C","D"]:
            await update.message.reply_text("Must be A, B, C, or D. Try again:")
            return
        context.user_data["aq_correct_answer"] = text.upper()
        context.user_data["waiting_for"] = "aq_explanation"
        await update.message.reply_text("✅ Saved. Type the *explanation*:", parse_mode="Markdown")
    elif waiting == "aq_explanation":
        context.user_data["aq_explanation"] = text
        context.user_data["waiting_for"] = "aq_reference"
        await update.message.reply_text(
            "✅ Saved. Type *reference* or type none:", parse_mode="Markdown")
    elif waiting == "aq_reference":
        context.user_data["aq_reference"] = "" if text.lower() == "none" else text
        context.user_data["waiting_for"] = "aq_year"
        await update.message.reply_text(
            "✅ Saved. Type the *exam year* (e.g. 2023) or type none:",
            parse_mode="Markdown")
    elif waiting == "aq_year":
        try:
            context.user_data["aq_year"] = int(text) if text.lower() != "none" else None
        except ValueError:
            context.user_data["aq_year"] = None
        context.user_data["waiting_for"] = None
        d = context.user_data
        preview = (
            f"📋 *Preview*\\n\\n"
            f"Subject: *{d.get('aq_subject_label')}*\\n"
            f"Exam: *{d.get('aq_exam_type','').title()}* | "
            f"Stream: *{d.get('aq_stream','').title()}*\\n"
            f"Year: *{d.get('aq_year') or 'N/A'}*\\n\\n"
            f"Q: {d.get('aq_question_text')}\\n\\n"
            f"A) {d.get('aq_option_a')}\\n"
            f"B) {d.get('aq_option_b')}\\n"
            f"C) {d.get('aq_option_c')}\\n"
            f"D) {d.get('aq_option_d')}\\n\\n"
            f"Answer: *{d.get('aq_correct_answer')}*\\n"
            f"Explanation: {d.get('aq_explanation')}\\n"
            f"Reference: {d.get('aq_reference') or 'N/A'}"
        )
        await update.message.reply_text(preview, parse_mode="Markdown",
            reply_markup=admin_confirm_keyboard())
    elif waiting == "grant_sub_id":
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number. Try again:")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text(
                    f"User {tid} not found. They must /start the bot first.",
                    reply_markup=admin_back_keyboard())
                context.user_data.clear()
                return
            await db.execute(
                "UPDATE users SET is_subscribed=1, "
                "subscription_expiry=datetime('now','+30 days') WHERE telegram_id=?",
                (tid,))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Subscription granted to *{row[0] or tid}* for 30 days.",
            parse_mode="Markdown", reply_markup=admin_back_keyboard())
        try:
            await context.bot.send_message(chat_id=tid,
                text="🎉 *Subscription activated!* 30 days full access. Good luck! 📚",
                parse_mode="Markdown")
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
                await context.bot.send_message(chat_id=uid,
                    text=f"📢 *EthiopianExamBot:*\\n\\n{text}", parse_mode="Markdown")
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"📢 Done! Sent: {sent} | Failed: {failed}",
            reply_markup=admin_back_keyboard())
    elif waiting == "new_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 5:
            await update.message.reply_text(
                "Wrong format. Use: exam_type|stream|key|name|emoji")
            return
        exam_type, stream, key, name, emoji = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO subjects (exam_type,stream,subject_key,subject_name,emoji) "
                    "VALUES (?,?,?,?,?)", (exam_type, stream, key, name, emoji))
                await db.commit()
                await update.message.reply_text(
                    f"✅ Subject {name} added!",
                    reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(f"Error: {e}",
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
                    f"✅ Department {name} added!",
                    reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(f"Error: {e}",
                    reply_markup=admin_back_keyboard())
        context.user_data.clear()


async def admin_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if context.user_data.get("waiting_for") != "question_file":
        return
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Please send a .txt file only.")
        return
    await update.message.reply_text("Reading file...")
    file = await context.bot.get_file(doc.file_id)
    content = bytes(await file.download_as_bytearray()).decode("utf-8", errors="ignore")
    parsed = parse_questions_from_text(content)
    if not parsed:
        await update.message.reply_text(
            "No valid questions found. Check the format and try again.",
            reply_markup=admin_back_keyboard())
        return
    context.user_data["parsed_questions"] = parsed
    context.user_data["waiting_for"] = "upload_exam_type"
    await update.message.reply_text(
        f"✅ Found {len(parsed)} questions! Choose exam type:",
        reply_markup=admin_exam_type_keyboard())


async def admin_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if not is_admin(query.from_user.id):
        return
    if not context.user_data.get("parsed_questions"):
        return
    if data == "aq_type_entrance":
        context.user_data["upload_exam_type"] = "entrance"
        await query.edit_message_text(
            "Choose stream:", reply_markup=admin_stream_keyboard())
    elif data == "aq_type_exit":
        context.user_data["upload_exam_type"] = "exit"
        context.user_data["upload_stream"] = "exit"
        depts = await get_depts()
        await query.edit_message_text(
            "Choose department:",
            reply_markup=build_dept_keyboard(depts, prefix="upload_subject_"))
    elif data == "aq_stream_natural":
        context.user_data["upload_stream"] = "natural"
        subjects = await get_subjects("entrance", "natural")
        await query.edit_message_text(
            "Choose subject:",
            reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
    elif data == "aq_stream_social":
        context.user_data["upload_stream"] = "social"
        subjects = await get_subjects("entrance", "social")
        await query.edit_message_text(
            "Choose subject:",
            reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
    elif data.startswith("upload_subject_"):
        subject = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream = context.user_data.get("upload_stream", "natural")
        await query.edit_message_text(
            f"Save {len(parsed)} questions to {subject.replace('_',' ').title()}? Confirm?",
            reply_markup=admin_confirm_keyboard())
    elif data == "aq_confirm_save":
        await save_bulk_questions(query, context)


async def save_bulk_questions(query, context: ContextTypes.DEFAULT_TYPE):
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
        f"✅ Upload Complete!\\n\\nSaved: {saved} | Failed: {failed}\\n"
        f"Subject: {subject.replace('_',' ').title()}",
        reply_markup=admin_back_keyboard())


async def save_question_from_context(query, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO questions "
                "(exam_type,stream,subject,year,question_text,"
                "option_a,option_b,option_c,option_d,"
                "correct_answer,explanation,reference) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (d.get("aq_exam_type"), d.get("aq_stream"), d.get("aq_subject"),
                 d.get("aq_year"), d.get("aq_question_text"),
                 d.get("aq_option_a"), d.get("aq_option_b"),
                 d.get("aq_option_c"), d.get("aq_option_d"),
                 d.get("aq_correct_answer"), d.get("aq_explanation",""),
                 d.get("aq_reference","")))
            await db.commit()
        context.user_data.clear()
        await query.edit_message_text(
            "✅ Question saved successfully!", reply_markup=admin_main_keyboard())
        logger.info(f"Question added: {d.get('aq_subject')}")
    except Exception as e:
        await query.edit_message_text(f"Error: {e}", reply_markup=admin_main_keyboard())


async def show_users(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        sub = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        today = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')")).fetchone())[0]
        new = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(created_at)=date('now')")).fetchone())[0]
        cur = await db.execute(
            "SELECT telegram_id,full_name,is_subscribed FROM users "
            "ORDER BY created_at DESC LIMIT 10")
        recent = await cur.fetchall()
    lines = "".join(
        f"{'💳' if r[2] else '🆓'} {r[1] or 'Unknown'} ({r[0]})\\n"
        for r in recent)
    await query.edit_message_text(
        f"👥 *Users*\\n\\nTotal: *{total}* | Sub: *{sub}* | Free: *{total-sub}*\\n"
        f"Active today: *{today}* | New today: *{new}*\\n\\n*Recent:*\\n{lines}",
        parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def show_stats(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        exams = (await (await db.execute(
            "SELECT COUNT(*) FROM exam_sessions WHERE completed=1")).fetchone())[0]
        today = (await (await db.execute(
            "SELECT COUNT(*) FROM exam_sessions WHERE completed=1 "
            "AND date(finished_at)=date('now')")).fetchone())[0]
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
    pop_text = "\\n".join(f"  {p[0].title()}: {p[1]}" for p in pop) or "None yet"
    await query.edit_message_text(
        f"📊 *Stats*\\n\\nExams: *{exams}* | Today: *{today}*\\n"
        f"Avg Score: *{avg:.1f}%* | Questions: *{qcount}*\\n\\n"
        f"🔥 Popular Subjects:\\n{pop_text}",
        parse_mode="Markdown", reply_markup=admin_back_keyboard())


async def show_questions(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT subject, year, COUNT(*) FROM questions "
            "GROUP BY subject, year ORDER BY subject, year DESC")
        rows = await cur.fetchall()
    if not rows:
        text = "No questions yet."
    else:
        lines = {}
        for r in rows:
            subj = r[0].replace("_"," ").title()
            yr = str(r[1]) if r[1] else "No year"
            if subj not in lines:
                lines[subj] = []
            lines[subj].append(f"  {yr}: {r[2]} questions")
        text = "❓ *Questions by Subject and Year*\\n\\n"
        for subj, yrs in lines.items():
            text += f"📘 *{subj}*\\n" + "\\n".join(yrs) + "\\n\\n"
    await query.edit_message_text(text, parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def list_subjects(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT exam_type,stream,subject_key,subject_name,emoji FROM subjects "
            "ORDER BY exam_type,stream,subject_name")
        rows = await cur.fetchall()
    text = "📚 *All Subjects*\\n\\n" + "".join(
        f"{r[4]} *{r[3]}* — {r[0]}/{r[1]} (key: {r[2]})\\n"
        for r in rows) if rows else "No subjects yet."
    await query.edit_message_text(text, parse_mode="Markdown",
        reply_markup=admin_back_keyboard())


async def list_depts(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT dept_key,dept_name,emoji FROM departments ORDER BY dept_name")
        rows = await cur.fetchall()
    text = "🏛 *All Departments*\\n\\n" + "".join(
        f"{r[2]} *{r[1]}* (key: {r[0]})\\n"
        for r in rows) if rows else "No departments yet."
    await query.edit_message_text(text, parse_mode="Markdown",
        reply_markup=admin_back_keyboard())
""")

print("All files written successfully!")