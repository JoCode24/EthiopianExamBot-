"""
main.py  —  EthiopianExamBot entry point

Handler registration order matters:
- More-specific patterns first (admin_upload before admin_button)
- stream| and dept| patterns use pipe, not underscore
"""
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters,
)
from config import BOT_TOKEN
from app.database.db import init_db
from app.exams.engine import seed_sample_questions
from app.handlers.start import (
    start_handler, button_handler,
    stream_select_handler, dept_select_handler,
)
from app.handlers.exam import (
    direct_subject_handler,
    start_exam_handler,
    answer_handler,
    next_question_handler,
    retry_exam_handler,
    my_subscribed_exams_handler,
    sub_subject_handler,
    sub_year_select_handler,
    sub_start_exam_handler,
    leaderboard_handler,
)
from app.handlers.admin import (
    admin_command,
    admin_button_handler,
    admin_text_handler,
    admin_file_handler,
    admin_upload_handler,
)
from app.handlers.subscription import (
    subscribe_handler,
    sub_exam_select_handler,
    sub_stream_select,
    sub_dept_select,
    pay_bank_handler,
    send_receipt_handler,
    receipt_photo_handler,
)
from app.handlers.user_features import redeem_command, referral_command
from app.handlers.mock_exam import (
    mock_menu_handler,
    mock_subject_handler,
    mock_start_handler,
    mock_answer_handler,
    mock_next_handler,
    mock_dept_group_handler,
)
from app.utils.logger import logger


def main():
    logger.info("Starting EthiopianExamBot...")

    async def post_init(application):
        await init_db()
        await seed_sample_questions()
        logger.info("Bot started successfully!")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # ── Commands ──────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",    start_handler))
    app.add_handler(CommandHandler("admin",    admin_command))
    app.add_handler(CommandHandler("redeem",   redeem_command))
    app.add_handler(CommandHandler("referral", referral_command))

    # ── Admin upload (before admin_button to avoid overlap) ───────────────
    app.add_handler(CallbackQueryHandler(
        admin_upload_handler,
        pattern=r"^(aq_type_|aq_stream_|aq_mock_stream_|aq_mock_dept_|upload_subject_|aq_confirm_save|aq_dept_)",
    ))

    # ── Admin panel ───────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(
        admin_button_handler,
        pattern=r"^(admin_|aq_subject_|edit_q_field_|rcpt_ok_|rcpt_no_|vq_)",
    ))

    # ── Subscription flow ─────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(subscribe_handler,       pattern=r"^subscribe$"))
    app.add_handler(CallbackQueryHandler(sub_exam_select_handler, pattern=r"^sub_exam_"))
    app.add_handler(CallbackQueryHandler(sub_stream_select,       pattern=r"^sub_stream_"))
    app.add_handler(CallbackQueryHandler(sub_dept_select,         pattern=r"^sub_dept_"))
    app.add_handler(CallbackQueryHandler(pay_bank_handler,        pattern=r"^pay_"))
    app.add_handler(CallbackQueryHandler(send_receipt_handler,    pattern=r"^send_receipt$"))

    # ── Subscribed exam flow ──────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(my_subscribed_exams_handler, pattern=r"^my_sub_exams$"))
    app.add_handler(CallbackQueryHandler(sub_subject_handler,         pattern=r"^sub_subject_"))
    app.add_handler(CallbackQueryHandler(sub_year_select_handler,     pattern=r"^subexamyear_"))
    app.add_handler(CallbackQueryHandler(sub_start_exam_handler,      pattern=r"^substart_"))

    # ── Direct exam flow ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(direct_subject_handler, pattern=r"^direct_subject_"))
    app.add_handler(CallbackQueryHandler(start_exam_handler,     pattern=r"^start_exam_"))
    app.add_handler(CallbackQueryHandler(answer_handler,         pattern=r"^answer_"))
    app.add_handler(CallbackQueryHandler(next_question_handler,  pattern=r"^next_question$"))
    app.add_handler(CallbackQueryHandler(retry_exam_handler,     pattern=r"^retry_exam_"))
    app.add_handler(CallbackQueryHandler(leaderboard_handler,    pattern=r"^leaderboard$"))

    # ── Stream / dept navigation (pipe-separated: stream|entrance|natural) ─
    app.add_handler(CallbackQueryHandler(stream_select_handler, pattern=r"^stream\|"))
    app.add_handler(CallbackQueryHandler(dept_select_handler,   pattern=r"^dept\|"))

    # ── Mock / Model Exam ─────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(mock_menu_handler,       pattern=r"^exam_mock$"))
    app.add_handler(CallbackQueryHandler(mock_dept_group_handler, pattern=r"^mock_dept_group\|"))
    app.add_handler(CallbackQueryHandler(mock_subject_handler,    pattern=r"^mock_subject\|"))
    app.add_handler(CallbackQueryHandler(mock_start_handler,      pattern=r"^mock_start\|"))
    app.add_handler(CallbackQueryHandler(mock_answer_handler,     pattern=r"^mock_answer_"))
    app.add_handler(CallbackQueryHandler(mock_next_handler,       pattern=r"^mock_next$"))

    # ── Catch-all (main_menu, exam_, referral, redeem_menu, etc.) ─────────
    app.add_handler(CallbackQueryHandler(button_handler))

    # ── Messages ──────────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.PHOTO,                   receipt_photo_handler))
    app.add_handler(MessageHandler(filters.Document.TXT,            admin_file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))

    logger.info("Handlers registered. Polling...")
    app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()