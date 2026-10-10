import os

def w(path, content):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK: " + path)


# ── config.py ─────────────────────────────────────────────
w("config.py", '''import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
DATABASE_PATH = "data/exam_bot.db"

SUBSCRIPTION_PRICE_ETB = 50
SUBSCRIPTION_DAYS = 30
FREE_QUESTIONS_LIMIT = 3
QUESTIONS_PER_EXAM = 10
PASS_MARK_PERCENT = 50

PAYMENT_INFO = {
    "CBE": {
        "account": "1000482304102",
        "name": "Yohanes Alemu Mengesha",
        "editable": True
    },
    "Awash": {
        "account": "1000482304102",
        "name": "Yohanes Alemu Mengesha",
        "editable": True
    },
    "Dashen": {
        "account": "1000482304102",
        "name": "Yohanes Alemu Mengesha",
        "editable": True
    },
}

ADMIN_USERNAME = "@John_3_13"

EXAM_TYPES = {
    "entrance": "Entrance Exam (Grade 12)",
    "exit": "University Exit Exam",
    "coc": "CoC Exam (TVET)",
    "driving": "Driving Licence Exam",
    "remedial": "Remedial Exam",
}
''')


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
                exam_type TEXT,
                stream TEXT,
                department TEXT,
                is_subscribed INTEGER DEFAULT 0,
                subscribed_exam_type TEXT,
                subscribed_stream TEXT,
                subscribed_dept TEXT,
                subscription_expiry TEXT,
                free_access_expiry TEXT,
                free_questions_used INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                admin_role TEXT DEFAULT 'none',
                referral_code TEXT UNIQUE,
                referred_by TEXT,
                referral_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                last_active TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                role TEXT DEFAULT 'sub',
                added_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
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
                started_at TEXT DEFAULT (datetime('now')),
                finished_at TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL,
                stream TEXT,
                subject TEXT NOT NULL,
                level TEXT,
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
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL,
                stream TEXT,
                subject_key TEXT NOT NULL UNIQUE,
                subject_name TEXT NOT NULL,
                emoji TEXT DEFAULT 'BOOK',
                level TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL DEFAULT 'exit',
                dept_key TEXT NOT NULL UNIQUE,
                dept_name TEXT NOT NULL,
                emoji TEXT DEFAULT 'ORG'
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                full_name TEXT,
                amount REAL DEFAULT 50,
                bank TEXT,
                receipt_file_id TEXT,
                status TEXT DEFAULT 'pending',
                exam_type TEXT,
                stream TEXT,
                dept TEXT,
                reviewed_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                duration_days INTEGER NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                exam_type TEXT,
                created_by INTEGER,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_uses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                telegram_id INTEGER NOT NULL,
                used_at TEXT DEFAULT (datetime('now'))
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT UNIQUE NOT NULL,
                account_number TEXT NOT NULL,
                account_name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.commit()
        await seed_defaults(db)
        logger.info("Database initialized.")


async def seed_defaults(db):
    cur = await db.execute("SELECT COUNT(*) FROM subjects")
    if (await cur.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO subjects (exam_type,stream,subject_key,subject_name,emoji) VALUES (?,?,?,?,?)",
            [

    # Natural Science Stream
    ("entrance","natural","mathematics","Mathematics","MATH"),
    ("entrance","natural","physics","Physics","PHY"),
    ("entrance","natural","chemistry","Chemistry","CHEM"),
    ("entrance","natural","biology","Biology","BIO"),
    ("entrance","natural","english","English","ENG"),
    ("entrance","natural","aptitude","Scholastic Aptitude Test","SAT"),

    # Social Science Stream
    ("entrance","social","english","English","ENG"),
    ("entrance","social","mathematics","Mathematics","MATH"),
    ("entrance","social","history","History","HIST"),
    ("entrance","social","geography","Geography","GEO"),
    ("entrance","social","economics","Economics","ECO"),
    ("entrance","social","aptitude","Scholastic Aptitude Test","SAT"),
                # Natural Science Stream
    ("remedial","natural","mathematics","Mathematics","MATH"),
    ("remedial","natural","english","English","ENG"),
    ("remedial","natural","biology","Biology","BIO"),
    ("remedial","natural","chemistry","Chemistry","CHEM"),
    ("remedial","natural","physics","Physics","PHY"),
    ("remedial","natural","ict","Information and Communication Technology","ICT"),
    # Social Science Stream
    ("remedial","social","english","English","ENG"),
    ("remedial","social","mathematics","Mathematics","MATH"),
    ("remedial","social","history","History","HIST"),
    ("remedial","social","geography","Geography","GEO"),
    ("remedial","social","economics","Economics","ECO"),
    ("remedial","social","ict","Information and Communication Technology","ICT"),
    ("driving","general","traffic_law","Traffic Law","LAW"),
    ("driving","general","road_signs","Road Signs","SIGN"),
    ("driving","general","first_aid","First Aid","AID"),
    ("driving","general","vehicle_mechanics","Basic Vehicle Mechanics","MECH"),
    ("driving","general","safe_driving","Safe Driving Practices","SAFE"),
    ("driving","general","defensive_driving","Defensive Driving","DEF"),
    ("driving","general","road_safety","Road Safety","RS"),
    ("driving","general","driver_responsibility","Driver Responsibility","DR"),
    ("driving","general","vehicle_control","Vehicle Control","CTRL"),
    ("driving","general","accident_prevention","Accident Prevention","AP"),
    ("driving","general","environmental_driving","Eco-Friendly Driving","ECO"),
    ("driving","general","transport_regulations","Transport Regulations","REG"),
            ]
        )

    cur2 = await db.execute("SELECT COUNT(*) FROM departments")
    if (await cur2.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO departments (exam_type,dept_key,dept_name,emoji) VALUES (?,?,?,?)",
            [
    ("exit","computer_science","Computer Science","CS"),
    ("exit","software_engineering","Software Engineering","SE"),
    ("exit","information_systems","Information Systems","IS"),
    ("exit","information_technology","Information Technology","IT"),
    ("exit","information_science","Information Science","INS"),
    ("exit","accounting","Accounting and Finance","ACC"),
    ("exit","banking_finance","Banking and Finance","BF"),
    ("exit","management","Management","MGT"),
    ("exit","business_management","Business Management","BIZ"),
    ("exit","marketing_management","Marketing Management","MM"),
    ("exit","economics","Economics","ECO"),
    ("exit","development_economics","Development Economics","DE"),
    ("exit","cooperative_business_management","Cooperative Business Management","CBM"),
    ("exit","law","Law","LAW"),
    ("exit","medicine","Doctor of Medicine","MED"),
    ("exit","nursing","Comprehensive Nursing","NUR"),
    ("exit","pharmacy","Pharmacy","PHR"),
    ("exit","public_health","Public Health Officer","PHO"),
    ("exit","midwifery","Midwifery","MID"),
    ("exit","anesthesia","Anesthesia","ANE"),
    ("exit","environmental_health","Environmental Health","EH"),
    ("exit","veterinary_medicine","Veterinary Medicine","VM"),
    ("exit","civil_engineering","Civil Engineering","CE"),
    ("exit","mechanical_engineering","Mechanical Engineering","ME"),
    ("exit","electrical_engineering","Electrical and Computer Engineering","ECE"),
    ("exit","computer_engineering","Computer Engineering","CPE"),
    ("exit","chemical_engineering","Chemical Engineering","CHE"),
    ("exit","manufacturing_engineering","Manufacturing Engineering","MFE"),
    ("exit","water_resource_engineering","Water Resource and Irrigation Engineering","WRIE"),
    ("exit","construction_management","Construction Technology and Management","CTM"),
    ("exit","architecture","Architecture","ARCH"),
    ("exit","agricultural_engineering","Agricultural Engineering","AGE"),
    ("exit","agricultural_economics","Agricultural Economics","AGEC"),
    ("exit","agribusiness","Agribusiness and Value Chain Management","ABM"),
    ("exit","plant_science","Plant Science","PS"),
    ("exit","animal_science","Animal Science","ANS"),
    ("exit","animal_range_science","Animal and Range Science","ARS"),
    ("exit","natural_resource_management","Natural Resource Management","NRM"),
    ("exit","forestry","Forestry","FOR"),
    ("exit","biology","Biology","BIO"),
    ("exit","chemistry","Chemistry","CHEM"),
    ("exit","physics","Physics","PHY"),
    ("exit","mathematics","Mathematics","MATH"),
    ("exit","statistics","Statistics","STAT"),
    ("exit","biotechnology","Biotechnology","BT"),
    ("exit","english","English Language and Literature","ENG"),
    ("exit","psychology","Psychology","PSY"),
    ("exit","sociology","Sociology","SOC"),
    ("exit","journalism","Journalism","JRN"),
    ("exit","communication","Communication and Media Studies","CMS"),
    ("exit","history","History","HIS"),
    ("exit","geography","Geography and Environmental Studies","GES"),
    ("exit","political_science","Political Science","POL"),
    ("exit","tourism_hospitality","Tourism and Hotel Management","THM"),
    ("exit","sport_science","Sport Science","SPS"),
    ("exit","environmental_science","Environmental Science","ENV"),
    ("coc","coc_electrical","Electrical Installation Level I-IV","ELE"),
    ("coc","coc_electronics","Electronics Technology","ELX"),
    ("coc","coc_construction","Construction and Civil Works","CON"),
    ("coc","coc_civil","Civil Engineering Technology","CIV"),
    ("coc","coc_mechanical","Mechanical Technology","MECH"),
    ("coc","coc_manufacturing","Manufacturing Technology","MFG"),
    ("coc","coc_welding","Welding and Metal Fabrication","WLD"),
    ("coc","coc_plumbing","Plumbing and Pipe Installation","PLB"),
    ("coc","coc_it","Information Technology","IT"),
    ("coc","coc_hardware","Computer Hardware and Networking","CHN"),
    ("coc","coc_software","Software Development","SWD"),
    ("coc","coc_database","Database Administration","DBA"),
    ("coc","coc_automotive","Automotive Technology","AUTO"),
    ("coc","coc_auto_electric","Automotive Electrician","AUE"),
    ("coc","coc_agriculture","Agriculture","AGR"),
    ("coc","coc_animal","Animal Production","ANP"),
    ("coc","coc_plant","Plant Science","PLS"),
    ("coc","coc_accounting","Accounting","ACC"),
    ("coc","coc_management","Management","MGT"),
    ("coc","coc_marketing","Marketing Management","MKT"),
    ("coc","coc_banking","Banking and Finance","BNK"),
    ("coc","coc_secretarial","Secretarial Science","SEC"),
    ("coc","coc_logistics","Logistics and Supply Chain","LOG"),
    ("coc","coc_hotel","Hotel Management","HTL"),
    ("coc","coc_tourism","Tourism Management","TOU"),
    ("coc","coc_food","Food Preparation","FPT"),
    ("coc","coc_housekeeping","Housekeeping Operations","HKP"),
    ("coc","coc_nursing","Nursing Assistant","NUR"),
    ("coc","coc_pharmacy","Pharmacy Technician","PHT"),
    ("coc","coc_lab","Medical Laboratory Technician","MLT"),
    ("coc","coc_midwifery","Midwifery Assistant","MID"),
    ("coc","coc_garment","Garment Production","GAR"),
    ("coc","coc_textile","Textile Technology","TXT"),
    ("coc","coc_leather","Leather Processing","LTH"),
    ("coc","coc_beauty","Beauty Therapy","BEA"),
    ("coc","coc_hairdressing","Hairdressing","HRD"),
    ("coc","coc_graphics","Graphic Design","GRD"),
    ("coc","coc_printing","Printing Technology","PRT"),
    ("coc","coc_water","Water Supply Technology","WST"),
    ("coc","coc_masonry","Masonry","MAS"),
    ("coc","coc_woodwork","Wood Work Technology","WWT"),
    ("coc","coc_furniture","Furniture Making","FUR"),

            ]
        )

    cur3 = await db.execute("SELECT COUNT(*) FROM bank_accounts")
    if (await cur3.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO bank_accounts (bank_name,account_number,account_name) VALUES (?,?,?)",
            [
                ("CBE","1000482304102","Yohanes Alemu Mengesha"),
                ("Awash","1000482304102","Yohanes Alemu Mengesha"),
                ("Dashen","1000482304102","Yohanes Alemu Mengesha"),
            ]
        )
    await db.commit()


