from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_dynamic_subject_keyboard(subjects: list) -> InlineKeyboardMarkup:
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(
            f"{s['emoji']} {s['subject_name']}",
            callback_data=f"subject_{s['subject_key']}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def build_year_select_keyboard(years: list, subject_key: str) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for y in sorted(years, reverse=True):
        row.append(InlineKeyboardButton(str(y), callback_data=f"examyear_{subject_key}_{y}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("📚 All Years", callback_data=f"examyear_{subject_key}_all")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="choose_subject")])
    return InlineKeyboardMarkup(keyboard)


def answer_keyboard(session_id: int) -> InlineKeyboardMarkup:
    keyboard = [[
        InlineKeyboardButton("A", callback_data=f"answer_{session_id}_A"),
        InlineKeyboardButton("B", callback_data=f"answer_{session_id}_B"),
        InlineKeyboardButton("C", callback_data=f"answer_{session_id}_C"),
        InlineKeyboardButton("D", callback_data=f"answer_{session_id}_D"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def after_exam_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔄 Try Again", callback_data="retry_exam")],
        [InlineKeyboardButton("📊 My Progress", callback_data="my_progress")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def start_exam_keyboard(subject: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🚀 Start Exam!", callback_data=f"start_exam_{subject}")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)
