from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Entrance Exam", callback_data="exam_type_entrance")],
        [InlineKeyboardButton("🏛️ University Exit Exam", callback_data="exam_type_exit")],
        [InlineKeyboardButton("📋 CoC Exam (TVET)", callback_data="exam_type_coc")],
        [InlineKeyboardButton("🚗 Driving Licence Exam", callback_data="exam_type_driving")],
        [InlineKeyboardButton("📝 Remedial Exam", callback_data="exam_type_remedial")],
        [InlineKeyboardButton("▶️ Start Practice Exam", callback_data="choose_subject")],
        [InlineKeyboardButton("📊 My Progress", callback_data="my_progress")],
        [InlineKeyboardButton("💳 Subscribe - 50 ETB/month", callback_data="subscribe")],
        [InlineKeyboardButton("🎁 Referral - Earn Free Access", callback_data="show_referral")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
    ])


def stream_keyboard(prefix="stream_"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔬 Natural Science", callback_data=prefix + "natural")],
        [InlineKeyboardButton("📚 Social Science", callback_data=prefix + "social")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])


def build_dept_select_keyboard(depts, prefix="dept_select_"):
    keyboard = []
    for d in depts:
        keyboard.append([InlineKeyboardButton(
            d["emoji"] + " " + d["dept_name"],
            callback_data=prefix + d["dept_key"])])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def back_to_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
    ])


def subscription_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏦 Pay via CBE", callback_data="pay_CBE")],
        [InlineKeyboardButton("🏦 Pay via Awash Bank", callback_data="pay_Awash")],
        [InlineKeyboardButton("🏦 Pay via Dashen Bank", callback_data="pay_Dashen")],
        [InlineKeyboardButton("📸 Send Payment Screenshot", callback_data="send_receipt")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])


def exam_select_for_sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Entrance Exam", callback_data="sub_exam_entrance")],
        [InlineKeyboardButton("🏛️ University Exit Exam", callback_data="sub_exam_exit")],
        [InlineKeyboardButton("📋 CoC Exam", callback_data="sub_exam_coc")],
        [InlineKeyboardButton("🚗 Driving Licence", callback_data="sub_exam_driving")],
        [InlineKeyboardButton("📝 Remedial Exam", callback_data="sub_exam_remedial")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ])