def get_db():
    os.makedirs("data", exist_ok=True)
    return aiosqlite.connect(DATABASE_PATH)
''')


# ── app/utils/access.py ───────────────────────────────────
w("app/utils/access.py", '''import aiosqlite
from config import DATABASE_PATH, ADMIN_ID, FREE_QUESTIONS_LIMIT
from datetime import datetime


async def get_user(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def is_super_admin(telegram_id):
    if telegram_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT role FROM admin_users WHERE telegram_id=? AND role=\'super\'",
            (telegram_id,))
        return bool(await cur.fetchone())


async def is_any_admin(telegram_id):
    if telegram_id == ADMIN_ID:
        return True
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id FROM admin_users WHERE telegram_id=?", (telegram_id,))
        return bool(await cur.fetchone())


async def get_admin_role(telegram_id):
    if telegram_id == ADMIN_ID:
        return "super"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT role FROM admin_users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def has_full_access(user: dict, exam_type: str, stream: str = None, dept: str = None):
    if not user:
        return False

    now = datetime.utcnow().isoformat()

    if user.get("free_access_expiry") and user["free_access_expiry"] > now:
        return True

    if not user.get("is_subscribed"):
        return False

    expiry = user.get("subscription_expiry", "")
    if expiry and expiry < now:
        return False

    sub_exam = user.get("subscribed_exam_type", "")
    if sub_exam != exam_type:
        return False

    if exam_type == "entrance":
        return user.get("subscribed_stream") == stream
    elif exam_type in ("exit", "coc"):
        return user.get("subscribed_dept") == dept

    return True


async def can_do_free_question(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT free_questions_used FROM users WHERE telegram_id=?",
            (telegram_id,))
        row = await cur.fetchone()
        used = row[0] if row else 0
        return used < FREE_QUESTIONS_LIMIT, used


async def increment_free_questions(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET free_questions_used=free_questions_used+1 "
            "WHERE telegram_id=?", (telegram_id,))
        await db.commit()
