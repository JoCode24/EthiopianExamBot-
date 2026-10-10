from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard(role="super"):
    rows = [
        [InlineKeyboardButton("➕ Add Question (Manual)", callback_data="admin_add_question")],
        [InlineKeyboardButton("📄 Upload Question File (.txt)", callback_data="admin_upload_file")],
        [InlineKeyboardButton("✏️ Edit Question", callback_data="admin_edit_question")],
        [InlineKeyboardButton("🗑️ Delete Question", callback_data="admin_delete_question")],
        [InlineKeyboardButton("❓ View Questions", callback_data="admin_view_questions")],
        [InlineKeyboardButton("📚 Manage Subjects", callback_data="admin_manage_subjects")],
        [InlineKeyboardButton("🏛️ Manage Departments", callback_data="admin_manage_depts")],
        [InlineKeyboardButton("👥 View Users", callback_data="admin_view_users")],
        [InlineKeyboardButton("💳 Grant Subscription", callback_data="admin_grant_sub")],
        [InlineKeyboardButton("🎁 Giveaway Free Access", callback_data="admin_giveaway")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🧾 Pending Receipts", callback_data="admin_pending_receipts")],
    ]
    if role == "super":
        rows.append([InlineKeyboardButton("👮 Manage Admins", callback_data="admin_manage_admins")])
        rows.append([InlineKeyboardButton("🏦 Edit Bank Accounts", callback_data="admin_edit_banks")])
        rows.append([InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")])
    rows.append([InlineKeyboardButton("❌ Close Panel", callback_data="admin_close")])
    return InlineKeyboardMarkup(rows)


def admin_back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]
    ])


def admin_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm & Save", callback_data="aq_confirm_save")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel_question")],
    ])


def admin_exam_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Entrance Exam", callback_data="aq_type_entrance")],
        [InlineKeyboardButton("🏛️ Exit Exam", callback_data="aq_type_exit")],
        [InlineKeyboardButton("📋 CoC Exam", callback_data="aq_type_coc")],
        [InlineKeyboardButton("🚗 Driving Licence", callback_data="aq_type_driving")],
        [InlineKeyboardButton("📝 Remedial Exam", callback_data="aq_type_remedial")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])


def admin_stream_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔬 Natural Science", callback_data="aq_stream_natural")],
        [InlineKeyboardButton("📚 Social Science", callback_data="aq_stream_social")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])


def build_subject_keyboard(subjects, prefix="aq_subject_"):
    keyboard = []
    for s in subjects:
        emoji = s.get("emoji", "📘")
        keyboard.append([InlineKeyboardButton(
            emoji + " " + s["subject_name"],
            callback_data=prefix + s["subject_key"])])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def build_dept_keyboard(depts, prefix="aq_dept_"):
    keyboard = []
    for d in depts:
        emoji = d.get("emoji", "🏛️")
        keyboard.append([InlineKeyboardButton(
            emoji + " " + d["dept_name"],
            callback_data=prefix + d["dept_key"])])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def manage_subjects_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Subject", callback_data="admin_add_subject")],
        [InlineKeyboardButton("✏️ Edit Subject Name", callback_data="admin_edit_subject")],
        [InlineKeyboardButton("🗑️ Delete Subject", callback_data="admin_delete_subject")],
        [InlineKeyboardButton("📋 View All Subjects", callback_data="admin_list_subjects")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])


def manage_depts_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Department", callback_data="admin_add_dept")],
        [InlineKeyboardButton("✏️ Edit Department Name", callback_data="admin_edit_dept")],
        [InlineKeyboardButton("🗑️ Delete Department", callback_data="admin_delete_dept")],
        [InlineKeyboardButton("📋 View All Departments", callback_data="admin_list_depts")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])


def manage_admins_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Sub Admin", callback_data="admin_add_subadmin")],
        [InlineKeyboardButton("🗑️ Remove Admin", callback_data="admin_remove_admin")],
        [InlineKeyboardButton("📋 View All Admins", callback_data="admin_list_admins")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])


def giveaway_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Create Giveaway Code", callback_data="admin_create_giveaway")],
        [InlineKeyboardButton("📋 View Active Codes", callback_data="admin_list_giveaways")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])


def receipt_action_keyboard(payment_id, telegram_id, exam_type, stream, dept):
    # FIXED: pipe '|' separator so 'computer_science' is not broken by split
    ok_data = f"rcpt_ok_{payment_id}|{telegram_id}|{exam_type}|{stream}|{dept}"
    no_data = f"rcpt_no_{payment_id}|{telegram_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve - Grant Access", callback_data=ok_data)],
        [InlineKeyboardButton("❌ Reject", callback_data=no_data)],
    ])