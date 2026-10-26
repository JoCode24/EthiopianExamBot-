import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN  = os.getenv("BOT_TOKEN")
ADMIN_ID   = int(os.getenv("ADMIN_ID", 0))
ADMIN_PIN  = os.getenv("ADMIN_PIN", "1234")   # add ADMIN_PIN=yourpin to .env

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DATABASE_PATH = os.path.join(DATA_DIR, "exam_bot.db")

SUBSCRIPTION_PRICE_ETB     = 50
SUBSCRIPTION_DAYS          = 30
FREE_QUESTIONS_PER_SUBJECT = 5
FREE_MOCK_QUESTIONS = 15          # Free questions for mock/model exams
QUESTIONS_PER_EXAM         = 40
PASS_MARK_PERCENT          = 50
ADMIN_USERNAME             = "@John_3_13"