''')


# ── app/keyboards/main_menu.py ────────────────────────────
w("app/keyboards/main_menu.py", '''from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Entrance Exam", callback_data="exam_type_entrance")],
        [InlineKeyboardButton("University Exit Exam", callback_data="exam_type_exit")],
        [InlineKeyboardButton("CoC Exam (TVET)", callback_data="exam_type_coc")],
        [InlineKeyboardButton("Driving Licence Exam", callback_data="exam_type_driving")],
        [InlineKeyboardButton("Remedial Exam", callback_data="exam_type_remedial")],
        [InlineKeyboardButton("Start Practice Exam", callback_data="choose_subject")],
        [InlineKeyboardButton("My Progress", callback_data="my_progress")],
        [InlineKeyboardButton("Subscribe - 50 ETB/month", callback_data="subscribe")],
        [InlineKeyboardButton("Referral - Earn Free Access", callback_data="show_referral")],
        [InlineKeyboardButton("Help", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def stream_keyboard():
    keyboard = [
        [InlineKeyboardButton("Natural Science", callback_data="stream_natural")],
        [InlineKeyboardButton("Social Science", callback_data="stream_social")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def remedial_stream_keyboard():
    keyboard = [
        [InlineKeyboardButton("Natural Science", callback_data="remedial_stream_natural")],
        [InlineKeyboardButton("Social Science", callback_data="remedial_stream_social")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_dept_select_keyboard(depts):
    keyboard = []
    for d in depts:
        keyboard.append([InlineKeyboardButton(
            d["dept_name"],
            callback_data="dept_" + d["dept_key"])])
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def back_to_main_keyboard():
    keyboard = [[InlineKeyboardButton("Back to Main Menu", callback_data="back_main")]]
    return InlineKeyboardMarkup(keyboard)


def subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("Pay via CBE", callback_data="pay_CBE")],
        [InlineKeyboardButton("Pay via Awash Bank", callback_data="pay_Awash")],
        [InlineKeyboardButton("Pay via Dashen Bank", callback_data="pay_Dashen")],
        [InlineKeyboardButton("I Already Paid - Send Receipt", callback_data="send_receipt")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def after_payment_keyboard():
    keyboard = [
        [InlineKeyboardButton("Send Payment Screenshot", callback_data="send_receipt")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def exam_select_keyboard():
    keyboard = [
        [InlineKeyboardButton("Entrance Exam", callback_data="sub_exam_entrance")],
        [InlineKeyboardButton("University Exit Exam", callback_data="sub_exam_exit")],
        [InlineKeyboardButton("CoC Exam", callback_data="sub_exam_coc")],
        [InlineKeyboardButton("Driving Licence", callback_data="sub_exam_driving")],
        [InlineKeyboardButton("Remedial Exam", callback_data="sub_exam_remedial")],
        [InlineKeyboardButton("Back", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)
''')


# ── app/keyboards/admin_menu.py ───────────────────────────
w("app/keyboards/admin_menu.py", '''from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard(role="super"):
    keyboard = []
    keyboard.append([InlineKeyboardButton("Add Question (Manual)", callback_data="admin_add_question")])
    keyboard.append([InlineKeyboardButton("Upload Question File", callback_data="admin_upload_file")])
    keyboard.append([InlineKeyboardButton("Edit Question", callback_data="admin_edit_question")])
    keyboard.append([InlineKeyboardButton("Delete Question", callback_data="admin_delete_question")])
    keyboard.append([InlineKeyboardButton("View Questions", callback_data="admin_view_questions")])
    keyboard.append([InlineKeyboardButton("Manage Subjects", callback_data="admin_manage_subjects")])
    keyboard.append([InlineKeyboardButton("Manage Departments", callback_data="admin_manage_depts")])
    keyboard.append([InlineKeyboardButton("View Users", callback_data="admin_view_users")])
    keyboard.append([InlineKeyboardButton("Grant Subscription", callback_data="admin_grant_sub")])
    keyboard.append([InlineKeyboardButton("Giveaway Free Access", callback_data="admin_giveaway")])
    keyboard.append([InlineKeyboardButton("Broadcast Message", callback_data="admin_broadcast")])
    keyboard.append([InlineKeyboardButton("Pending Receipts", callback_data="admin_pending_receipts")])
    if role == "super":
        keyboard.append([InlineKeyboardButton("Manage Admins", callback_data="admin_manage_admins")])
        keyboard.append([InlineKeyboardButton("Edit Bank Accounts", callback_data="admin_edit_banks")])
        keyboard.append([InlineKeyboardButton("Statistics", callback_data="admin_stats")])
    keyboard.append([InlineKeyboardButton("Close Panel", callback_data="admin_close")])
    return InlineKeyboardMarkup(keyboard)


def admin_back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Back to Admin", callback_data="admin_back")]])


def admin_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Confirm", callback_data="aq_confirm_save")],
        [InlineKeyboardButton("Cancel", callback_data="admin_cancel_question")],
    ])


def admin_exam_type_keyboard():
    keyboard = [
        [InlineKeyboardButton("Entrance Exam", callback_data="aq_type_entrance")],
        [InlineKeyboardButton("Exit Exam", callback_data="aq_type_exit")],
        [InlineKeyboardButton("CoC Exam", callback_data="aq_type_coc")],
        [InlineKeyboardButton("Driving Licence", callback_data="aq_type_driving")],
        [InlineKeyboardButton("Remedial Exam", callback_data="aq_type_remedial")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_stream_keyboard():
    keyboard = [
        [InlineKeyboardButton("Natural Science", callback_data="aq_stream_natural")],
        [InlineKeyboardButton("Social Science", callback_data="aq_stream_social")],
        [InlineKeyboardButton("General", callback_data="aq_stream_general")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_subject_keyboard(subjects, prefix="aq_subject_"):
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(
            s["subject_name"],
            callback_data=prefix + s["subject_key"])])
    keyboard.append([InlineKeyboardButton("Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def build_dept_keyboard(depts, prefix="aq_dept_"):
    keyboard = []
    for d in depts:
        keyboard.append([InlineKeyboardButton(
            d["dept_name"],
            callback_data=prefix + d["dept_key"])])
    keyboard.append([InlineKeyboardButton("Back", callback_data="admin_back")])
    return InlineKeyboardMarkup(keyboard)


def manage_subjects_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Subject", callback_data="admin_add_subject")],
        [InlineKeyboardButton("Edit Subject", callback_data="admin_edit_subject")],
        [InlineKeyboardButton("Delete Subject", callback_data="admin_delete_subject")],
        [InlineKeyboardButton("View All Subjects", callback_data="admin_list_subjects")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ])


def manage_depts_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Department", callback_data="admin_add_dept")],
        [InlineKeyboardButton("Edit Department", callback_data="admin_edit_dept")],
        [InlineKeyboardButton("Delete Department", callback_data="admin_delete_dept")],
        [InlineKeyboardButton("View All Departments", callback_data="admin_list_depts")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ])


def manage_admins_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Add Sub Admin", callback_data="admin_add_subadmin")],
        [InlineKeyboardButton("Remove Admin", callback_data="admin_remove_admin")],
        [InlineKeyboardButton("View All Admins", callback_data="admin_list_admins")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ])


def giveaway_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Create Giveaway Code", callback_data="admin_create_giveaway")],
        [InlineKeyboardButton("View Active Codes", callback_data="admin_list_giveaways")],
        [InlineKeyboardButton("Back", callback_data="admin_back")],
    ])


def receipt_action_keyboard(payment_id, telegram_id, exam_type, stream, dept):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Approve - Grant Access",
            callback_data="receipt_approve_" + str(payment_id) + "_" + str(telegram_id) +
                          "_" + str(exam_type) + "_" + str(stream) + "_" + str(dept))],
        [InlineKeyboardButton(
            "Reject",
            callback_data="receipt_reject_" + str(payment_id) + "_" + str(telegram_id))],
    ])
''')


# ── app/handlers/subscription.py ─────────────────────────
w("app/handlers/subscription.py", '''from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.main_menu import (
    subscription_keyboard, back_to_main_keyboard,
    exam_select_keyboard, stream_keyboard, build_dept_select_keyboard,
)
from config import DATABASE_PATH, ADMIN_USERNAME, SUBSCRIPTION_PRICE_ETB
from app.utils.logger import logger
import aiosqlite


async def get_banks():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM bank_accounts WHERE is_active=1 ORDER BY bank_name")
        return [dict(r) for r in await cur.fetchall()]


async def get_exit_depts():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=\'exit\' ORDER BY dept_name")
        return [dict(r) for r in await cur.fetchall()]


async def get_coc_depts():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=\'coc\' ORDER BY dept_name")
        return [dict(r) for r in await cur.fetchall()]


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "SUBSCRIPTION - " + str(SUBSCRIPTION_PRICE_ETB) + " ETB/month\n\n"
        "Choose your exam type first, then pay.\n"
        "After payment, send your receipt screenshot.\n"
        "Admin will activate your access within a few hours.\n\n"
        "Choose which exam you want to subscribe to:",
        reply_markup=exam_select_keyboard())


async def sub_exam_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    exam_type = data.replace("sub_exam_", "")
    context.user_data["sub_exam_type"] = exam_type

    if exam_type == "entrance":
        await query.edit_message_text(
            "Entrance Exam Subscription\n\nChoose your stream:",
            reply_markup=stream_keyboard())
    elif exam_type == "exit":
        depts = await get_exit_depts()
        await query.edit_message_text(
            "Exit Exam Subscription\n\nChoose your department:",
            reply_markup=build_dept_select_keyboard(depts))
    elif exam_type == "coc":
        depts = await get_coc_depts()
        await query.edit_message_text(
            "CoC Exam Subscription\n\nChoose your department:",
            reply_markup=build_dept_select_keyboard(depts))
    elif exam_type in ("driving", "remedial"):
        context.user_data["sub_stream"] = "general"
        context.user_data["sub_dept"] = ""
        await show_payment_options(query, context)


async def sub_stream_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stream = query.data.replace("stream_", "")
    context.user_data["sub_stream"] = stream
    context.user_data["sub_dept"] = ""
    await show_payment_options(query, context)


async def sub_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dept = query.data.replace("dept_", "")
    context.user_data["sub_dept"] = dept
    context.user_data["sub_stream"] = ""
    await show_payment_options(query, context)


async def show_payment_options(query, context):
    banks = await get_banks()
    exam_type = context.user_data.get("sub_exam_type", "")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")

    label = exam_type.title()
    if stream:
        label += " / " + stream.title()
    if dept:
        label += " / " + dept.replace("_", " ").title()

    bank_text = ""
    for b in banks:
        bank_text += b["bank_name"] + "\n"
        bank_text += "Account: " + b["account_number"] + "\n"
        bank_text += "Name: " + b["account_name"] + "\n\n"

    await query.edit_message_text(
        "PAYMENT DETAILS\n\n"
        "Selected: " + label + "\n"
        "Amount: " + str(SUBSCRIPTION_PRICE_ETB) + " ETB\n\n"
        "Send payment to any of these accounts:\n\n" +
        bank_text +
        "After paying, take a screenshot and send it here.\n"
        "Admin: " + ADMIN_USERNAME + "\n\n"
        "Tap the button below to send your receipt:",
        reply_markup=subscription_keyboard())


async def pay_bank_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bank = query.data.replace("pay_", "")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM bank_accounts WHERE bank_name=?", (bank,))
        b = await cur.fetchone()

    if not b:
        await query.edit_message_text("Bank info not found.", reply_markup=back_to_main_keyboard())
        return

    context.user_data["selected_bank"] = bank
    await query.edit_message_text(
        "PAY VIA " + bank.upper() + "\n\n"
        "Account Number: " + b["account_number"] + "\n"
        "Account Name: " + b["account_name"] + "\n"
        "Amount: " + str(SUBSCRIPTION_PRICE_ETB) + " ETB\n\n"
        "Steps:\n"
        "1. Open your " + bank + " app or go to the bank\n"
        "2. Transfer " + str(SUBSCRIPTION_PRICE_ETB) + " ETB to the account above\n"
        "3. Take a screenshot of the receipt\n"
        "4. Come back here and tap Send Receipt\n\n"
        "After sending receipt, admin will activate your account.",
        reply_markup=subscription_keyboard())


async def send_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for"] = "receipt_photo"
    await query.edit_message_text(
        "Send Payment Receipt\n\n"
        "Please send a PHOTO or SCREENSHOT of your payment receipt now.\n\n"
        "Make sure the screenshot clearly shows:\n"
        "- Your name\n"
        "- Amount paid\n"
        "- Date and time\n"
        "- Transaction reference\n\n"
        "Send the photo now:")


async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if context.user_data.get("waiting_for") != "receipt_photo":
        return

    photo = update.message.photo
    if not photo:
        await update.message.reply_text(
            "Please send a photo/screenshot, not a file.")
        return

    file_id = photo[-1].file_id
    exam_type = context.user_data.get("sub_exam_type", "entrance")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")
    bank = context.user_data.get("selected_bank", "Unknown")
    context.user_data["waiting_for"] = None

    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payments (telegram_id,full_name,bank,receipt_file_id,exam_type,stream,dept) "
            "VALUES (?,?,?,?,?,?,?)",
            (user.id, user.full_name, bank, file_id, exam_type, stream, dept))
        payment_id = cur.lastrowid
        await db.commit()

    await update.message.reply_text(
        "Receipt received! Thank you.\n\n"
        "Admin will review and activate your access soon.\n"
        "You will get a notification when approved.\n\n"
        "Admin: " + ADMIN_USERNAME,
        reply_markup=back_to_main_keyboard())
    logger.info("Receipt from user " + str(user.id) + " payment " + str(payment_id))

    from config import ADMIN_ID
    try:
        label = exam_type.title()
        if stream:
            label += "/" + stream
        if dept:
            label += "/" + dept
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption="NEW PAYMENT RECEIPT\n\n"
                    "User: " + (user.full_name or "Unknown") + "\n"
                    "ID: " + str(user.id) + "\n"
                    "Bank: " + bank + "\n"
                    "Exam: " + label + "\n"
                    "Payment ID: " + str(payment_id) + "\n\n"
                    "Use /admin to approve or reject.")
    except Exception:
        pass
''')


# ── app/handlers/admin.py ─────────────────────────────────
w("app/handlers/admin.py", '''from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.admin_menu import (
    admin_main_keyboard, admin_back_keyboard, admin_confirm_keyboard,
    admin_exam_type_keyboard, admin_stream_keyboard,
    build_subject_keyboard, build_dept_keyboard,
    manage_subjects_keyboard, manage_depts_keyboard,
    manage_admins_keyboard, giveaway_keyboard, receipt_action_keyboard,
)
from app.utils.access import is_super_admin, is_any_admin, get_admin_role
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
            "SELECT * FROM subjects WHERE exam_type=? AND (stream=? OR stream IS NULL) ORDER BY subject_name",
            (exam_type, stream))
        return [dict(r) for r in await cur.fetchall()]


async def get_depts(exam_type="exit"):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=? ORDER BY dept_name", (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_any_admin(uid):
        await update.message.reply_text("Unauthorized.")
        return
    role = await get_admin_role(uid)
    await update.message.reply_text(
        "Admin Panel\n\nRole: " + (role or "super").upper(),
        reply_markup=admin_main_keyboard(role or "super"))


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id

    if not await is_any_admin(uid):
        await query.edit_message_text("Unauthorized.")
        return

    role = await get_admin_role(uid)
    is_super = (role == "super")

    if data == "admin_back":
        await query.edit_message_text(
            "Admin Panel",
            reply_markup=admin_main_keyboard(role or "super"))

    elif data == "admin_close":
        await query.edit_message_text("Panel closed.")

    elif data == "admin_view_users":
        await show_users(query)

    elif data == "admin_stats":
        if not is_super:
            await query.edit_message_text("No permission.", reply_markup=admin_back_keyboard())
            return
        await show_stats(query)

    elif data == "admin_view_questions":
        await show_questions(query)

    elif data == "admin_manage_subjects":
        await query.edit_message_text("Manage Subjects", reply_markup=manage_subjects_keyboard())

    elif data == "admin_manage_depts":
        await query.edit_message_text("Manage Departments", reply_markup=manage_depts_keyboard())

    elif data == "admin_manage_admins":
        if not is_super:
            await query.edit_message_text("No permission.", reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("Manage Admins", reply_markup=manage_admins_keyboard())

    elif data == "admin_list_admins":
        await list_admins(query)

    elif data == "admin_add_subadmin":
        if not is_super:
            await query.edit_message_text("No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "add_subadmin"
        await query.edit_message_text(
            "Add Sub Admin\n\n"
            "Send the Telegram ID of the person to make sub admin.\n"
            "They must have started the bot first.\n\n"
            "Type /cancel to abort.")

    elif data == "admin_remove_admin":
        if not is_super:
            await query.edit_message_text("No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "remove_admin"
        await query.edit_message_text(
            "Remove Admin\n\n"
            "Send the Telegram ID of the admin to remove.\n\n"
            "Type /cancel to abort.")

    elif data == "admin_add_subject":
        context.user_data["waiting_for"] = "new_subject_info"
        await query.edit_message_text(
            "Add Subject\n\n"
            "Send in this format:\n"
            "exam_type|stream|key|name\n\n"
            "exam_type options: entrance, exit, coc, driving, remedial\n"
            "stream options: natural, social, general, exit (for exit exam)\n\n"
            "Examples:\n"
            "entrance|natural|physics|Physics\n"
            "coc|coc_electrical|coc_elec_l1|Electrical Level 1\n"
            "driving|general|traffic_law|Traffic Law\n\n"
            "Type /cancel to abort.")

    elif data == "admin_edit_subject":
        context.user_data["waiting_for"] = "edit_subject_info"
        await query.edit_message_text(
            "Edit Subject\n\n"
            "Format: old_key|new_name\n\n"
            "Example: physics|Advanced Physics\n\n"
            "Type /cancel to abort.")

    elif data == "admin_delete_subject":
        context.user_data["waiting_for"] = "delete_subject_key"
        await query.edit_message_text(
            "Delete Subject\n\n"
            "Send the subject key.\n"
            "Use View Subjects to find keys.\n\n"
            "Type /cancel to abort.")

    elif data == "admin_list_subjects":
        await list_subjects(query)

    elif data == "admin_add_dept":
        context.user_data["waiting_for"] = "new_dept_info"
        await query.edit_message_text(
            "Add Department\n\n"
            "Format: exam_type|key|name\n\n"
            "exam_type: exit or coc\n\n"
            "Examples:\n"
            "exit|nursing|Nursing\n"
            "coc|coc_welding|Welding\n\n"
            "Type /cancel to abort.")

    elif data == "admin_edit_dept":
        context.user_data["waiting_for"] = "edit_dept_info"
        await query.edit_message_text(
            "Edit Department\n\n"
            "Format: old_key|new_name\n\n"
            "Example: law|Ethiopian Law\n\n"
            "Type /cancel to abort.")

    elif data == "admin_delete_dept":
        context.user_data["waiting_for"] = "delete_dept_key"
        await query.edit_message_text(
            "Delete Department\n\n"
            "Send the department key.\n\n"
            "Type /cancel to abort.")

    elif data == "admin_list_depts":
        await list_depts(query)

    elif data == "admin_add_question":
        context.user_data.clear()
        await query.edit_message_text(
            "Add Question\n\nChoose exam type:",
            reply_markup=admin_exam_type_keyboard())

    elif data == "admin_edit_question":
        context.user_data["waiting_for"] = "edit_question_id"
        await query.edit_message_text(
            "Edit Question\n\n"
            "Send the question ID.\n"
            "Use View Questions to find IDs.\n\n"
            "Type /cancel to abort.")

    elif data == "admin_delete_question":
        context.user_data["waiting_for"] = "delete_question_id"
        await query.edit_message_text(
            "Delete Question\n\n"
            "Send the question ID.\n\n"
            "Type /cancel to abort.")

    elif data == "admin_upload_file":
        context.user_data["waiting_for"] = "question_file"
        await query.edit_message_text(
            "Upload Question File\n\n"
            "Send a .txt file with this format:\n\n"
            "Q: Question text\n"
            "A) Option A\n"
            "B) Option B\n"
            "C) Option C\n"
            "D) Option D\n"
            "Answer: B\n"
            "Explanation: reason\n"
            "Reference: Grade 12 Book\n"
            "Year: 2023\n\n"
            "Separate questions with a blank line.")

    elif data == "admin_grant_sub":
        context.user_data["waiting_for"] = "grant_sub_info"
        await query.edit_message_text(
            "Grant Subscription\n\n"
            "Format: telegram_id|days|exam_type|stream_or_dept\n\n"
            "Examples:\n"
            "123456789|30|entrance|natural\n"
            "123456789|30|exit|medicine\n"
            "123456789|30|coc|coc_electrical\n"
            "123456789|30|driving|general\n\n"
            "Type /cancel to abort.")

    elif data == "admin_giveaway":
        await query.edit_message_text("Giveaway Free Access", reply_markup=giveaway_keyboard())

    elif data == "admin_create_giveaway":
        context.user_data["waiting_for"] = "giveaway_info"
        await query.edit_message_text(
            "Create Giveaway Code\n\n"
            "Format: days|max_uses\n\n"
            "Examples:\n"
            "7|100   (7 days free, 100 students)\n"
            "30|1    (30 days, 1 student only)\n"
            "3|500   (3 days, 500 students)\n\n"
            "Type /cancel to abort.")

    elif data == "admin_list_giveaways":
        await list_giveaways(query)

    elif data == "admin_broadcast":
        context.user_data["waiting_for"] = "broadcast_msg"
        await query.edit_message_text(
            "Broadcast Message\n\n"
            "Type message to send to ALL users.\n"
            "Type /cancel to abort.")

    elif data == "admin_pending_receipts":
        await show_pending_receipts(query, context)

    elif data == "admin_edit_banks":
        if not is_super:
            await query.edit_message_text("No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "edit_bank_info"
        await query.edit_message_text(
            "Edit Bank Account\n\n"
            "Format: bank_name|account_number|account_name\n\n"
            "bank_name options: CBE, Awash, Dashen\n\n"
            "Example:\n"
            "CBE|1000482304102|Yohanes Alemu Mengesha\n\n"
            "To add new bank:\n"
            "NewBank|0912345678|Account Name\n\n"
            "Type /cancel to abort.")

    elif data == "admin_cancel_question":
        context.user_data.clear()
        await query.edit_message_text("Cancelled.", reply_markup=admin_main_keyboard(role or "super"))

    elif data.startswith("aq_subject_"):
        subject = data.replace("aq_subject_", "")
        context.user_data["aq_subject"] = subject
        context.user_data["aq_subject_label"] = subject.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            "Subject: " + context.user_data["aq_subject_label"] + "\n\n"
            "Type the question text:\n"
            "Type /cancel to abort.")

    elif data.startswith("aq_dept_"):
        dept = data.replace("aq_dept_", "")
        context.user_data["aq_stream"] = dept
        context.user_data["aq_subject"] = dept
        context.user_data["aq_subject_label"] = dept.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            "Department: " + context.user_data["aq_subject_label"] + "\n\n"
            "Type the question text:\n"
            "Type /cancel to abort.")

    elif data.startswith("edit_q_field_"):
        field = data.replace("edit_q_field_", "")
        context.user_data["edit_field"] = field
        context.user_data["waiting_for"] = "edit_q_value"
        field_labels = {
            "question_text": "question text",
            "option_a": "Option A", "option_b": "Option B",
            "option_c": "Option C", "option_d": "Option D",
            "correct_answer": "correct answer (A/B/C/D)",
            "explanation": "explanation", "reference": "reference",
            "year": "year (number or none)",
        }
        await query.edit_message_text(
            "Send the new " + field_labels.get(field, field) + ":")

    elif data.startswith("receipt_approve_"):
        await approve_receipt(query, context, data)

    elif data.startswith("receipt_reject_"):
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
        await query.edit_message_text("Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_type_exit":
        context.user_data["aq_exam_type"] = "exit"
        if has_upload:
            context.user_data["upload_exam_type"] = "exit"
        depts = await get_depts("exit")
        await query.edit_message_text(
            "Choose department:", reply_markup=build_dept_keyboard(depts))

    elif data == "aq_type_coc":
        context.user_data["aq_exam_type"] = "coc"
        if has_upload:
            context.user_data["upload_exam_type"] = "coc"
        depts = await get_depts("coc")
        await query.edit_message_text(
            "Choose CoC department:", reply_markup=build_dept_keyboard(depts))

    elif data == "aq_type_driving":
        context.user_data["aq_exam_type"] = "driving"
        context.user_data["aq_stream"] = "general"
        if has_upload:
            context.user_data["upload_exam_type"] = "driving"
            context.user_data["upload_stream"] = "general"
        subjects = await get_subjects("driving", "general")
        await query.edit_message_text(
            "Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data == "aq_type_remedial":
        context.user_data["aq_exam_type"] = "remedial"
        if has_upload:
            context.user_data["upload_exam_type"] = "remedial"
        await query.edit_message_text("Choose stream:", reply_markup=admin_stream_keyboard())

    elif data == "aq_stream_natural":
        exam_type = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "natural"
        if has_upload:
            context.user_data["upload_stream"] = "natural"
        subjects = await get_subjects(exam_type, "natural")
        if has_upload:
            await query.edit_message_text(
                "Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data == "aq_stream_social":
        exam_type = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "social"
        if has_upload:
            context.user_data["upload_stream"] = "social"
        subjects = await get_subjects(exam_type, "social")
        if has_upload:
            await query.edit_message_text(
                "Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data == "aq_stream_general":
        exam_type = context.user_data.get("aq_exam_type", "driving")
        context.user_data["aq_stream"] = "general"
        if has_upload:
            context.user_data["upload_stream"] = "general"
        subjects = await get_subjects(exam_type, "general")
        if has_upload:
            await query.edit_message_text(
                "Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "Choose subject:", reply_markup=build_subject_keyboard(subjects))

    elif data.startswith("upload_subject_"):
        subject = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream = context.user_data.get("upload_stream", "natural")
        await query.edit_message_text(
            "Ready to save " + str(len(parsed)) + " questions\n"
            "Subject: " + subject.replace("_", " ").title() + "\n"
            "Exam: " + exam_type.title() + " Stream: " + stream.title() + "\n\nConfirm?",
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
        await update.message.reply_text("Cancelled.", reply_markup=admin_main_keyboard(role or "super"))
        return

    simple_steps = {
        "aq_question_text": ("aq_option_a", "OK. Type Option A:"),
        "aq_option_a": ("aq_option_b", "OK. Type Option B:"),
        "aq_option_b": ("aq_option_c", "OK. Type Option C:"),
        "aq_option_c": ("aq_option_d", "OK. Type Option D:"),
    }

    if waiting in simple_steps:
        context.user_data[waiting] = text
        nxt, msg = simple_steps[waiting]
        context.user_data["waiting_for"] = nxt
        await update.message.reply_text(msg)

    elif waiting == "aq_option_d":
        context.user_data["aq_option_d"] = text
        context.user_data["waiting_for"] = "aq_correct_answer"
        await update.message.reply_text("Correct answer: A, B, C, or D")

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
            "Subject: " + str(d.get("aq_subject_label")) + "\n"
            "Exam: " + str(d.get("aq_exam_type", "")).title() + "\n"
            "Stream: " + str(d.get("aq_stream", "")).title() + "\n"
            "Year: " + str(d.get("aq_year") or "N/A") + "\n\n"
            "Q: " + str(d.get("aq_question_text")) + "\n\n"
            "A) " + str(d.get("aq_option_a")) + "\n"
            "B) " + str(d.get("aq_option_b")) + "\n"
            "C) " + str(d.get("aq_option_c")) + "\n"
            "D) " + str(d.get("aq_option_d")) + "\n\n"
            "Answer: " + str(d.get("aq_correct_answer")) + "\n"
            "Explanation: " + str(d.get("aq_explanation")) + "\n"
            "Reference: " + str(d.get("aq_reference") or "N/A")
        )
        await update.message.reply_text(preview, reply_markup=admin_confirm_keyboard())

    elif waiting == "grant_sub_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 4:
            await update.message.reply_text(
                "Wrong format.\n"
                "Use: telegram_id|days|exam_type|stream_or_dept\n\n"
                "Example: 123456789|30|entrance|natural")
            return
        try:
            tid = int(parts[0])
            days = int(parts[1])
        except ValueError:
            await update.message.reply_text("ID and days must be numbers.")
            return
        exam_type = parts[2].strip()
        stream_or_dept = parts[3].strip()

        stream = stream_or_dept if exam_type == "entrance" else ""
        dept = stream_or_dept if exam_type in ("exit","coc") else ""

        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("User not found. They must /start first.")
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
            label += "/" + stream
        if dept:
            label += "/" + dept
        await update.message.reply_text(
            "Subscription granted!\n\n"
            "User: " + str(row[0] or tid) + "\n"
            "Access: " + label + "\n"
            "Duration: " + str(days) + " days",
            reply_markup=admin_back_keyboard())
        try:
            await context.bot.send_message(
                chat_id=tid,
                text="Your subscription is activated!\n\n"
                     "Access: " + label + "\n"
                     "Duration: " + str(days) + " days\n\n"
                     "Start practicing now! Send /start")
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
            "Broadcast done. Sent: " + str(sent) + " Failed: " + str(failed),
            reply_markup=admin_back_keyboard())

    elif waiting == "new_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 4:
            await update.message.reply_text(
                "Wrong format.\n"
                "Use: exam_type|stream|key|name\n\n"
                "Example: entrance|natural|physics|Physics")
            return
        exam_type, stream, key, name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO subjects (exam_type,stream,subject_key,subject_name) VALUES (?,?,?,?)",
                    (exam_type, stream, key, name))
                await db.commit()
                await update.message.reply_text(
                    "Subject " + name + " added!", reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(
                    "Error: " + str(e) + "\nMaybe key already exists.",
                    reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("Format: old_key|new_name")
            return
        old_key, new_name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id FROM subjects WHERE subject_key=?", (old_key,))
            if not await cur.fetchone():
                await update.message.reply_text("Key not found: " + old_key)
                context.user_data.clear()
                return
            await db.execute("UPDATE subjects SET subject_name=? WHERE subject_key=?", (new_name, old_key))
            await db.commit()
        await update.message.reply_text("Subject updated to " + new_name, reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_subject_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT subject_name FROM subjects WHERE subject_key=?", (text,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("Key not found: " + text)
                context.user_data.clear()
                return
            await db.execute("DELETE FROM subjects WHERE subject_key=?", (text,))
            await db.commit()
        await update.message.reply_text("Subject " + row[0] + " deleted.", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "new_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Format: exam_type|key|name\nExample: coc|coc_welding|Welding")
            return
        exam_type, key, name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO departments (exam_type,dept_key,dept_name) VALUES (?,?,?)",
                    (exam_type, key, name))
                await db.commit()
                await update.message.reply_text("Department " + name + " added!", reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text("Error: " + str(e), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("Format: old_key|new_name")
            return
        old_key, new_name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id FROM departments WHERE dept_key=?", (old_key,))
            if not await cur.fetchone():
                await update.message.reply_text("Key not found: " + old_key)
                context.user_data.clear()
                return
            await db.execute("UPDATE departments SET dept_name=? WHERE dept_key=?", (new_name, old_key))
            await db.commit()
        await update.message.reply_text("Department updated to " + new_name, reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_dept_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT dept_name FROM departments WHERE dept_key=?", (text,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("Key not found: " + text)
                context.user_data.clear()
                return
            await db.execute("DELETE FROM departments WHERE dept_key=?", (text,))
            await db.commit()
        await update.message.reply_text("Department " + row[0] + " deleted.", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "add_subadmin":
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("User not found. They must /start first.")
                context.user_data.clear()
                return
            try:
                await db.execute(
                    "INSERT INTO admin_users (telegram_id,full_name,role,added_by) VALUES (?,?,\'sub\',?)",
                    (tid, row[0], uid))
                await db.commit()
                await update.message.reply_text(
                    "Sub admin added: " + str(row[0] or tid),
                    reply_markup=admin_back_keyboard())
                try:
                    await context.bot.send_message(
                        chat_id=tid,
                        text="You have been added as a Sub Admin.\n"
                             "Use /admin to access the admin panel.")
                except Exception:
                    pass
            except Exception as e:
                await update.message.reply_text("Error: " + str(e))
        context.user_data.clear()

    elif waiting == "remove_admin":
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM admin_users WHERE telegram_id=?", (tid,))
            await db.commit()
        await update.message.reply_text("Admin removed: " + str(tid), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_question_id":
        try:
            qid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM questions WHERE id=?", (qid,))
            row = await cur.fetchone()
        if not row:
            await update.message.reply_text("Question ID " + str(qid) + " not found.")
            context.user_data.clear()
            return
        q = dict(row)
        context.user_data["edit_question_id"] = qid
        context.user_data["waiting_for"] = None
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        preview = (
            "ID: " + str(q["id"]) + " Subject: " + str(q["subject"]) + " Year: " + str(q.get("year") or "N/A") + "\n\n"
            "Q: " + str(q["question_text"]) + "\n\n"
            "A) " + str(q["option_a"]) + "\n"
            "B) " + str(q["option_b"]) + "\n"
            "C) " + str(q["option_c"]) + "\n"
            "D) " + str(q["option_d"]) + "\n\n"
            "Answer: " + str(q["correct_answer"]) + "\n"
            "Explanation: " + str(q.get("explanation","")) + "\n"
            "Reference: " + str(q.get("reference",""))
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
            [InlineKeyboardButton("Back", callback_data="admin_back")],
        ])
        await update.message.reply_text(preview, reply_markup=edit_kb)

    elif waiting == "edit_q_value":
        qid = context.user_data.get("edit_question_id")
        field = context.user_data.get("edit_field")
        if not qid or not field:
            await update.message.reply_text("Session expired.")
            context.user_data.clear()
            return
        value = text
        if field == "correct_answer":
            value = text.upper()
            if value not in ["A","B","C","D"]:
                await update.message.reply_text("Must be A, B, C, or D.")
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
        await update.message.reply_text(
            "Question " + str(qid) + " updated!", reply_markup=admin_back_keyboard())

    elif waiting == "delete_question_id":
        try:
            qid = int(text)
        except ValueError:
            await update.message.reply_text("Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT subject FROM questions WHERE id=?", (qid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("Not found: " + str(qid))
                context.user_data.clear()
                return
            await db.execute("DELETE FROM questions WHERE id=?", (qid,))
            await db.commit()
        await update.message.reply_text("Question " + str(qid) + " deleted.", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "giveaway_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("Format: days|max_uses\nExample: 7|100")
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
                "INSERT INTO giveaway_codes (code,duration_days,max_uses,created_by) VALUES (?,?,?,?)",
                (code, days, max_uses, uid))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text(
            "Giveaway Code Created!\n\n"
            "Code: " + code + "\n"
            "Duration: " + str(days) + " days free access\n"
            "Max Uses: " + str(max_uses) + " students\n\n"
            "Students use: /redeem " + code,
            reply_markup=admin_back_keyboard())

    elif waiting == "edit_bank_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Format: bank_name|account_number|account_name")
            return
        bank_name, acc_num, acc_name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO bank_accounts (bank_name,account_number,account_name) VALUES (?,?,?) "
                "ON CONFLICT(bank_name) DO UPDATE SET account_number=?, account_name=?",
                (bank_name, acc_num, acc_name, acc_num, acc_name))
            await db.commit()
        await update.message.reply_text(
            "Bank account updated!\n" + bank_name + ": " + acc_num + " / " + acc_name,
            reply_markup=admin_back_keyboard())
        context.user_data.clear()


async def admin_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_any_admin(uid):
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
        await update.message.reply_text("No valid questions found. Check the format.")
        return
    context.user_data["parsed_questions"] = parsed
    context.user_data["waiting_for"] = "upload_exam_type"
    await update.message.reply_text(
        "Found " + str(len(parsed)) + " questions! Choose exam type:",
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
                    "option_a,option_b,option_c,option_d,correct_answer,explanation,reference) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (exam_type, stream, subject, q.get("year"),
                     q.get("question_text"), q.get("option_a"), q.get("option_b"),
                     q.get("option_c"), q.get("option_d"), q.get("correct_answer"),
                     q.get("explanation",""), q.get("reference","")))
                saved += 1
            except Exception:
                failed += 1
        await db.commit()
    context.user_data.clear()
    await query.edit_message_text(
        "Upload done! Saved: " + str(saved) + " Failed: " + str(failed),
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
                 d.get("aq_year"), d.get("aq_question_text"), d.get("aq_option_a"),
                 d.get("aq_option_b"), d.get("aq_option_c"), d.get("aq_option_d"),
                 d.get("aq_correct_answer"), d.get("aq_explanation",""), d.get("aq_reference","")))
            await db.commit()
        context.user_data.clear()
        await query.edit_message_text("Question saved!", reply_markup=admin_main_keyboard())
    except Exception as e:
        await query.edit_message_text("Error: " + str(e), reply_markup=admin_main_keyboard())


async def show_users(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        sub = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        today = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')")).fetchone())[0]
        cur = await db.execute(
            "SELECT telegram_id,full_name,is_subscribed,subscribed_exam_type "
            "FROM users ORDER BY created_at DESC LIMIT 15")
        recent = await cur.fetchall()
    lines = ""
    for r in recent:
        tag = "[SUB:" + str(r[3] or "") + "]" if r[2] else "[FREE]"
        lines += tag + " " + str(r[1] or "Unknown") + " (" + str(r[0]) + ")\n"
    await query.edit_message_text(
        "Users\n\nTotal: " + str(total) + " Sub: " + str(sub) + " Free: " + str(total-sub) + "\n"
        "Active today: " + str(today) + "\n\nRecent:\n" + lines,
        reply_markup=admin_back_keyboard())


async def show_stats(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        exams = (await (await db.execute("SELECT COUNT(*) FROM exam_sessions WHERE completed=1")).fetchone())[0]
        qcount = (await (await db.execute("SELECT COUNT(*) FROM questions")).fetchone())[0]
        row = await (await db.execute(
            "SELECT AVG(CAST(score AS FLOAT)/total*100) FROM exam_sessions WHERE completed=1 AND total>0")).fetchone()
        avg = row[0] if row[0] else 0
        pending = (await (await db.execute(
            "SELECT COUNT(*) FROM payments WHERE status='pending'")).fetchone())[0]
    await query.edit_message_text(
        "Statistics\n\nTotal Exams: " + str(exams) + "\nQuestions: " + str(qcount) +
        "\nAvg Score: " + str(round(avg,1)) + "%\nPending Receipts: " + str(pending),
        reply_markup=admin_back_keyboard())


async def show_questions(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id,exam_type,subject,year,question_text FROM questions "
            "ORDER BY exam_type,subject,year DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No questions yet.", reply_markup=admin_back_keyboard())
        return
    text = "Questions (up to 30)\n\n"
    for r in rows:
        yr = str(r[3]) if r[3] else "N/A"
        q_short = r[4][:35] + "..." if len(r[4]) > 35 else r[4]
        text += "ID:" + str(r[0]) + " [" + str(r[2]) + "] " + yr + "\n" + q_short + "\n\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_subjects(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT exam_type,stream,subject_key,subject_name FROM subjects ORDER BY exam_type,stream,subject_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No subjects.", reply_markup=admin_back_keyboard())
        return
    text = "All Subjects\n\n"
    for r in rows:
        text += r[3] + " (" + r[0] + "/" + str(r[1]) + ") key=" + r[2] + "\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_depts(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT exam_type,dept_key,dept_name FROM departments ORDER BY exam_type,dept_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No departments.", reply_markup=admin_back_keyboard())
        return
    text = "All Departments\n\n"
    for r in rows:
        text += r[2] + " (" + r[0] + ") key=" + r[1] + "\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_admins(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT telegram_id,full_name,role FROM admin_users ORDER BY role")
        rows = await cur.fetchall()
    text = "All Admins\n\n"
    text += "[SUPER] Main Admin (" + str(ADMIN_ID) + ")\n"
    for r in rows:
        text += "[" + str(r[2]).upper() + "] " + str(r[1] or "Unknown") + " (" + str(r[0]) + ")\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_giveaways(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT code,duration_days,max_uses,used_count,created_at "
            "FROM giveaway_codes ORDER BY created_at DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No giveaway codes.", reply_markup=admin_back_keyboard())
        return
    text = "Giveaway Codes\n\n"
    for r in rows:
        text += "Code: " + r[0] + "\n"
        text += str(r[3]) + "/" + str(r[1]) + " uses | " + str(r[1]) + " days\n\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def show_pending_receipts(query, context):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id,telegram_id,full_name,bank,exam_type,stream,dept,created_at,receipt_file_id "
            "FROM payments WHERE status=\'pending\' ORDER BY created_at ASC LIMIT 5")
        rows = [dict(r) for r in await cur.fetchall()]

    if not rows:
        await query.edit_message_text("No pending receipts.", reply_markup=admin_back_keyboard())
        return

    for p in rows:
        label = str(p["exam_type"] or "") + "/" + str(p["stream"] or p["dept"] or "")
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
            p["exam_type"] or "", p["stream"] or "", p["dept"] or "")
        try:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=p["receipt_file_id"],
                caption=caption,
                reply_markup=kb)
        except Exception:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=caption, reply_markup=kb)


async def approve_receipt(query, context, data):
    parts = data.replace("receipt_approve_", "").split("_")
    payment_id = int(parts[0])
    telegram_id = int(parts[1])
    exam_type = parts[2]
    stream = parts[3] if parts[3] != "None" else ""
    dept = parts[4] if parts[4] != "None" else ""

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=\'approved\', reviewed_by=? WHERE id=?",
            (query.from_user.id, payment_id))
        await db.execute(
            "UPDATE users SET is_subscribed=1, "
            "subscription_expiry=datetime('now','+30 days'), "
            "subscribed_exam_type=?, subscribed_stream=?, subscribed_dept=? "
            "WHERE telegram_id=?",
            (exam_type, stream, dept, telegram_id))
        await db.commit()

    await query.edit_message_caption("APPROVED - Subscription activated.")
    try:
        label = exam_type + ("/" + stream if stream else "") + ("/" + dept if dept else "")
        await context.bot.send_message(
            chat_id=telegram_id,
            text="Your payment is approved!\n\n"
                 "Access: " + label + "\n"
                 "Duration: 30 days\n\n"
                 "Start practicing now! Send /start")
    except Exception:
        pass


async def reject_receipt(query, context, data):
    parts = data.replace("receipt_reject_", "").split("_")
    payment_id = int(parts[0])
    telegram_id = int(parts[1])

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE payments SET status=\'rejected\', reviewed_by=? WHERE id=?",
            (query.from_user.id, payment_id))
        await db.commit()

    await query.edit_message_caption("REJECTED.")
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="Your payment receipt was not approved.\n\n"
                 "Please make sure you sent the correct amount to the correct account.\n"
                 "Contact admin: @John_3_13 for help.")
    except Exception:
        pass
''')


# ── app/handlers/exam.py ──────────────────────────────────
w("app/handlers/exam.py", '''from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.exams.engine import get_questions, save_session, finish_session
from app.keyboards.main_menu import back_to_main_keyboard
from app.utils.access import get_user, has_full_access, can_do_free_question, increment_free_questions
from app.utils.logger import logger
from config import PASS_MARK_PERCENT, FREE_QUESTIONS_LIMIT, DATABASE_PATH
import aiosqlite


async def get_subjects_db(exam_type, stream):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects WHERE exam_type=? AND (stream=? OR stream=\'general\') "
            "ORDER BY subject_name", (exam_type, stream))
        return [dict(r) for r in await cur.fetchall()]


async def get_years_db(exam_type, stream, subject):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT year FROM questions "
            "WHERE exam_type=? AND subject=? AND year IS NOT NULL ORDER BY year DESC",
            (exam_type, subject))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def get_depts_db(exam_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=? ORDER BY dept_name", (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


async def subject_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)

    if not user or not user.get("exam_type"):
        await query.edit_message_text(
            "Please choose your exam type first from the main menu.",
            reply_markup=back_to_main_keyboard())
        return

    exam_type = user.get("exam_type")
    stream = user.get("stream", "natural")

    if exam_type in ("exit", "coc"):
        depts = await get_depts_db(exam_type)
        keyboard = []
        for d in depts:
            keyboard.append([InlineKeyboardButton(d["dept_name"], callback_data="user_dept_" + d["dept_key"])])
        keyboard.append([InlineKeyboardButton("Back", callback_data="back_main")])
        await query.edit_message_text(
            "Choose your department:",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    subjects = await get_subjects_db(exam_type, stream)
    if not subjects:
        await query.edit_message_text("No subjects available yet.", reply_markup=back_to_main_keyboard())
        return

    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(s["subject_name"], callback_data="subject_" + s["subject_key"])])
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_main")])
    await query.edit_message_text(
        "Choose a subject:", reply_markup=InlineKeyboardMarkup(keyboard))


async def user_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dept = query.data.replace("user_dept_", "")
    user = await get_user(query.from_user.id)
    exam_type = user.get("exam_type", "exit")

    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET department=? WHERE telegram_id=?",
            (dept, query.from_user.id))
        await db.commit()

    subjects = await get_subjects_db(exam_type, dept)
    if not subjects:
        subjects = await get_subjects_db(exam_type, "general")

    if not subjects:
        await query.edit_message_text(
            "No subjects yet for this department. Admin is adding soon!",
            reply_markup=back_to_main_keyboard())
        return

    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(s["subject_name"], callback_data="subject_" + s["subject_key"])])
    keyboard.append([InlineKeyboardButton("Back", callback_data="back_main")])
    await query.edit_message_text(
        "Choose a subject:", reply_markup=InlineKeyboardMarkup(keyboard))


async def show_subject_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.replace("subject_", "")
    user_id = query.from_user.id
    user = await get_user(user_id)
    exam_type = user.get("exam_type", "entrance")
    stream = user.get("stream", "natural")
    dept = user.get("department", "")

    context.user_data["subject"] = subject
    context.user_data["exam_type"] = exam_type
    context.user_data["stream"] = stream
    context.user_data["dept"] = dept

    years = await get_years_db(exam_type, stream, subject)
    label = subject.replace("_", " ").title()

    has_access = await has_full_access(user, exam_type, stream, dept)

    if not has_access:
        can_free, used = await can_do_free_question(user_id)
        remaining = FREE_QUESTIONS_LIMIT - used
        access_note = (
            "\n\nFREE PREVIEW: " + str(remaining) + " questions remaining.\n"
            "Subscribe for full access - 50 ETB/month"
        )
    else:
        access_note = "\n\nFull access active."

    if years:
        keyboard = []
        row = []
        for y in sorted(years, reverse=True):
            row.append(InlineKeyboardButton(str(y), callback_data="examyear_" + subject + "_" + str(y)))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("All Years", callback_data="examyear_" + subject + "_all")])
        keyboard.append([InlineKeyboardButton("Back", callback_data="choose_subject")])
        await query.edit_message_text(
            label + "\n\nAvailable years: " + str(len(years)) + "\nChoose a year:" + access_note,
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(
            label + "\n\n10 questions per exam.\nInstant feedback and explanations." + access_note,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Start Exam!", callback_data="start_exam_" + subject + "__yall")],
                [InlineKeyboardButton("Back", callback_data="back_main")],
            ]))


async def year_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    raw = query.data.replace("examyear_", "")
    parts = raw.rsplit("_", 1)
    subject = parts[0]
    year_str = parts[1]
    year = None if year_str == "all" else int(year_str)
    context.user_data["selected_year"] = year
    context.user_data["subject"] = subject
    label = subject.replace("_", " ").title()
    yr_label = str(year) if year else "All Years"
    await query.edit_message_text(
        label + " - " + yr_label + "\n\nReady to start?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Start Exam!", callback_data="start_exam_" + subject + "__y" + str(year or "all"))],
            [InlineKeyboardButton("Back", callback_data="back_main")],
        ]))


async def start_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    raw = query.data.replace("start_exam_", "")
    if "__y" in raw:
        parts = raw.split("__y")
        subject = parts[0]
        year_str = parts[1]
        year = None if year_str == "all" else int(year_str)
    else:
        subject = raw
        year = context.user_data.get("selected_year")

    user_id = query.from_user.id
    user = await get_user(user_id)
    exam_type = user.get("exam_type", "entrance")
    stream = user.get("stream", "natural")
    dept = user.get("department", "")

    has_access = await has_full_access(user, exam_type, stream, dept)
    can_free, used = await can_do_free_question(user_id)

    if not has_access and not can_free:
        await query.edit_message_text(
            "Free preview limit reached!\n\n"
            "You have used all " + str(FREE_QUESTIONS_LIMIT) + " free questions.\n\n"
            "Subscribe for 50 ETB/month for full unlimited access.\n\n"
            "Use /start and tap Subscribe to pay.",
            reply_markup=back_to_main_keyboard())
        return

    questions = await get_questions(exam_type, stream, subject, year)
    if not questions:
        await query.edit_message_text(
            "No questions found for this selection. Admin is adding soon!",
            reply_markup=back_to_main_keyboard())
        return

    if not has_access:
        questions = questions[:FREE_QUESTIONS_LIMIT]

    session_id = await save_session(user_id, exam_type, stream, subject)
    context.user_data["questions"] = questions
    context.user_data["current_q"] = 0
    context.user_data["score"] = 0
    context.user_data["session_id"] = session_id
    context.user_data["subject"] = subject
    context.user_data["is_free_session"] = not has_access
    context.user_data["free_limit"] = FREE_QUESTIONS_LIMIT
    logger.info("User " + str(user_id) + " started exam: " + subject)
    await ask_question(query, context)


async def ask_question(query, context):
    questions = context.user_data["questions"]
    current = context.user_data["current_q"]
    session_id = context.user_data["session_id"]
    total = len(questions)
    q = questions[current]
    is_free = context.user_data.get("is_free_session", False)
    free_note = ""
    if is_free:
        remaining = total - current
        free_note = "\n[FREE PREVIEW - Question " + str(current+1) + " of " + str(total) + "]"

    await query.edit_message_text(
        "Question " + str(current+1) + " of " + str(total) + free_note + "\n"
        + "-"*28 + "\n\n"
        + q["question_text"] + "\n\n"
        "A) " + q["option_a"] + "\n"
        "B) " + q["option_b"] + "\n"
        "C) " + q["option_c"] + "\n"
        "D) " + q["option_d"],
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("A", callback_data="answer_" + str(session_id) + "_A"),
            InlineKeyboardButton("B", callback_data="answer_" + str(session_id) + "_B"),
            InlineKeyboardButton("C", callback_data="answer_" + str(session_id) + "_C"),
            InlineKeyboardButton("D", callback_data="answer_" + str(session_id) + "_D"),
        ]]))


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chosen = query.data.split("_")[-1]
    questions = context.user_data.get("questions")
    current = context.user_data.get("current_q", 0)
    is_free = context.user_data.get("is_free_session", False)

    if not questions:
        await query.edit_message_text("Session expired.", reply_markup=back_to_main_keyboard())
        return

    q = questions[current]
    correct = q["correct_answer"]
    is_correct = chosen == correct
    if is_correct:
        context.user_data["score"] += 1

    opts = {"A": q["option_a"], "B": q["option_b"], "C": q["option_c"], "D": q["option_d"]}
    icon = "CORRECT" if is_correct else "WRONG"
    result_text = "Correct!" if is_correct else "Wrong! Answer: " + correct + ") " + opts[correct]
    yr = " | Year: " + str(q["year"]) if q.get("year") else ""
    feedback = (
        icon + " - " + result_text + "\n\n"
        "Explanation:\n" + str(q.get("explanation", "No explanation.")) + "\n\n"
        "Reference: " + str(q.get("reference", "N/A")) + yr
    )

    if is_free:
        await increment_free_questions(query.from_user.id)

    context.user_data["current_q"] += 1
    next_q = context.user_data["current_q"]
    total = len(questions)

    if next_q >= total:
        score = context.user_data["score"]
        session_id = context.user_data["session_id"]
        await finish_session(session_id, score, total)
        pct = (score/total)*100
        passed = pct >= PASS_MARK_PERCENT

        final_text = (
            feedback + "\n\n"
            + "="*28 + "\n"
            "EXAM COMPLETE!\n\n"
            "Score: " + str(score) + "/" + str(total) + " (" + str(round(pct)) + "%)\n"
            "Result: " + ("PASSED!" if passed else "Keep practicing!") + "\n\n"
        )

        if is_free:
            final_text += (
                "-"*28 + "\n"
                "You have used all " + str(FREE_QUESTIONS_LIMIT) + " free questions.\n\n"
                "Subscribe for 50 ETB/month for unlimited access!\n"
                "Use /start and tap Subscribe.\n"
                "Contact admin: @John_3_13"
            )
            await query.edit_message_text(
                final_text,
                reply_markup=back_to_main_keyboard())
        else:
            await query.edit_message_text(
                final_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Try Again", callback_data="retry_exam")],
                    [InlineKeyboardButton("Main Menu", callback_data="back_main")],
                ]))
        logger.info("User " + str(query.from_user.id) + " finished: " + str(score) + "/" + str(total))
    else:
        await query.edit_message_text(
            feedback,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Next (" + str(next_q+1) + "/" + str(total) + ")",
                                     callback_data="next_question")
            ]]))


async def next_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await ask_question(query, context)


async def retry_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = context.user_data.get("subject", "")
    if subject:
        query.data = "start_exam_" + subject + "__yall"
        await start_exam_handler(update, context)
    else:
        await query.edit_message_text("Choose a subject.", reply_markup=back_to_main_keyboard())
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
    start_exam_handler, answer_handler, next_question_handler,
    retry_exam_handler, user_dept_select,
)
from app.handlers.admin import (
    admin_command, admin_button_handler, admin_text_handler,
    admin_file_handler, admin_upload_handler,
)
from app.handlers.subscription import (
    subscribe_handler, sub_exam_select_handler, sub_stream_select,
    sub_dept_select, pay_bank_handler, send_receipt_handler,
    receipt_photo_handler,
)
from app.handlers.user_features import redeem_command, referral_command
from app.utils.logger import logger


def main():
    logger.info("Starting EthiopianExamBot...")

    async def post_init(application):
        await init_db()
        await seed_sample_questions()
        logger.info("Bot started!")

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
        pattern="^(admin_|aq_subject_|aq_dept_|edit_q_field_|receipt_approve_|receipt_reject_)"))

    app.add_handler(CallbackQueryHandler(subscribe_handler, pattern="^subscribe$"))
    app.add_handler(CallbackQueryHandler(sub_exam_select_handler, pattern="^sub_exam_"))
    app.add_handler(CallbackQueryHandler(sub_stream_select, pattern="^stream_"))
    app.add_handler(CallbackQueryHandler(sub_dept_select, pattern="^dept_"))
    app.add_handler(CallbackQueryHandler(pay_bank_handler, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(send_receipt_handler, pattern="^send_receipt$"))

    app.add_handler(CallbackQueryHandler(subject_selection_handler, pattern="^choose_subject$"))
    app.add_handler(CallbackQueryHandler(user_dept_select, pattern="^user_dept_"))
    app.add_handler(CallbackQueryHandler(show_subject_intro, pattern="^subject_"))
    app.add_handler(CallbackQueryHandler(year_select_handler, pattern="^examyear_"))
    app.add_handler(CallbackQueryHandler(start_exam_handler, pattern="^start_exam_"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(next_question_handler, pattern="^next_question$"))
    app.add_handler(CallbackQueryHandler(retry_exam_handler, pattern="^retry_exam$"))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.PHOTO, receipt_photo_handler))
    app.add_handler(MessageHandler(filters.Document.TXT, admin_file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))

    logger.info("Handlers registered. Bot is polling...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
''')

print("\nAll files written successfully!")
print("Now run:")
print("  Remove-Item -Force data\\exam_bot.db")
print("  python main.py")