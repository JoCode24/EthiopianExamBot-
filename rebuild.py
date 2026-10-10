import os

def w(path, content):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ " + path)

# ─────────────────────────────────────────────────────────
w("config.py", '''import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
DATABASE_PATH = "data/exam_bot.db"

SUBSCRIPTION_PRICE_ETB = 50
SUBSCRIPTION_DAYS = 30
FREE_QUESTIONS_LIMIT = 5
QUESTIONS_PER_EXAM = 10
PASS_MARK_PERCENT = 50
ADMIN_USERNAME = "@John_3_13"
''')

# ─────────────────────────────────────────────────────────
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
                emoji TEXT DEFAULT '📘'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL DEFAULT 'exit',
                dept_key TEXT NOT NULL UNIQUE,
                dept_name TEXT NOT NULL,
                emoji TEXT DEFAULT '🏛️'
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
        logger.info("✅ Database initialized.")


async def seed_defaults(db):
    cur = await db.execute("SELECT COUNT(*) FROM subjects")
    if (await cur.fetchone())[0] == 0:
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
                ("remedial","natural","rem_math","Mathematics","🧮"),
                ("remedial","natural","rem_english","English","🌍"),
                ("remedial","natural","rem_physics","Physics","⚡"),
                ("remedial","social","rem_soc_english","English","🌍"),
                ("remedial","social","rem_history","History","📜"),
                ("remedial","social","rem_civics","Civics","⚖️"),
                ("driving","general","traffic_law","Traffic Law","🚦"),
                ("driving","general","road_signs","Road Signs","🛑"),
                ("driving","general","first_aid","First Aid","🏥"),
                ("driving","general","vehicle_mechanics","Vehicle Mechanics","🔧"),
                ("coc","coc_electrical","coc_elec_l1","Electrical Level 1","⚡"),
                ("coc","coc_electrical","coc_elec_l2","Electrical Level 2","⚡"),
                ("coc","coc_construction","coc_constr","Construction & Civil","🏗️"),
                ("coc","coc_it","coc_it_l1","IT & Computer Level 1","💻"),
                ("coc","coc_it","coc_it_l2","IT & Computer Level 2","💻"),
                ("coc","coc_automotive","coc_auto","Automotive","🚗"),
                ("coc","coc_accounting","coc_acc","Accounting","📊"),
                ("coc","coc_management","coc_mgmt","Management","💼"),
                ("coc","coc_hotel","coc_hotel","Hotel Management","🏨"),
                ("coc","coc_marketing","coc_mkt","Marketing","📣"),
                ("coc","coc_mechanical","coc_mech","Mechanical","⚙️"),
            ]
        )

    cur2 = await db.execute("SELECT COUNT(*) FROM departments")
    if (await cur2.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO departments (exam_type,dept_key,dept_name,emoji) VALUES (?,?,?,?)",
            [
                ("exit","computer_science","Computer Science","💻"),
                ("exit","accounting","Accounting & Finance","📊"),
                ("exit","law","Law","⚖️"),
                ("exit","medicine","Medicine","🏥"),
                ("exit","engineering","Engineering","⚙️"),
                ("exit","business","Business Management","💼"),
                ("exit","agriculture","Agriculture","🌾"),
                ("exit","education","Education","📖"),
                ("exit","nursing","Nursing","🩺"),
                ("coc","coc_electrical","Electrical","⚡"),
                ("coc","coc_construction","Construction & Civil","🏗️"),
                ("coc","coc_mechanical","Mechanical","⚙️"),
                ("coc","coc_it","IT & Computer","💻"),
                ("coc","coc_automotive","Automotive","🚗"),
                ("coc","coc_accounting","Accounting","📊"),
                ("coc","coc_management","Management","💼"),
                ("coc","coc_hotel","Hotel Management","🏨"),
                ("coc","coc_marketing","Marketing","📣"),
                ("remedial","remedial_natural","Natural Science","🔬"),
                ("remedial","remedial_social","Social Science","📚"),
                ("driving","driving_general","Driving General","🚗"),
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

# ─────────────────────────────────────────────────────────
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
        sub_dept = user.get("subscribed_dept", "")
        if not dept:
            return True
        return sub_dept == dept or sub_dept == ""
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
            "UPDATE users SET free_questions_used=free_questions_used+1 WHERE telegram_id=?",
            (telegram_id,))
        await db.commit()
''')

# ─────────────────────────────────────────────────────────
w("app/exams/engine.py", '''import aiosqlite
import os
from config import DATABASE_PATH, QUESTIONS_PER_EXAM


async def get_questions(exam_type, stream, subject, year=None):
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if year:
            cur = await db.execute(
                "SELECT * FROM questions WHERE exam_type=? AND subject=? AND year=? "
                "ORDER BY RANDOM() LIMIT ?",
                (exam_type, subject, year, QUESTIONS_PER_EXAM))
        else:
            cur = await db.execute(
                "SELECT * FROM questions WHERE exam_type=? AND subject=? "
                "ORDER BY RANDOM() LIMIT ?",
                (exam_type, subject, QUESTIONS_PER_EXAM))
        return [dict(r) for r in await cur.fetchall()]


async def save_session(telegram_id, exam_type, stream, subject):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO exam_sessions (telegram_id,exam_type,stream,subject) VALUES (?,?,?,?)",
            (telegram_id, exam_type, stream, subject))
        await db.commit()
        return cur.lastrowid


async def finish_session(session_id, score, total):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE exam_sessions SET score=?,total=?,completed=1,finished_at=datetime('now') WHERE id=?",
            (score, total, session_id))
        await db.commit()


async def seed_sample_questions():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM questions")
        if (await cur.fetchone())[0] > 0:
            return
        samples = [
            ("entrance","natural","math",2023,"What is the value of x if 2x + 6 = 14?","2","3","4","5","C","2x=8 so x=4","Grade 12 Math Ch.2"),
            ("entrance","natural","math",2022,"What is the derivative of x squared?","x","2x","2","x+2","B","Power rule: d/dx(x^2)=2x","Grade 12 Math Calculus"),
            ("entrance","natural","math",2021,"What is log base 2 of 8?","2","4","3","6","C","2^3=8 so log2(8)=3","Grade 12 Math Logarithms"),
            ("entrance","natural","math",2020,"What is the area of a circle with radius 7? Use pi=3.14","43.96","153.86","21.98","87.92","B","Area=pi*r^2=3.14*49=153.86","Grade 12 Math Geometry"),
            ("entrance","natural","math",2019,"What is 3 squared plus 4 squared?","14","25","49","12","B","9+16=25 Pythagorean triple","Grade 12 Math Algebra"),
            ("entrance","natural","physics",2023,"What is the SI unit of force?","Watt","Joule","Newton","Pascal","C","Force is measured in Newtons F=ma","Grade 12 Physics Ch.1"),
            ("entrance","natural","physics",2022,"What is the speed of light in vacuum?","3x10^6 m/s","3x10^8 m/s","3x10^10 m/s","3x10^4 m/s","B","Speed of light c=3x10^8 m/s","Grade 12 Physics Optics"),
            ("entrance","natural","physics",2021,"Newton third law states what?","Objects at rest stay at rest","F=ma","Every action has equal opposite reaction","Gravity law","C","Action-reaction pairs","Grade 12 Physics Mechanics"),
            ("entrance","natural","physics",2020,"What is the formula for kinetic energy?","mgh","half mv squared","mv","Fd","B","KE=0.5mv^2","Grade 12 Physics Energy"),
            ("entrance","natural","physics",2019,"What happens to resistance when temperature increases in conductor?","Decreases","Stays same","Increases","Becomes zero","C","Resistance increases with temperature in conductors","Grade 12 Physics Electricity"),
            ("entrance","natural","chemistry",2023,"What is the atomic number of Carbon?","6","12","8","14","A","Carbon has 6 protons","Grade 12 Chemistry Periodic Table"),
            ("entrance","natural","chemistry",2022,"What is the chemical formula for water?","HO","H2O","H3O","OH","B","Water is H2O two hydrogen one oxygen","Grade 12 Chemistry"),
            ("entrance","natural","chemistry",2021,"What gas is produced when acid reacts with metal?","Oxygen","Carbon dioxide","Hydrogen","Nitrogen","C","Acid plus Metal gives Salt plus Hydrogen gas","Grade 12 Chemistry Reactions"),
            ("entrance","natural","chemistry",2020,"What is the pH of neutral solution?","0","7","14","1","B","pH 7 is neutral below is acidic above is basic","Grade 12 Chemistry"),
            ("entrance","natural","chemistry",2019,"What is Avogadro number?","6.02x10^21","6.02x10^23","6.02x10^25","6.02x10^22","B","Avogadro number is 6.02x10^23 per mole","Grade 12 Chemistry Mole"),
            ("entrance","natural","biology",2023,"What is the powerhouse of the cell?","Nucleus","Ribosome","Mitochondria","Chloroplast","C","Mitochondria produce ATP through cellular respiration","Grade 12 Biology"),
            ("entrance","natural","biology",2022,"What molecule carries genetic information?","RNA","ATP","DNA","Protein","C","DNA carries genetic information","Grade 12 Biology Genetics"),
            ("entrance","natural","biology",2021,"How many chromosomes do normal human cells have?","23","44","46","48","C","Human cells have 46 chromosomes 23 pairs","Grade 12 Biology"),
            ("entrance","natural","biology",2020,"What is the process by which plants make food?","Respiration","Photosynthesis","Digestion","Transpiration","B","Photosynthesis CO2 plus H2O plus light gives glucose plus O2","Grade 12 Biology"),
            ("entrance","natural","biology",2019,"Which blood type is the universal donor?","A","B","AB","O","D","Blood type O negative is the universal donor","Grade 12 Biology Blood"),
            ("entrance","natural","english",2023,"She ___ to school every day.","go","goes","going","gone","B","Third person singular uses goes in present simple","Grade 12 English Grammar"),
            ("entrance","natural","english",2022,"What is the synonym of enormous?","Tiny","Huge","Fast","Slow","B","Enormous means very large Huge is its synonym","Grade 12 English Vocabulary"),
            ("entrance","natural","english",2021,"Which sentence is passive voice?","The dog bit the man","The man was bitten by the dog","The man bit the dog","The dog bites","B","Passive voice subject receives the action","Grade 12 English"),
            ("entrance","natural","english",2020,"What does break a leg mean?","Get injured","Good luck","Run fast","Work hard","B","Break a leg is an idiom meaning good luck","Grade 12 English Idioms"),
            ("entrance","natural","english",2019,"Which is the correct spelling?","Recieve","Receive","Receve","Receeve","B","Correct spelling is receive i before e except after c","Grade 12 English Spelling"),
            ("entrance","social","history",2023,"When did Ethiopia defeat Italy at Adwa?","1885","1896","1906","1916","B","Battle of Adwa March 1 1896","Grade 12 History"),
            ("entrance","social","history",2022,"Who was the emperor at Battle of Adwa?","Haile Selassie","Menelik II","Tewodros","Yohannes IV","B","Emperor Menelik II led Ethiopia at Adwa","Grade 12 History"),
            ("entrance","social","history",2021,"When did Ethiopia join the United Nations?","1945","1950","1955","1960","A","Ethiopia was a founding member of UN in 1945","Grade 12 History"),
            ("entrance","social","history",2020,"What year did the EPRDF come to power?","1987","1989","1991","1993","C","EPRDF came to power in 1991","Grade 12 History"),
            ("entrance","social","history",2019,"Which country colonized Eritrea before independence?","Ethiopia","Italy","Britain","France","B","Italy colonized Eritrea","Grade 12 History"),
            ("entrance","social","geography",2023,"What is the capital city of Ethiopia?","Dire Dawa","Hawassa","Addis Ababa","Bahir Dar","C","Addis Ababa is the capital of Ethiopia","Grade 12 Geography"),
            ("entrance","social","geography",2022,"What is the longest river in Africa?","Congo","Niger","Nile","Zambezi","C","The Nile is the longest river in Africa","Grade 12 Geography"),
            ("entrance","social","geography",2021,"What is the largest lake in Ethiopia?","Tana","Ziway","Turkana","Abijata","A","Lake Tana is the largest lake in Ethiopia","Grade 12 Geography"),
            ("entrance","social","geography",2020,"Which ocean borders East Africa?","Atlantic","Pacific","Indian","Arctic","C","Indian Ocean borders East Africa","Grade 12 Geography"),
            ("entrance","social","geography",2019,"What is the Great Rift Valley?","A mountain range","A tectonic crack","A river","A plateau","B","The Great Rift Valley is a tectonic crack in Earth","Grade 12 Geography"),
            ("entrance","social","economics",2023,"What does GDP stand for?","Gross Domestic Product","General Development Plan","Gross Development Process","General Domestic Progress","A","GDP is the total value of goods and services","Grade 12 Economics"),
            ("entrance","social","economics",2022,"What is inflation?","Decrease in prices","Increase in money supply","General increase in price levels","Low unemployment","C","Inflation is a general increase in price levels","Grade 12 Economics"),
            ("entrance","social","economics",2021,"What is a budget deficit?","When revenue exceeds spending","When spending exceeds revenue","When exports exceed imports","When imports exceed exports","B","Budget deficit is when government spending exceeds revenue","Grade 12 Economics"),
            ("entrance","social","economics",2020,"What is the function of a central bank?","Sell goods","Control money supply","Build roads","Collect taxes","B","Central bank controls money supply and interest rates","Grade 12 Economics"),
            ("entrance","social","economics",2019,"What is comparative advantage?","Producing at lowest opportunity cost","Producing the most","Having best technology","Lowest wages","A","Comparative advantage means producing at lowest opportunity cost","Grade 12 Economics"),
            ("entrance","social","civics",2023,"What is the supreme law of Ethiopia?","Criminal Code","Civil Code","The Constitution","Parliament Act","C","1995 Constitution is the supreme law","Grade 12 Civics"),
            ("entrance","social","civics",2022,"How many regions does Ethiopia have?","9","10","11","12","C","Ethiopia has 11 regional states","Grade 12 Civics"),
            ("entrance","social","civics",2021,"What type of government does Ethiopia have?","Monarchy","Federal Democratic Republic","Military","Theocracy","B","Ethiopia is a Federal Democratic Republic","Grade 12 Civics"),
            ("entrance","social","civics",2020,"Who elects the Prime Minister of Ethiopia?","The people directly","The House of Peoples Representatives","The Senate","The military","B","House of Peoples Representatives elects PM","Grade 12 Civics"),
            ("entrance","social","civics",2019,"What does human rights mean?","Rights given by government","Rights earned through work","Rights belonging to all humans","Rights for citizens only","C","Human rights belong to all people regardless of origin","Grade 12 Civics"),
            ("driving","general","traffic_law",2023,"What does a red traffic light mean?","Go","Slow down","Stop","Caution","C","Red light means stop completely","Traffic Law Ch.1"),
            ("driving","general","traffic_law",2023,"What is the speed limit in Ethiopian cities?","40 km/h","50 km/h","60 km/h","80 km/h","B","City speed limit in Ethiopia is 50 km/h","Traffic Law"),
            ("driving","general","road_signs",2023,"A triangular sign with red border means?","Stop","Warning","Information","Direction","B","Triangular red border signs are warning signs","Road Signs Ch.1"),
            ("driving","general","first_aid",2023,"First step in accident scene is?","Move victim","Call for help","Check for danger","Give water","C","First check for danger before approaching","First Aid"),
            ("driving","general","vehicle_mechanics",2023,"What fluid is in the radiator?","Oil","Coolant","Brake fluid","Transmission fluid","B","Radiator contains coolant to prevent overheating","Vehicle Mechanics"),
            ("coc","coc_electrical","coc_elec_l1",2023,"What is Ohm law formula?","V=IR","P=IV","I=PV","R=PI","A","Ohm law V=IR Voltage equals Current times Resistance","Electrical Engineering"),
            ("coc","coc_electrical","coc_elec_l1",2023,"What unit measures electrical resistance?","Volt","Ampere","Ohm","Watt","C","Resistance is measured in Ohms","Electrical Engineering"),
            ("coc","coc_it","coc_it_l1",2023,"What does CPU stand for?","Central Processing Unit","Computer Power Unit","Central Power Unit","Computer Processing Unit","A","CPU is the Central Processing Unit","IT Fundamentals"),
            ("coc","coc_it","coc_it_l1",2023,"What is RAM?","Read Access Memory","Random Access Memory","Rapid Access Module","Read Actual Memory","B","RAM is Random Access Memory temporary storage","IT Fundamentals"),
            ("coc","coc_accounting","coc_acc",2023,"What is a balance sheet?","Income statement","Statement of financial position","Cash flow statement","Budget plan","B","Balance sheet shows assets liabilities and equity","Accounting"),
            ("remedial","natural","rem_math",2023,"What is 15 percent of 200?","25","30","35","40","B","15 percent of 200 is 30","Remedial Math"),
            ("remedial","natural","rem_english",2023,"Choose the correct sentence.","He go to school","He goes to school","He going to school","He gone to school","B","Third person singular present tense uses goes","Remedial English"),
            ("remedial","social","rem_soc_english",2023,"What is a noun?","Action word","Describing word","Person place or thing","Connecting word","C","A noun is a person place thing or idea","Remedial English"),
            ("remedial","social","rem_history",2023,"What continent is Ethiopia in?","Asia","Europe","Africa","America","C","Ethiopia is located in the continent of Africa","Remedial Geography"),
        ]
        await db.executemany(
            "INSERT INTO questions (exam_type,stream,subject,year,question_text,"
            "option_a,option_b,option_c,option_d,correct_answer,explanation,reference) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", samples)
        await db.commit()
        logger.info("✅ Sample questions seeded.")


from app.utils.logger import logger
''')

# ─────────────────────────────────────────────────────────
w("app/utils/question_parser.py", '''import re


def parse_questions_from_text(text: str) -> list:
    questions = []
    blocks = re.split(r"\\n\\s*\\n+", text.strip())
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        try:
            q = parse_single_block(block)
            if q:
                questions.append(q)
        except Exception:
            continue
    return questions


def parse_single_block(block: str) -> dict:
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if len(lines) < 6:
        return None
    result = {
        "question_text": "", "option_a": "", "option_b": "",
        "option_c": "", "option_d": "", "correct_answer": "",
        "explanation": "", "reference": "", "year": None,
    }
    for line in lines:
        low = line.lower()
        if low.startswith("q:") or low.startswith("question:"):
            result["question_text"] = re.sub(r"^(question:|q:)\\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^a[\\)\\.]\\s*", line, re.IGNORECASE):
            result["option_a"] = re.sub(r"^a[\\)\\.]\\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^b[\\)\\.]\\s*", line, re.IGNORECASE):
            result["option_b"] = re.sub(r"^b[\\)\\.]\\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^c[\\)\\.]\\s*", line, re.IGNORECASE):
            result["option_c"] = re.sub(r"^c[\\)\\.]\\s*", "", line, flags=re.IGNORECASE).strip()
        elif re.match(r"^d[\\)\\.]\\s*", line, re.IGNORECASE):
            result["option_d"] = re.sub(r"^d[\\)\\.]\\s*", "", line, flags=re.IGNORECASE).strip()
        elif low.startswith("answer:") or low.startswith("ans:") or low.startswith("correct:"):
            ans = re.sub(r"^(answer:|ans:|correct:)\\s*", "", line, flags=re.IGNORECASE).strip().upper()
            if ans in ["A", "B", "C", "D"]:
                result["correct_answer"] = ans
        elif low.startswith("explanation:") or low.startswith("exp:"):
            result["explanation"] = re.sub(r"^(explanation:|exp:)\\s*", "", line, flags=re.IGNORECASE).strip()
        elif low.startswith("reference:") or low.startswith("ref:"):
            result["reference"] = re.sub(r"^(reference:|ref:)\\s*", "", line, flags=re.IGNORECASE).strip()
        elif low.startswith("year:"):
            try:
                result["year"] = int(re.sub(r"^year:\\s*", "", line, flags=re.IGNORECASE).strip())
            except Exception:
                pass
    if not all([result["question_text"], result["option_a"], result["option_b"],
                result["option_c"], result["option_d"], result["correct_answer"]]):
        return None
    return result
''')

# ─────────────────────────────────────────────────────────
w("app/keyboards/main_menu.py", '''from telegram import InlineKeyboardButton, InlineKeyboardMarkup


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
''')

# ─────────────────────────────────────────────────────────
w("app/keyboards/admin_menu.py", '''from telegram import InlineKeyboardButton, InlineKeyboardMarkup


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
    approve_data = "rcpt_ok_" + "_".join([
        str(payment_id), str(telegram_id),
        str(exam_type), str(stream), str(dept)
    ])
    reject_data = "rcpt_no_" + str(payment_id) + "_" + str(telegram_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve - Grant Access", callback_data=approve_data)],
        [InlineKeyboardButton("❌ Reject", callback_data=reject_data)],
    ])
''')

# ─────────────────────────────────────────────────────────
w("app/handlers/start.py", '''from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.main_menu import (
    main_menu_keyboard, stream_keyboard,
    back_to_main_keyboard, build_dept_select_keyboard,
)
from app.utils.logger import logger
from app.handlers.user_features import handle_referral_start, ensure_referral_code
from config import ADMIN_ID, DATABASE_PATH
import aiosqlite


async def get_depts_for_exam(exam_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=? ORDER BY dept_name",
            (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


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
            logger.info("🆕 New user: " + str(user.full_name) + " (" + str(user.id) + ")")
            await handle_referral_start(update, context)
        else:
            await db.execute(
                "UPDATE users SET last_active=datetime('now') WHERE telegram_id=?",
                (user.id,))
            await db.commit()
    await ensure_referral_code(user.id)
    name = user.first_name or "Student"
    await update.message.reply_text(
        "👋 Welcome, " + name + "!\n\n"
        "🇪🇹 Ethiopian Exam Preparation Bot\n\n"
        "📚 Prepare for:\n"
        "🎓 Entrance Exam (Grade 12)\n"
        "🏛️ University Exit Exam\n"
        "📋 CoC Exam (TVET)\n"
        "🚗 Driving Licence Exam\n"
        "📝 Remedial Exam\n\n"
        "✅ Get 5 free practice questions (one time).\n"
        "💳 Subscribe for 50 ETB/month for full access.\n\n"
        "👇 Choose an option:",
        reply_markup=main_menu_keyboard())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    if data == "back_main":
        await query.edit_message_text(
            "👇 Main Menu:", reply_markup=main_menu_keyboard())

    elif data == "exam_type_entrance":
        await query.edit_message_text(
            "🎓 Entrance Exam\n\nChoose your stream:",
            reply_markup=stream_keyboard())

    elif data == "exam_type_exit":
        depts = await get_depts_for_exam("exit")
        await query.edit_message_text(
            "🏛️ University Exit Exam\n\nChoose your department:",
            reply_markup=build_dept_select_keyboard(depts))

    elif data == "exam_type_coc":
        depts = await get_depts_for_exam("coc")
        await query.edit_message_text(
            "📋 CoC Exam (TVET)\n\nChoose your department:",
            reply_markup=build_dept_select_keyboard(depts))

    elif data == "exam_type_driving":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET exam_type='driving', stream='general' WHERE telegram_id=?",
                (user.id,))
            await db.commit()
        await query.edit_message_text(
            "🚗 Driving Licence Exam selected!\n\n"
            "Tap ▶️ Start Practice Exam from the main menu.",
            reply_markup=back_to_main_keyboard())

    elif data == "exam_type_remedial":
        await query.edit_message_text(
            "📝 Remedial Exam\n\nChoose your stream:",
            reply_markup=stream_keyboard(prefix="rem_stream_"))

    elif data.startswith("stream_"):
        stream = data.replace("stream_", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT exam_type FROM users WHERE telegram_id=?", (user.id,))
            row = await cur.fetchone()
            exam_type = row[0] if (row and row[0] and row[0] != "driving") else "entrance"
            await db.execute(
                "UPDATE users SET exam_type=?, stream=? WHERE telegram_id=?",
                (exam_type, stream, user.id))
            await db.commit()
        names = {"natural": "🔬 Natural Science", "social": "📚 Social Science"}
        await query.edit_message_text(
            "✅ Stream: " + names.get(stream, stream) + "\n\n"
            "Profile saved! Tap ▶️ Start Practice Exam from the main menu.",
            reply_markup=back_to_main_keyboard())

    elif data.startswith("rem_stream_"):
        stream = data.replace("rem_stream_", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE users SET exam_type='remedial', stream=? WHERE telegram_id=?",
                (stream, user.id))
            await db.commit()
        names = {"natural": "🔬 Natural Science", "social": "📚 Social Science"}
        await query.edit_message_text(
            "✅ Remedial - " + names.get(stream, stream) + "\n\n"
            "Profile saved! Tap ▶️ Start Practice Exam.",
            reply_markup=back_to_main_keyboard())

    elif data.startswith("dept_select_"):
        dept = data.replace("dept_select_", "")
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT exam_type FROM users WHERE telegram_id=?", (user.id,))
            row = await cur.fetchone()
            exam_type = row[0] if row and row[0] else "exit"
            await db.execute(
                "UPDATE users SET exam_type=?, department=?, stream=? WHERE telegram_id=?",
                (exam_type, dept, dept, user.id))
            await db.commit()
        await query.edit_message_text(
            "✅ Department selected!\n\n"
            "Profile saved. Tap ▶️ Start Practice Exam.",
            reply_markup=back_to_main_keyboard())

    elif data == "my_progress":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT score,total FROM exam_sessions WHERE telegram_id=? AND completed=1",
                (user.id,))
            sessions = await cur.fetchall()
            cur2 = await db.execute(
                "SELECT referral_count,free_questions_used,is_subscribed,subscribed_exam_type "
                "FROM users WHERE telegram_id=?", (user.id,))
            urow = await cur2.fetchone()
        ref_count = urow[0] if urow else 0
        free_used = urow[1] if urow else 0
        is_sub = urow[2] if urow else 0
        sub_type = urow[3] if urow else ""
        if not sessions:
            text = (
                "📊 Your Progress\n\n"
                "No exams completed yet. Start practicing!\n\n"
                "🆓 Free questions used: " + str(free_used) + "/5\n"
                "💳 Subscription: " + ("✅ Active - " + str(sub_type) if is_sub else "❌ Not subscribed") + "\n"
                "👥 Friends referred: " + str(ref_count)
            )
        else:
            ts = len(sessions)
            avg_s = sum(s[0] for s in sessions) / ts
            avg_t = sum(s[1] for s in sessions) / ts
            pct = (avg_s / avg_t * 100) if avg_t > 0 else 0
            text = (
                "📊 Your Progress\n\n"
                "📝 Exams taken: " + str(ts) + "\n"
                "✅ Avg score: " + str(round(avg_s, 1)) + "/" + str(round(avg_t)) + "\n"
                "📈 Avg %: " + str(round(pct, 1)) + "%\n\n"
                "🆓 Free questions used: " + str(free_used) + "/5\n"
                "💳 Subscription: " + ("✅ Active - " + str(sub_type) if is_sub else "❌ Not subscribed") + "\n"
                "👥 Friends referred: " + str(ref_count) + "\n\n"
                "Use /referral to earn free access!"
            )
        await query.edit_message_text(text, reply_markup=back_to_main_keyboard())

    elif data == "show_referral":
        from app.handlers.user_features import referral_command
        await referral_command(update, context)

    elif data == "subscribe":
        from app.handlers.subscription import subscribe_handler
        await subscribe_handler(update, context)

    elif data == "help":
        await query.edit_message_text(
            "ℹ️ Help\n\n"
            "📌 Commands:\n"
            "/start - Main menu\n"
            "/redeem CODE - Redeem free access code\n"
            "/referral - Get your referral link\n\n"
            "📌 How to use:\n"
            "1️⃣ Choose your exam type\n"
            "2️⃣ Select stream or department\n"
            "3️⃣ Tap ▶️ Start Practice Exam\n"
            "4️⃣ Answer questions and see results\n\n"
            "🆓 New users get 5 free questions (one time).\n"
            "💳 Subscribe for 50 ETB/month for full access.\n\n"
            "📞 Contact admin: @John_3_13",
            reply_markup=back_to_main_keyboard())
''')

# ─────────────────────────────────────────────────────────
w("app/handlers/user_features.py", '''from telegram import Update
from telegram.ext import ContextTypes
from config import DATABASE_PATH
from app.keyboards.main_menu import back_to_main_keyboard
from app.utils.logger import logger
import aiosqlite
import random
import string


def gen_code(n=7):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


async def ensure_referral_code(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT referral_code FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        if row and row[0]:
            return row[0]
        code = gen_code()
        await db.execute(
            "UPDATE users SET referral_code=? WHERE telegram_id=?", (code, telegram_id))
        await db.commit()
        return code


async def redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args:
        await update.message.reply_text(
            "🎁 Usage: /redeem CODE\n\nExample: /redeem ABC12345")
        return
    code = args[0].strip().upper()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id,duration_days,max_uses,used_count FROM giveaway_codes WHERE code=?",
            (code,))
        gc = await cur.fetchone()
        if not gc:
            await update.message.reply_text("❌ Invalid code. Please check and try again.")
            return
        gc_id, duration_days, max_uses, used_count = gc
        if used_count >= max_uses:
            await update.message.reply_text(
                "❌ This code has reached its maximum uses. Contact admin for a new code.")
            return
        cur2 = await db.execute(
            "SELECT id FROM giveaway_uses WHERE code=? AND telegram_id=?",
            (code, user.id))
        if await cur2.fetchone():
            await update.message.reply_text("❌ You have already used this code.")
            return
        await db.execute(
            "UPDATE giveaway_codes SET used_count=used_count+1 WHERE code=?", (code,))
        await db.execute(
            "INSERT INTO giveaway_uses (code,telegram_id) VALUES (?,?)", (code, user.id))
        days_param = "+" + str(duration_days) + " days"
        await db.execute(
            "UPDATE users SET free_access_expiry=CASE "
            "WHEN free_access_expiry IS NULL OR free_access_expiry < datetime('now') "
            "THEN datetime('now',?) "
            "ELSE datetime(free_access_expiry,?) END "
            "WHERE telegram_id=?",
            (days_param, days_param, user.id))
        await db.commit()
    await update.message.reply_text(
        "🎉 Code redeemed successfully!\n\n"
        "✅ You now have " + str(duration_days) + " days of FREE access to all exams.\n\n"
        "Start practicing now! Send /start",
        reply_markup=back_to_main_keyboard())
    logger.info("🎁 User " + str(user.id) + " redeemed code " + code)


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user = update.effective_user
    else:
        user = update.callback_query.from_user
    code = await ensure_referral_code(user.id)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT referral_count FROM users WHERE telegram_id=?", (user.id,))
        row = await cur.fetchone()
        count = row[0] if row else 0
    me = await context.bot.get_me()
    link = "https://t.me/" + me.username + "?start=ref_" + code
    text = (
        "🎁 Your Referral Code: " + code + "\n\n"
        "🔗 Your Referral Link:\n" + link + "\n\n"
        "👥 Friends referred: " + str(count) + "\n\n"
        "🎯 For every 3 friends who join using your link,\n"
        "you get 7 days FREE access!\n\n"
        "Share your link and start earning! 🚀"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=back_to_main_keyboard())
    else:
        await update.callback_query.edit_message_text(
            text, reply_markup=back_to_main_keyboard())


async def handle_referral_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    if not args or not args[0].startswith("ref_"):
        return
    referrer_code = args[0].replace("ref_", "")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT telegram_id,referral_count FROM users WHERE referral_code=?",
            (referrer_code,))
        referrer = await cur.fetchone()
        if not referrer or referrer[0] == user.id:
            return
        cur2 = await db.execute(
            "SELECT referred_by FROM users WHERE telegram_id=?", (user.id,))
        me = await cur2.fetchone()
        if not me or me[0]:
            return
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
                "WHEN free_access_expiry IS NULL OR free_access_expiry < datetime('now') "
                "THEN datetime('now','+7 days') "
                "ELSE datetime(free_access_expiry,'+7 days') END "
                "WHERE telegram_id=?",
                (referrer[0],))
            try:
                await context.bot.send_message(
                    chat_id=referrer[0],
                    text="🎉 You earned 7 days FREE access!\n"
                    "You have now referred " + str(new_count) + " friends!\n\n"
                    "Keep sharing to earn more! 🚀")
            except Exception:
                pass
        await db.commit()
''')

# ─────────────────────────────────────────────────────────
w("app/handlers/subscription.py", '''from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.main_menu import (
    subscription_keyboard, back_to_main_keyboard,
    exam_select_for_sub_keyboard, stream_keyboard, build_dept_select_keyboard,
)
from config import DATABASE_PATH, ADMIN_USERNAME, SUBSCRIPTION_PRICE_ETB, ADMIN_ID
from app.utils.logger import logger
import aiosqlite


async def get_banks():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM bank_accounts WHERE is_active=1 ORDER BY bank_name")
        return [dict(r) for r in await cur.fetchall()]


async def get_depts(exam_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=? ORDER BY dept_name",
            (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 SUBSCRIPTION\n\n"
        "Price: " + str(SUBSCRIPTION_PRICE_ETB) + " ETB/month\n\n"
        "First choose which exam you want to subscribe to,\n"
        "then you will see the payment details.\n\n"
        "Choose your exam type:",
        reply_markup=exam_select_for_sub_keyboard())


async def sub_exam_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    exam_type = query.data.replace("sub_exam_", "")
    context.user_data["sub_exam_type"] = exam_type
    if exam_type == "entrance":
        await query.edit_message_text(
            "🎓 Entrance Exam Subscription\n\nChoose your stream:",
            reply_markup=stream_keyboard(prefix="sub_stream_"))
    elif exam_type == "exit":
        depts = await get_depts("exit")
        await query.edit_message_text(
            "🏛️ Exit Exam Subscription\n\nChoose your department:",
            reply_markup=build_dept_select_keyboard(depts, prefix="sub_dept_"))
    elif exam_type == "coc":
        depts = await get_depts("coc")
        await query.edit_message_text(
            "📋 CoC Exam Subscription\n\nChoose your department:",
            reply_markup=build_dept_select_keyboard(depts, prefix="sub_dept_"))
    elif exam_type in ("driving", "remedial"):
        context.user_data["sub_stream"] = "general"
        context.user_data["sub_dept"] = ""
        await show_payment_options(query, context)


async def sub_stream_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stream = query.data.replace("sub_stream_", "")
    context.user_data["sub_stream"] = stream
    context.user_data["sub_dept"] = ""
    await show_payment_options(query, context)


async def sub_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dept = query.data.replace("sub_dept_", "")
    context.user_data["sub_dept"] = dept
    context.user_data["sub_stream"] = ""
    await show_payment_options(query, context)


async def show_payment_options(query, context):
    banks = await get_banks()
    exam_type = context.user_data.get("sub_exam_type", "")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")
    label = exam_type.title()
    if stream and stream != "general":
        label += " / " + stream.title()
    if dept:
        label += " / " + dept.replace("_", " ").title()
    bank_text = ""
    for b in banks:
        bank_text += (
            "🏦 " + b["bank_name"] + "\n"
            "   Account: " + b["account_number"] + "\n"
            "   Name: " + b["account_name"] + "\n\n"
        )
    await query.edit_message_text(
        "💳 PAYMENT DETAILS\n\n"
        "📚 Selected: " + label + "\n"
        "💰 Amount: " + str(SUBSCRIPTION_PRICE_ETB) + " ETB\n\n"
        "Send payment to any of these accounts:\n\n" +
        bank_text +
        "📸 After paying, take a clear screenshot and tap\n"
        "Send Payment Screenshot below.\n\n"
        "📞 Admin: " + ADMIN_USERNAME,
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
        await query.edit_message_text(
            "❌ Bank info not found.", reply_markup=back_to_main_keyboard())
        return
    context.user_data["selected_bank"] = bank
    await query.edit_message_text(
        "🏦 PAY VIA " + bank.upper() + "\n\n"
        "Account Number: " + b["account_number"] + "\n"
        "Account Name: " + b["account_name"] + "\n"
        "Amount: " + str(SUBSCRIPTION_PRICE_ETB) + " ETB\n\n"
        "Steps:\n"
        "1️⃣ Open your " + bank + " app or visit the bank\n"
        "2️⃣ Transfer " + str(SUBSCRIPTION_PRICE_ETB) + " ETB to the account above\n"
        "3️⃣ Take a screenshot of the confirmation\n"
        "4️⃣ Tap Send Payment Screenshot below\n\n"
        "✅ Admin will activate your account after review.",
        reply_markup=subscription_keyboard())


async def send_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for_receipt"] = True
    await query.edit_message_text(
        "📸 Send Payment Receipt\n\n"
        "Please send a PHOTO/SCREENSHOT of your payment now.\n\n"
        "Make sure it clearly shows:\n"
        "✅ Your name\n"
        "✅ Amount paid\n"
        "✅ Date and time\n"
        "✅ Transaction reference\n\n"
        "Send the photo now:")


async def receipt_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not context.user_data.get("waiting_for_receipt"):
        return
    photo = update.message.photo
    if not photo:
        await update.message.reply_text(
            "❌ Please send a photo screenshot, not a document.")
        return
    file_id = photo[-1].file_id
    exam_type = context.user_data.get("sub_exam_type", "entrance")
    stream = context.user_data.get("sub_stream", "")
    dept = context.user_data.get("sub_dept", "")
    bank = context.user_data.get("selected_bank", "Unknown")
    context.user_data["waiting_for_receipt"] = False
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO payments (telegram_id,full_name,bank,receipt_file_id,exam_type,stream,dept) "
            "VALUES (?,?,?,?,?,?,?)",
            (user.id, user.full_name, bank, file_id, exam_type, stream, dept))
        payment_id = cur.lastrowid
        await db.commit()
    label = exam_type.title()
    if stream and stream != "general":
        label += "/" + stream
    if dept:
        label += "/" + dept.replace("_", " ").title()
    await update.message.reply_text(
        "✅ Receipt received! Thank you.\n\n"
        "📋 Details submitted:\n"
        "Exam: " + label + "\n"
        "Bank: " + bank + "\n\n"
        "⏳ Admin will review and activate your access soon.\n"
        "You will get a notification when approved.\n\n"
        "📞 Admin: " + ADMIN_USERNAME,
        reply_markup=back_to_main_keyboard())
    logger.info("🧾 Receipt from user " + str(user.id) + " payment ID " + str(payment_id))
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=file_id,
            caption=(
                "🧾 NEW PAYMENT RECEIPT\n\n"
                "👤 User: " + str(user.full_name or "Unknown") + "\n"
                "🆔 ID: " + str(user.id) + "\n"
                "🏦 Bank: " + bank + "\n"
                "📚 Exam: " + label + "\n"
                "🔢 Payment ID: " + str(payment_id) + "\n\n"
                "Use /admin to approve or reject."
            ))
    except Exception:
        pass
''')

# ─────────────────────────────────────────────────────────
w("app/handlers/exam.py", '''from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.exams.engine import get_questions, save_session, finish_session
from app.keyboards.main_menu import back_to_main_keyboard
from app.utils.access import (
    get_user, has_full_access,
    can_do_free_question, increment_free_questions
)
from app.utils.logger import logger
from config import PASS_MARK_PERCENT, FREE_QUESTIONS_LIMIT, DATABASE_PATH
import aiosqlite


async def get_subjects_db(exam_type, stream):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM subjects WHERE exam_type=? AND stream=? ORDER BY subject_name",
            (exam_type, stream))
        return [dict(r) for r in await cur.fetchall()]


async def get_years_db(exam_type, subject):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT year FROM questions "
            "WHERE exam_type=? AND subject=? AND year IS NOT NULL ORDER BY year DESC",
            (exam_type, subject))
        return [r[0] for r in await cur.fetchall()]


async def get_depts_db(exam_type):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM departments WHERE exam_type=? ORDER BY dept_name",
            (exam_type,))
        return [dict(r) for r in await cur.fetchall()]


async def subject_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = await get_user(user_id)
    if not user or not user.get("exam_type"):
        await query.edit_message_text(
            "⚠️ Please choose your exam type first from the main menu.",
            reply_markup=back_to_main_keyboard())
        return
    exam_type = user.get("exam_type")
    stream = user.get("stream", "natural")
    dept = user.get("department", "")

    if exam_type in ("exit", "coc"):
        depts = await get_depts_db(exam_type)
        keyboard = []
        for d in depts:
            keyboard.append([InlineKeyboardButton(
                d["emoji"] + " " + d["dept_name"],
                callback_data="user_dept_" + d["dept_key"])])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
        await query.edit_message_text(
            "🏛️ Choose your department:",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if exam_type == "driving":
        stream = "general"
    elif exam_type == "remedial":
        stream = user.get("stream", "natural")

    subjects = await get_subjects_db(exam_type, stream)
    if not subjects:
        await query.edit_message_text(
            "⚠️ No subjects available yet. Admin is adding soon!",
            reply_markup=back_to_main_keyboard())
        return
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(
            s["emoji"] + " " + s["subject_name"],
            callback_data="subject_" + s["subject_key"])])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    await query.edit_message_text(
        "📚 Choose a subject:",
        reply_markup=InlineKeyboardMarkup(keyboard))


async def user_dept_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dept = query.data.replace("user_dept_", "")
    user = await get_user(query.from_user.id)
    exam_type = user.get("exam_type", "exit") if user else "exit"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET department=?, stream=? WHERE telegram_id=?",
            (dept, dept, query.from_user.id))
        await db.commit()
    subjects = await get_subjects_db(exam_type, dept)
    if not subjects:
        await query.edit_message_text(
            "⚠️ No subjects for this department yet. Admin is adding soon!",
            reply_markup=back_to_main_keyboard())
        return
    keyboard = []
    for s in subjects:
        keyboard.append([InlineKeyboardButton(
            s["emoji"] + " " + s["subject_name"],
            callback_data="subject_" + s["subject_key"])])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_main")])
    await query.edit_message_text(
        "📚 Choose a subject:",
        reply_markup=InlineKeyboardMarkup(keyboard))


async def show_subject_intro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.replace("subject_", "")
    user_id = query.from_user.id
    user = await get_user(user_id)
    exam_type = user.get("exam_type", "entrance") if user else "entrance"
    stream = user.get("stream", "natural") if user else "natural"
    dept = user.get("department", "") if user else ""
    context.user_data["subject"] = subject
    context.user_data["exam_type"] = exam_type
    context.user_data["stream"] = stream
    context.user_data["dept"] = dept
    years = await get_years_db(exam_type, subject)
    label = subject.replace("_", " ").title()
    has_access = await has_full_access(user, exam_type, stream, dept)
    can_free, used = await can_do_free_question(user_id)
    if not has_access:
        if can_free:
            remaining = FREE_QUESTIONS_LIMIT - used
            access_note = (
                "\n\n🆓 FREE PREVIEW: " + str(remaining) + " questions remaining.\n"
                "💳 Subscribe for full access - 50 ETB/month"
            )
        else:
            access_note = (
                "\n\n❌ Free preview used up.\n"
                "💳 Subscribe for 50 ETB/month for full access."
            )
    else:
        access_note = "\n\n✅ Full access active."
    if years:
        keyboard = []
        row = []
        for y in sorted(years, reverse=True):
            row.append(InlineKeyboardButton(
                str(y),
                callback_data="examyear_" + subject + "_" + str(y)))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton(
            "📚 All Years",
            callback_data="examyear_" + subject + "_all")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="choose_subject")])
        await query.edit_message_text(
            "📘 " + label + "\n\n"
            "📅 Available years: " + str(len(years)) + "\n"
            "Choose a year:" + access_note,
            reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text(
            "📘 " + label + "\n\n"
            "❓ " + str(FREE_QUESTIONS_LIMIT if not has_access else QUESTIONS_PER_EXAM) +
            " questions | ✅ Instant feedback | 📖 Explanations" + access_note,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "▶️ Start Exam!",
                    callback_data="start_exam_" + subject + "__yall")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
            ]))


QUESTIONS_PER_EXAM = 10


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
        "📘 " + label + " - " + yr_label + "\n\nReady to start? 💪",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "▶️ Start Exam!",
                callback_data="start_exam_" + subject + "__y" + str(year or "all"))],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")],
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
    exam_type = user.get("exam_type", "entrance") if user else "entrance"
    stream = user.get("stream", "natural") if user else "natural"
    dept = user.get("department", "") if user else ""
    has_access = await has_full_access(user, exam_type, stream, dept)
    can_free, used = await can_do_free_question(user_id)
    if not has_access and not can_free:
        banks = []
        try:
            import aiosqlite
            async with aiosqlite.connect(DATABASE_PATH) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute(
                    "SELECT * FROM bank_accounts WHERE is_active=1 ORDER BY bank_name")
                banks = [dict(r) for r in await cur.fetchall()]
        except Exception:
            pass
        bank_text = ""
        for b in banks:
            bank_text += "🏦 " + b["bank_name"] + ": " + b["account_number"] + "\n"
        await query.edit_message_text(
            "❌ Free preview limit reached!\n\n"
            "You have used all " + str(FREE_QUESTIONS_LIMIT) + " free questions.\n\n"
            "💳 Subscribe for 50 ETB/month for unlimited access!\n\n"
            "Payment accounts:\n" + bank_text + "\n"
            "📞 Contact: @John_3_13\n\n"
            "Use /start and tap 💳 Subscribe to pay.",
            reply_markup=back_to_main_keyboard())
        return
    questions = await get_questions(exam_type, stream, subject, year)
    if not questions:
        await query.edit_message_text(
            "⚠️ No questions found for this selection.\n"
            "Admin is adding questions soon! Please check back later.",
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
    context.user_data["is_free"] = not has_access
    logger.info("▶️ User " + str(user_id) + " started: " + subject)
    await ask_question(query, context)


async def ask_question(query, context):
    questions = context.user_data["questions"]
    current = context.user_data["current_q"]
    session_id = context.user_data["session_id"]
    total = len(questions)
    q = questions[current]
    is_free = context.user_data.get("is_free", False)
    free_note = ""
    if is_free:
        free_note = " | 🆓 Free " + str(current + 1) + "/" + str(total)
    await query.edit_message_text(
        "📝 Question " + str(current + 1) + " of " + str(total) + free_note + "\n"
        + "─" * 30 + "\n\n"
        + q["question_text"] + "\n\n"
        + "🅐 " + q["option_a"] + "\n"
        + "🅑 " + q["option_b"] + "\n"
        + "🅒 " + q["option_c"] + "\n"
        + "🅓 " + q["option_d"],
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
    is_free = context.user_data.get("is_free", False)
    if not questions:
        await query.edit_message_text(
            "⚠️ Session expired. Please start again.",
            reply_markup=back_to_main_keyboard())
        return
    q = questions[current]
    correct = q["correct_answer"]
    is_correct = chosen == correct
    if is_correct:
        context.user_data["score"] += 1
    opts = {
        "A": q["option_a"], "B": q["option_b"],
        "C": q["option_c"], "D": q["option_d"]
    }
    if is_correct:
        result_line = "✅ Correct!"
    else:
        result_line = "❌ Wrong! Answer: " + correct + ") " + opts[correct]
    yr = ""
    if q.get("year"):
        yr = " | 📅 Year: " + str(q["year"])
    feedback = (
        result_line + "\n\n"
        "📖 Explanation:\n" + str(q.get("explanation") or "No explanation available.") + "\n\n"
        "📚 Reference: " + str(q.get("reference") or "N/A") + yr
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
        pct = (score / total) * 100
        passed = pct >= PASS_MARK_PERCENT
        result_emoji = "🏆" if passed else "📈"
        result_word = "PASSED! 🎉" if passed else "Keep practicing! 💪"
        final_text = (
            feedback + "\n\n"
            + "═" * 28 + "\n"
            + result_emoji + " EXAM COMPLETE!\n\n"
            + "📊 Score: " + str(score) + "/" + str(total)
            + " (" + str(round(pct)) + "%)\n"
            + "🎯 Result: " + result_word
        )
        if is_free:
            banks = []
            try:
                async with __import__("aiosqlite").connect(DATABASE_PATH) as db:
                    db.row_factory = __import__("aiosqlite").Row
                    cur = await db.execute(
                        "SELECT * FROM bank_accounts WHERE is_active=1 ORDER BY bank_name")
                    banks = [dict(r) for r in await cur.fetchall()]
            except Exception:
                pass
            bank_text = ""
            for b in banks:
                bank_text += "🏦 " + b["bank_name"] + ": " + b["account_number"] + "\n"
            final_text += (
                "\n\n" + "─" * 28 + "\n"
                "🆓 Free preview complete!\n\n"
                "💳 Subscribe for 50 ETB/month\nfor unlimited access to all exams!\n\n"
                "Payment accounts:\n" + bank_text + "\n"
                "📞 Contact: @John_3_13\n"
                "Use /start and tap 💳 Subscribe."
            )
            await query.edit_message_text(
                final_text, reply_markup=back_to_main_keyboard())
        else:
            await query.edit_message_text(
                final_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Again", callback_data="retry_exam")],
                    [InlineKeyboardButton("📊 My Progress", callback_data="my_progress")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="back_main")],
                ]))
        logger.info("✅ User " + str(query.from_user.id) + " finished: " + str(score) + "/" + str(total))
    else:
        await query.edit_message_text(
            feedback,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "➡️ Next (" + str(next_q + 1) + "/" + str(total) + ")",
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
        await query.edit_message_text(
            "⚠️ Please choose a subject.",
            reply_markup=back_to_main_keyboard())
''')

# ─────────────────────────────────────────────────────────
w("app/handlers/admin.py", '''from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
            "SELECT * FROM subjects WHERE exam_type=? AND stream=? ORDER BY subject_name",
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
        await update.message.reply_text("❌ Unauthorized.")
        return
    role = await get_admin_role(uid)
    await update.message.reply_text(
        "🔧 Admin Panel\n\nRole: " + (role or "super").upper(),
        reply_markup=admin_main_keyboard(role or "super"))


async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    if not await is_any_admin(uid):
        await query.edit_message_text("❌ Unauthorized.")
        return
    role = await get_admin_role(uid)
    is_super = (role == "super")

    if data == "admin_back":
        await query.edit_message_text(
            "🔧 Admin Panel",
            reply_markup=admin_main_keyboard(role or "super"))
    elif data == "admin_close":
        await query.edit_message_text("✅ Panel closed.")
    elif data == "admin_view_users":
        await show_users(query)
    elif data == "admin_stats":
        if not is_super:
            await query.edit_message_text("❌ No permission.", reply_markup=admin_back_keyboard())
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
            await query.edit_message_text("❌ No permission.", reply_markup=admin_back_keyboard())
            return
        await query.edit_message_text("👮 Manage Admins", reply_markup=manage_admins_keyboard())
    elif data == "admin_list_admins":
        await list_admins(query)
    elif data == "admin_add_subadmin":
        if not is_super:
            await query.edit_message_text("❌ No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "add_subadmin"
        await query.edit_message_text(
            "👮 Add Sub Admin\n\n"
            "Send the Telegram ID of the person.\n"
            "They must have started the bot first.\n\n"
            "Type /cancel to abort.")
    elif data == "admin_remove_admin":
        if not is_super:
            await query.edit_message_text("❌ No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "remove_admin"
        await query.edit_message_text(
            "🗑️ Remove Admin\n\nSend the Telegram ID.\n\nType /cancel to abort.")
    elif data == "admin_add_subject":
        context.user_data["waiting_for"] = "new_subject_info"
        await query.edit_message_text(
            "➕ Add Subject\n\n"
            "Format: exam_type|stream|key|name|emoji\n\n"
            "exam_type options:\n"
            "entrance, exit, coc, driving, remedial\n\n"
            "stream for entrance: natural or social\n"
            "stream for coc: use dept key e.g. coc_electrical\n"
            "stream for driving: general\n"
            "stream for remedial: natural or social\n\n"
            "Examples:\n"
            "entrance|natural|physics|Physics|⚡\n"
            "coc|coc_electrical|coc_elec_l3|Electrical Level 3|⚡\n"
            "driving|general|parking|Parking Rules|🅿️\n\n"
            "Type /cancel to abort.")
    elif data == "admin_edit_subject":
        context.user_data["waiting_for"] = "edit_subject_info"
        await query.edit_message_text(
            "✏️ Edit Subject\n\nFormat: old_key|new_name|new_emoji\n\n"
            "Example: physics|Advanced Physics|⚡\n\n"
            "Type /cancel to abort.")
    elif data == "admin_delete_subject":
        context.user_data["waiting_for"] = "delete_subject_key"
        await query.edit_message_text(
            "🗑️ Delete Subject\n\nSend the subject key.\n"
            "Use View Subjects to find keys.\n\nType /cancel to abort.")
    elif data == "admin_list_subjects":
        await list_subjects(query)
    elif data == "admin_add_dept":
        context.user_data["waiting_for"] = "new_dept_info"
        await query.edit_message_text(
            "➕ Add Department\n\n"
            "Format: exam_type|key|name|emoji\n\n"
            "exam_type: exit, coc, remedial, driving\n\n"
            "Examples:\n"
            "exit|nursing|Nursing|🩺\n"
            "coc|coc_welding|Welding|🔩\n"
            "remedial|remedial_math|Remedial Math|🧮\n\n"
            "Type /cancel to abort.")
    elif data == "admin_edit_dept":
        context.user_data["waiting_for"] = "edit_dept_info"
        await query.edit_message_text(
            "✏️ Edit Department\n\nFormat: old_key|new_name|new_emoji\n\n"
            "Example: law|Ethiopian Law|⚖️\n\nType /cancel to abort.")
    elif data == "admin_delete_dept":
        context.user_data["waiting_for"] = "delete_dept_key"
        await query.edit_message_text(
            "🗑️ Delete Department\n\nSend the department key.\n\nType /cancel to abort.")
    elif data == "admin_list_depts":
        await list_depts(query)
    elif data == "admin_add_question":
        context.user_data.clear()
        await query.edit_message_text(
            "➕ Add Question\n\nStep 1: Choose exam type:",
            reply_markup=admin_exam_type_keyboard())
    elif data == "admin_edit_question":
        context.user_data["waiting_for"] = "edit_question_id"
        await query.edit_message_text(
            "✏️ Edit Question\n\nSend the question ID.\n"
            "Use View Questions to find IDs.\n\nType /cancel to abort.")
    elif data == "admin_delete_question":
        context.user_data["waiting_for"] = "delete_question_id"
        await query.edit_message_text(
            "🗑️ Delete Question\n\nSend the question ID.\n\nType /cancel to abort.")
    elif data == "admin_upload_file":
        context.user_data["waiting_for"] = "question_file"
        await query.edit_message_text(
            "📄 Upload Question File\n\n"
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
            "💳 Grant Subscription\n\n"
            "Format: telegram_id|days|exam_type|stream_or_dept\n\n"
            "Examples:\n"
            "123456789|30|entrance|natural\n"
            "123456789|30|exit|medicine\n"
            "123456789|30|coc|coc_electrical\n"
            "123456789|30|driving|general\n"
            "123456789|30|remedial|natural\n\n"
            "Type /cancel to abort.")
    elif data == "admin_giveaway":
        await query.edit_message_text("🎁 Giveaway Free Access", reply_markup=giveaway_keyboard())
    elif data == "admin_create_giveaway":
        context.user_data["waiting_for"] = "giveaway_info"
        await query.edit_message_text(
            "🎁 Create Giveaway Code\n\n"
            "Format: days|max_uses\n\n"
            "Examples:\n"
            "7|100   = 7 days free, up to 100 students\n"
            "30|1    = 30 days, 1 student only\n"
            "3|500   = 3 days, 500 students\n\n"
            "Type /cancel to abort.")
    elif data == "admin_list_giveaways":
        await list_giveaways(query)
    elif data == "admin_broadcast":
        context.user_data["waiting_for"] = "broadcast_msg"
        await query.edit_message_text(
            "📢 Broadcast Message\n\n"
            "Type your message to send to ALL users.\n"
            "Type /cancel to abort.")
    elif data == "admin_pending_receipts":
        await show_pending_receipts(query, context)
    elif data == "admin_edit_banks":
        if not is_super:
            await query.edit_message_text("❌ No permission.", reply_markup=admin_back_keyboard())
            return
        context.user_data["waiting_for"] = "edit_bank_info"
        await query.edit_message_text(
            "🏦 Edit Bank Account\n\n"
            "Format: bank_name|account_number|account_name\n\n"
            "To update existing: CBE|1000482304102|New Name\n"
            "To add new bank: Telebirr|0912345678|Account Name\n\n"
            "Type /cancel to abort.")
    elif data == "admin_cancel_question":
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Cancelled.", reply_markup=admin_main_keyboard(role or "super"))
    elif data.startswith("aq_subject_"):
        subject = data.replace("aq_subject_", "")
        context.user_data["aq_subject"] = subject
        context.user_data["aq_subject_label"] = subject.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            "📘 Subject: " + context.user_data["aq_subject_label"] + "\n\n"
            "Type the question text:\n"
            "Type /cancel to abort.")
    elif data.startswith("aq_dept_"):
        dept = data.replace("aq_dept_", "")
        context.user_data["aq_stream"] = dept
        context.user_data["aq_subject"] = dept
        context.user_data["aq_subject_label"] = dept.replace("_", " ").title()
        context.user_data["waiting_for"] = "aq_question_text"
        await query.edit_message_text(
            "🏛️ Department: " + context.user_data["aq_subject_label"] + "\n\n"
            "Type the question text:\n"
            "Type /cancel to abort.")
    elif data.startswith("edit_q_field_"):
        field = data.replace("edit_q_field_", "")
        context.user_data["edit_field"] = field
        context.user_data["waiting_for"] = "edit_q_value"
        labels = {
            "question_text": "question text",
            "option_a": "Option A", "option_b": "Option B",
            "option_c": "Option C", "option_d": "Option D",
            "correct_answer": "correct answer (A/B/C/D)",
            "explanation": "explanation",
            "reference": "reference",
            "year": "year (number or type none)",
        }
        await query.edit_message_text(
            "✏️ Send the new " + labels.get(field, field) + ":")
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
        await query.edit_message_text(
            "🎓 Choose stream:", reply_markup=admin_stream_keyboard())
    elif data == "aq_type_exit":
        context.user_data["aq_exam_type"] = "exit"
        if has_upload:
            context.user_data["upload_exam_type"] = "exit"
        depts = await get_depts("exit")
        await query.edit_message_text(
            "🏛️ Choose department:", reply_markup=build_dept_keyboard(depts))
    elif data == "aq_type_coc":
        context.user_data["aq_exam_type"] = "coc"
        if has_upload:
            context.user_data["upload_exam_type"] = "coc"
        depts = await get_depts("coc")
        await query.edit_message_text(
            "📋 Choose CoC department:", reply_markup=build_dept_keyboard(depts))
    elif data == "aq_type_driving":
        context.user_data["aq_exam_type"] = "driving"
        context.user_data["aq_stream"] = "general"
        if has_upload:
            context.user_data["upload_exam_type"] = "driving"
            context.user_data["upload_stream"] = "general"
        subjects = await get_subjects("driving", "general")
        prefix = "upload_subject_" if has_upload else "aq_subject_"
        await query.edit_message_text(
            "🚗 Choose subject:", reply_markup=build_subject_keyboard(subjects, prefix=prefix))
    elif data == "aq_type_remedial":
        context.user_data["aq_exam_type"] = "remedial"
        if has_upload:
            context.user_data["upload_exam_type"] = "remedial"
        await query.edit_message_text(
            "📝 Choose stream:", reply_markup=admin_stream_keyboard())
    elif data == "aq_stream_natural":
        exam_type = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "natural"
        subjects = await get_subjects(exam_type, "natural")
        if has_upload:
            context.user_data["upload_stream"] = "natural"
            await query.edit_message_text(
                "📚 Choose subject:",
                reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "📚 Choose subject:", reply_markup=build_subject_keyboard(subjects))
    elif data == "aq_stream_social":
        exam_type = context.user_data.get("aq_exam_type", "entrance")
        context.user_data["aq_stream"] = "social"
        subjects = await get_subjects(exam_type, "social")
        if has_upload:
            context.user_data["upload_stream"] = "social"
            await query.edit_message_text(
                "📚 Choose subject:",
                reply_markup=build_subject_keyboard(subjects, prefix="upload_subject_"))
        else:
            await query.edit_message_text(
                "📚 Choose subject:", reply_markup=build_subject_keyboard(subjects))
    elif data.startswith("aq_dept_") and has_upload:
        dept = data.replace("aq_dept_", "")
        context.user_data["upload_stream"] = dept
        context.user_data["upload_subject"] = dept
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "exit")
        await query.edit_message_text(
            "📋 Ready to save " + str(len(parsed)) + " questions\n"
            "Department: " + dept.replace("_", " ").title() + "\n"
            "Exam: " + exam_type.title() + "\n\nConfirm?",
            reply_markup=admin_confirm_keyboard())
    elif data.startswith("upload_subject_"):
        subject = data.replace("upload_subject_", "")
        context.user_data["upload_subject"] = subject
        parsed = context.user_data.get("parsed_questions", [])
        exam_type = context.user_data.get("upload_exam_type", "entrance")
        stream = context.user_data.get("upload_stream", "natural")
        await query.edit_message_text(
            "📋 Ready to save " + str(len(parsed)) + " questions\n"
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
        await update.message.reply_text(
            "❌ Cancelled.", reply_markup=admin_main_keyboard(role or "super"))
        return

    simple_steps = {
        "aq_question_text": ("aq_option_a", "✅ Saved.\n\n🅐 Type Option A:"),
        "aq_option_a":      ("aq_option_b", "✅ Saved.\n\n🅑 Type Option B:"),
        "aq_option_b":      ("aq_option_c", "✅ Saved.\n\n🅒 Type Option C:"),
        "aq_option_c":      ("aq_option_d", "✅ Saved.\n\n🅓 Type Option D:"),
    }

    if waiting in simple_steps:
        context.user_data[waiting] = text
        nxt, msg = simple_steps[waiting]
        context.user_data["waiting_for"] = nxt
        await update.message.reply_text(msg)

    elif waiting == "aq_option_d":
        context.user_data["aq_option_d"] = text
        context.user_data["waiting_for"] = "aq_correct_answer"
        await update.message.reply_text("✅ Saved.\n\n❓ Correct answer: A, B, C, or D")

    elif waiting == "aq_correct_answer":
        if text.upper() not in ["A","B","C","D"]:
            await update.message.reply_text("❌ Must be A, B, C, or D. Try again:")
            return
        context.user_data["aq_correct_answer"] = text.upper()
        context.user_data["waiting_for"] = "aq_explanation"
        await update.message.reply_text("✅ Saved.\n\n📖 Type the explanation:")

    elif waiting == "aq_explanation":
        context.user_data["aq_explanation"] = text
        context.user_data["waiting_for"] = "aq_reference"
        await update.message.reply_text("✅ Saved.\n\n📚 Type reference or type none:")

    elif waiting == "aq_reference":
        context.user_data["aq_reference"] = "" if text.lower() == "none" else text
        context.user_data["waiting_for"] = "aq_year"
        await update.message.reply_text("✅ Saved.\n\n📅 Type exam year (e.g. 2023) or none:")

    elif waiting == "aq_year":
        try:
            context.user_data["aq_year"] = int(text) if text.lower() != "none" else None
        except ValueError:
            context.user_data["aq_year"] = None
        context.user_data["waiting_for"] = None
        d = context.user_data
        preview = (
            "📋 QUESTION PREVIEW\n\n"
            "📘 Subject: " + str(d.get("aq_subject_label")) + "\n"
            "🎓 Exam: " + str(d.get("aq_exam_type", "")).title() + "\n"
            "📂 Stream: " + str(d.get("aq_stream", "")).title() + "\n"
            "📅 Year: " + str(d.get("aq_year") or "N/A") + "\n\n"
            "❓ " + str(d.get("aq_question_text")) + "\n\n"
            "🅐 " + str(d.get("aq_option_a")) + "\n"
            "🅑 " + str(d.get("aq_option_b")) + "\n"
            "🅒 " + str(d.get("aq_option_c")) + "\n"
            "🅓 " + str(d.get("aq_option_d")) + "\n\n"
            "✅ Answer: " + str(d.get("aq_correct_answer")) + "\n"
            "📖 Explanation: " + str(d.get("aq_explanation")) + "\n"
            "📚 Reference: " + str(d.get("aq_reference") or "N/A")
        )
        await update.message.reply_text(preview, reply_markup=admin_confirm_keyboard())

    elif waiting == "grant_sub_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 4:
            await update.message.reply_text(
                "❌ Wrong format.\n"
                "Use: telegram_id|days|exam_type|stream_or_dept\n\n"
                "Example: 123456789|30|entrance|natural")
            return
        try:
            tid = int(parts[0])
            days = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ ID and days must be numbers.")
            return
        exam_type = parts[2].strip()
        stream_or_dept = parts[3].strip()
        stream = stream_or_dept if exam_type == "entrance" else ""
        dept = stream_or_dept if exam_type in ("exit","coc") else ""
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("❌ User not found. They must /start first.")
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
            label += " / " + dept.replace("_"," ").title()
        await update.message.reply_text(
            "✅ Subscription granted!\n\n"
            "👤 User: " + str(row[0] or tid) + "\n"
            "📚 Access: " + label + "\n"
            "📅 Duration: " + str(days) + " days",
            reply_markup=admin_back_keyboard())
        try:
            await context.bot.send_message(
                chat_id=tid,
                text="🎉 Your subscription is activated!\n\n"
                "📚 Access: " + label + "\n"
                "📅 Duration: " + str(days) + " days\n\n"
                "Start practicing now! Send /start 🚀")
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
            "📢 Broadcast done!\n✅ Sent: " + str(sent) + "\n❌ Failed: " + str(failed),
            reply_markup=admin_back_keyboard())

    elif waiting == "new_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) not in [4, 5]:
            await update.message.reply_text(
                "❌ Wrong format.\n"
                "Use: exam_type|stream|key|name|emoji\n"
                "emoji is optional.\n\n"
                "Example: entrance|natural|physics|Physics|⚡")
            return
        exam_type = parts[0]
        stream = parts[1]
        key = parts[2]
        name = parts[3]
        emoji = parts[4] if len(parts) == 5 else "📘"
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO subjects (exam_type,stream,subject_key,subject_name,emoji) "
                    "VALUES (?,?,?,?,?)",
                    (exam_type, stream, key, name, emoji))
                await db.commit()
                await update.message.reply_text(
                    "✅ Subject added: " + emoji + " " + name,
                    reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(
                    "❌ Error: " + str(e) + "\nMaybe key already exists.",
                    reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_subject_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            await update.message.reply_text("❌ Format: old_key|new_name|new_emoji")
            return
        old_key = parts[0]
        new_name = parts[1]
        new_emoji = parts[2] if len(parts) >= 3 else None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id FROM subjects WHERE subject_key=?", (old_key,))
            if not await cur.fetchone():
                await update.message.reply_text("❌ Key not found: " + old_key)
                context.user_data.clear()
                return
            if new_emoji:
                await db.execute(
                    "UPDATE subjects SET subject_name=?, emoji=? WHERE subject_key=?",
                    (new_name, new_emoji, old_key))
            else:
                await db.execute(
                    "UPDATE subjects SET subject_name=? WHERE subject_key=?",
                    (new_name, old_key))
            await db.commit()
        await update.message.reply_text(
            "✅ Subject updated: " + new_name, reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_subject_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT subject_name FROM subjects WHERE subject_key=?", (text,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("❌ Key not found: " + text)
                context.user_data.clear()
                return
            await db.execute("DELETE FROM subjects WHERE subject_key=?", (text,))
            await db.commit()
        await update.message.reply_text(
            "✅ Subject deleted: " + row[0], reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "new_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) not in [3, 4]:
            await update.message.reply_text(
                "❌ Format: exam_type|key|name|emoji\n"
                "emoji is optional.\n\n"
                "Example: coc|coc_welding|Welding|🔩")
            return
        exam_type = parts[0]
        key = parts[1]
        name = parts[2]
        emoji = parts[3] if len(parts) == 4 else "🏛️"
        async with aiosqlite.connect(DATABASE_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO departments (exam_type,dept_key,dept_name,emoji) VALUES (?,?,?,?)",
                    (exam_type, key, name, emoji))
                await db.commit()
                await update.message.reply_text(
                    "✅ Department added: " + emoji + " " + name,
                    reply_markup=admin_back_keyboard())
            except Exception as e:
                await update.message.reply_text(
                    "❌ Error: " + str(e), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_dept_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) < 2:
            await update.message.reply_text("❌ Format: old_key|new_name|new_emoji")
            return
        old_key = parts[0]
        new_name = parts[1]
        new_emoji = parts[2] if len(parts) >= 3 else None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT id FROM departments WHERE dept_key=?", (old_key,))
            if not await cur.fetchone():
                await update.message.reply_text("❌ Key not found: " + old_key)
                context.user_data.clear()
                return
            if new_emoji:
                await db.execute(
                    "UPDATE departments SET dept_name=?, emoji=? WHERE dept_key=?",
                    (new_name, new_emoji, old_key))
            else:
                await db.execute(
                    "UPDATE departments SET dept_name=? WHERE dept_key=?",
                    (new_name, old_key))
            await db.commit()
        await update.message.reply_text(
            "✅ Department updated: " + new_name, reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "delete_dept_key":
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT dept_name FROM departments WHERE dept_key=?", (text,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("❌ Key not found: " + text)
                context.user_data.clear()
                return
            await db.execute("DELETE FROM departments WHERE dept_key=?", (text,))
            await db.commit()
        await update.message.reply_text(
            "✅ Department deleted: " + row[0], reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "add_subadmin":
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute(
                "SELECT full_name FROM users WHERE telegram_id=?", (tid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("❌ User not found. They must /start first.")
                context.user_data.clear()
                return
            try:
                await db.execute(
                    "INSERT INTO admin_users (telegram_id,full_name,role,added_by) VALUES (?,?,'sub',?)",
                    (tid, row[0], uid))
                await db.commit()
                await update.message.reply_text(
                    "✅ Sub admin added: " + str(row[0] or tid),
                    reply_markup=admin_back_keyboard())
                try:
                    await context.bot.send_message(
                        chat_id=tid,
                        text="👮 You have been added as a Sub Admin!\n"
                        "Use /admin to access the admin panel.")
                except Exception:
                    pass
            except Exception as e:
                await update.message.reply_text("❌ Error: " + str(e))
        context.user_data.clear()

    elif waiting == "remove_admin":
        try:
            tid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("DELETE FROM admin_users WHERE telegram_id=?", (tid,))
            await db.commit()
        await update.message.reply_text(
            "✅ Admin removed: " + str(tid), reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "edit_question_id":
        try:
            qid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM questions WHERE id=?", (qid,))
            row = await cur.fetchone()
        if not row:
            await update.message.reply_text("❌ Question ID " + str(qid) + " not found.")
            context.user_data.clear()
            return
        q = dict(row)
        context.user_data["edit_question_id"] = qid
        context.user_data["waiting_for"] = None
        preview = (
            "📋 ID:" + str(q["id"]) + " | " + str(q["subject"]) + " | " + str(q.get("year") or "N/A") + "\n\n"
            "❓ " + str(q["question_text"]) + "\n\n"
            "🅐 " + str(q["option_a"]) + "\n"
            "🅑 " + str(q["option_b"]) + "\n"
            "🅒 " + str(q["option_c"]) + "\n"
            "🅓 " + str(q["option_d"]) + "\n\n"
            "✅ Answer: " + str(q["correct_answer"]) + "\n"
            "📖 " + str(q.get("explanation") or "") + "\n"
            "📚 " + str(q.get("reference") or "")
        )
        edit_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Edit Question", callback_data="edit_q_field_question_text")],
            [InlineKeyboardButton("🅐 Edit A", callback_data="edit_q_field_option_a"),
             InlineKeyboardButton("🅑 Edit B", callback_data="edit_q_field_option_b")],
            [InlineKeyboardButton("🅒 Edit C", callback_data="edit_q_field_option_c"),
             InlineKeyboardButton("🅓 Edit D", callback_data="edit_q_field_option_d")],
            [InlineKeyboardButton("✅ Edit Answer", callback_data="edit_q_field_correct_answer")],
            [InlineKeyboardButton("📖 Edit Explanation", callback_data="edit_q_field_explanation")],
            [InlineKeyboardButton("📚 Edit Reference", callback_data="edit_q_field_reference")],
            [InlineKeyboardButton("📅 Edit Year", callback_data="edit_q_field_year")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
        ])
        await update.message.reply_text(preview, reply_markup=edit_kb)

    elif waiting == "edit_q_value":
        qid = context.user_data.get("edit_question_id")
        field = context.user_data.get("edit_field")
        if not qid or not field:
            await update.message.reply_text("❌ Session expired. Try again.")
            context.user_data.clear()
            return
        value = text
        if field == "correct_answer":
            value = text.upper()
            if value not in ["A","B","C","D"]:
                await update.message.reply_text("❌ Must be A, B, C, or D.")
                return
        if field == "year":
            try:
                value = int(text) if text.lower() != "none" else None
            except ValueError:
                value = None
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "UPDATE questions SET " + field + "=? WHERE id=?", (value, qid))
            await db.commit()
        context.user_data["waiting_for"] = None
        await update.message.reply_text(
            "✅ Question " + str(qid) + " updated!", reply_markup=admin_back_keyboard())

    elif waiting == "delete_question_id":
        try:
            qid = int(text)
        except ValueError:
            await update.message.reply_text("❌ Must be a number.")
            return
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cur = await db.execute("SELECT subject FROM questions WHERE id=?", (qid,))
            row = await cur.fetchone()
            if not row:
                await update.message.reply_text("❌ Not found: " + str(qid))
                context.user_data.clear()
                return
            await db.execute("DELETE FROM questions WHERE id=?", (qid,))
            await db.commit()
        await update.message.reply_text(
            "✅ Question " + str(qid) + " deleted.", reply_markup=admin_back_keyboard())
        context.user_data.clear()

    elif waiting == "giveaway_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 2:
            await update.message.reply_text("❌ Format: days|max_uses\n\nExample: 7|100")
            return
        try:
            days = int(parts[0])
            max_uses = int(parts[1])
        except ValueError:
            await update.message.reply_text("❌ Both must be numbers.")
            return
        code = gen_code()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO giveaway_codes (code,duration_days,max_uses,created_by) VALUES (?,?,?,?)",
                (code, days, max_uses, uid))
            await db.commit()
        context.user_data.clear()
        await update.message.reply_text(
            "🎁 Giveaway Code Created!\n\n"
            "🔑 Code: " + code + "\n"
            "📅 Duration: " + str(days) + " days free access\n"
            "👥 Max uses: " + str(max_uses) + " students\n\n"
            "📤 Students redeem with:\n/redeem " + code,
            reply_markup=admin_back_keyboard())

    elif waiting == "edit_bank_info":
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("❌ Format: bank_name|account_number|account_name")
            return
        bank_name, acc_num, acc_name = parts
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO bank_accounts (bank_name,account_number,account_name) VALUES (?,?,?) "
                "ON CONFLICT(bank_name) DO UPDATE SET "
                "account_number=excluded.account_number, account_name=excluded.account_name",
                (bank_name, acc_num, acc_name))
            await db.commit()
        await update.message.reply_text(
            "✅ Bank updated!\n🏦 " + bank_name + "\n💳 " + acc_num + "\n👤 " + acc_name,
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
        await update.message.reply_text("❌ Please send a .txt file only.")
        return
    await update.message.reply_text("⏳ Reading file...")
    file = await context.bot.get_file(doc.file_id)
    content = bytes(await file.download_as_bytearray()).decode("utf-8", errors="ignore")
    parsed = parse_questions_from_text(content)
    if not parsed:
        await update.message.reply_text("❌ No valid questions found. Check the format.")
        return
    context.user_data["parsed_questions"] = parsed
    context.user_data["waiting_for"] = "upload_exam_type"
    await update.message.reply_text(
        "✅ Found " + str(len(parsed)) + " questions!\n\n"
        "Now choose the exam type:",
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
        "✅ Upload done!\n📥 Saved: " + str(saved) + "\n❌ Failed: " + str(failed),
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
        await query.edit_message_text(
            "✅ Question saved successfully!", reply_markup=admin_main_keyboard())
    except Exception as e:
        await query.edit_message_text("❌ Error: " + str(e), reply_markup=admin_main_keyboard())


async def show_users(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        sub = (await (await db.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1")).fetchone())[0]
        today = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(last_active)=date('now')")).fetchone())[0]
        new_today = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE date(created_at)=date('now')")).fetchone())[0]
        cur = await db.execute(
            "SELECT telegram_id,full_name,is_subscribed,subscribed_exam_type "
            "FROM users ORDER BY created_at DESC LIMIT 15")
        recent = await cur.fetchall()
    lines = ""
    for r in recent:
        tag = "💳[" + str(r[3] or "") + "]" if r[2] else "🆓"
        lines += tag + " " + str(r[1] or "Unknown") + " (" + str(r[0]) + ")\n"
    await query.edit_message_text(
        "👥 USERS\n\n"
        "📊 Total: " + str(total) + "\n"
        "💳 Subscribed: " + str(sub) + "\n"
        "🆓 Free: " + str(total - sub) + "\n"
        "🟢 Active today: " + str(today) + "\n"
        "🆕 New today: " + str(new_today) + "\n\n"
        "📋 Recent 15:\n" + lines,
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
        cur = await db.execute(
            "SELECT subject,COUNT(*) FROM exam_sessions WHERE completed=1 "
            "GROUP BY subject ORDER BY COUNT(*) DESC LIMIT 5")
        pop = await cur.fetchall()
    pop_text = "\n".join("  " + p[0].replace("_"," ").title() + ": " + str(p[1]) for p in pop) or "None yet"
    await query.edit_message_text(
        "📊 STATISTICS\n\n"
        "📝 Total Exams: " + str(exams) + "\n"
        "❓ Questions: " + str(qcount) + "\n"
        "📈 Avg Score: " + str(round(avg,1)) + "%\n"
        "🧾 Pending Receipts: " + str(pending) + "\n\n"
        "🔥 Popular Subjects:\n" + pop_text,
        reply_markup=admin_back_keyboard())


async def show_questions(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT id,exam_type,subject,year,question_text FROM questions "
            "ORDER BY exam_type,subject,year DESC LIMIT 30")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("❓ No questions yet.", reply_markup=admin_back_keyboard())
        return
    text = "❓ Questions (up to 30)\n\n"
    for r in rows:
        yr = str(r[3]) if r[3] else "N/A"
        qs = r[4][:35] + "..." if len(r[4]) > 35 else r[4]
        text += "🔢 ID:" + str(r[0]) + " [" + str(r[2]) + "] 📅" + yr + "\n" + qs + "\n\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_subjects(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT exam_type,stream,subject_key,subject_name,emoji "
            "FROM subjects ORDER BY exam_type,stream,subject_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("📚 No subjects yet.", reply_markup=admin_back_keyboard())
        return
    text = "📚 ALL SUBJECTS\n\n"
    for r in rows:
        text += str(r[4]) + " " + str(r[3]) + "\n  (" + str(r[0]) + "/" + str(r[1]) + ") key=" + str(r[2]) + "\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_depts(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT exam_type,dept_key,dept_name,emoji "
            "FROM departments ORDER BY exam_type,dept_name")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("🏛️ No departments yet.", reply_markup=admin_back_keyboard())
        return
    text = "🏛️ ALL DEPARTMENTS\n\n"
    for r in rows:
        text += str(r[3]) + " " + str(r[2]) + "\n  (" + str(r[0]) + ") key=" + str(r[1]) + "\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_admins(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT telegram_id,full_name,role FROM admin_users ORDER BY role")
        rows = await cur.fetchall()
    text = "👮 ALL ADMINS\n\n"
    text += "👑 [SUPER] Main Admin (" + str(ADMIN_ID) + ")\n"
    for r in rows:
        text += "🔰 [" + str(r[2]).upper() + "] " + str(r[1] or "Unknown") + " (" + str(r[0]) + ")\n"
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def list_giveaways(query):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT code,duration_days,max_uses,used_count,created_at "
            "FROM giveaway_codes ORDER BY created_at DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("🎁 No giveaway codes yet.", reply_markup=admin_back_keyboard())
        return
    text = "🎁 GIVEAWAY CODES\n\n"
    for r in rows:
        text += ("🔑 Code: " + str(r[0]) + "\n"
                 "📅 " + str(r[1]) + " days | "
                 "👥 " + str(r[3]) + "/" + str(r[2]) + " used\n"
                 "📆 Created: " + str(r[4])[:10] + "\n\n")
    await query.edit_message_text(text, reply_markup=admin_back_keyboard())


async def show_pending_receipts(query, context):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id,telegram_id,full_name,bank,exam_type,stream,dept,created_at,receipt_file_id "
            "FROM payments WHERE status='pending' ORDER BY created_at ASC LIMIT 5")
        rows = [dict(r) for r in await cur.fetchall()]
    if not rows:
        await query.edit_message_text("✅ No pending receipts.", reply_markup=admin_back_keyboard())
        return
    for p in rows:
        label = str(p["exam_type"] or "")
        if p["stream"] and p["stream"] != "general":
            label += "/" + str(p["stream"])
        if p["dept"]:
            label += "/" + str(p["dept"]).replace("_"," ").title()
        caption = (
            "🧾 PENDING RECEIPT\n\n"
            "👤 User: " + str(p["full_name"] or "Unknown") + "\n"
            "🆔 ID: " + str(p["telegram_id"]) + "\n"
            "🏦 Bank: " + str(p["bank"]) + "\n"
            "📚 Exam: " + label + "\n"
            "📆 Date: " + str(p["created_at"])[:10]
        )
        kb = receipt_action_keyboard(
            p["id"], p["telegram_id"],
            p["exam_type"] or "", p["stream"] or "", p["dept"] or "")
        try:
            await context.bot.send_photo(
                chat_id=query.from_user.id,
                photo=p["receipt_file_id"],
                caption=caption, reply_markup=kb)
        except Exception:
            await context.bot.send_message(
                chat_id=query.from_user.id, text=caption, reply_markup=kb)


async def approve_receipt(query, context, data):
    parts = data.replace("rcpt_ok_", "").split("_")
    payment_id = int(parts[0])
    telegram_id = int(parts[1])
    exam_type = parts[2] if len(parts) > 2 else "entrance"
    stream = parts[3] if len(parts) > 3 and parts[3] not in ("", "None") else ""
    dept = parts[4] if len(parts) > 4 and parts[4] not in ("", "None") else ""
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
    try:
        await query.edit_message_caption("✅ APPROVED - Subscription activated.")
    except Exception:
        pass
    label = exam_type.title()
    if stream and stream != "general":
        label += " / " + stream.title()
    if dept:
        label += " / " + dept.replace("_"," ").title()
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="🎉 Your payment is approved!\n\n"
            "✅ Access: " + label + "\n"
            "📅 Duration: 30 days\n\n"
            "Start practicing now! Send /start 🚀")
    except Exception:
        pass


async def reject_receipt(query, context, data):
    parts = data.replace("rcpt_no_", "").split("_")
    payment_id = int(parts[0])
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
            text="❌ Your payment receipt was not approved.\n\n"
            "Please make sure you sent the correct amount to the correct account.\n"
            "Contact admin: @John_3_13 for help.")
    except Exception:
        pass
''')

# ─────────────────────────────────────────────────────────
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
        logger.info("✅ Bot started!")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("redeem", redeem_command))
    app.add_handler(CommandHandler("referral", referral_command))

    # Admin upload flow (must be before admin_button_handler)
    app.add_handler(CallbackQueryHandler(
        admin_upload_handler,
        pattern="^(aq_type_|aq_stream_|upload_subject_|aq_confirm_save|aq_dept_)"))

    # Admin panel buttons
    app.add_handler(CallbackQueryHandler(
        admin_button_handler,
        pattern="^(admin_|aq_subject_|edit_q_field_|rcpt_ok_|rcpt_no_)"))

    # Subscription flow
    app.add_handler(CallbackQueryHandler(subscribe_handler, pattern="^subscribe$"))
    app.add_handler(CallbackQueryHandler(sub_exam_select_handler, pattern="^sub_exam_"))
    app.add_handler(CallbackQueryHandler(sub_stream_select, pattern="^sub_stream_"))
    app.add_handler(CallbackQueryHandler(sub_dept_select, pattern="^sub_dept_"))
    app.add_handler(CallbackQueryHandler(pay_bank_handler, pattern="^pay_"))
    app.add_handler(CallbackQueryHandler(send_receipt_handler, pattern="^send_receipt$"))

    # Exam flow
    app.add_handler(CallbackQueryHandler(subject_selection_handler, pattern="^choose_subject$"))
    app.add_handler(CallbackQueryHandler(user_dept_select, pattern="^user_dept_"))
    app.add_handler(CallbackQueryHandler(show_subject_intro, pattern="^subject_"))
    app.add_handler(CallbackQueryHandler(year_select_handler, pattern="^examyear_"))
    app.add_handler(CallbackQueryHandler(start_exam_handler, pattern="^start_exam_"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern="^answer_"))
    app.add_handler(CallbackQueryHandler(next_question_handler, pattern="^next_question$"))
    app.add_handler(CallbackQueryHandler(retry_exam_handler, pattern="^retry_exam$"))

    # Stream and dept selection for exam type setup
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(exam_type_|stream_|rem_stream_|dept_select_|back_main|my_progress|show_referral|help)"))

    # Catch-all for remaining buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.PHOTO, receipt_photo_handler))
    app.add_handler(MessageHandler(filters.Document.TXT, admin_file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler))

    logger.info("✅ Handlers registered. Bot is polling...")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
''')

print("\n✅ All files written successfully!")
print("Now run:")
print("  Remove-Item -Force data\\exam_bot.db -ErrorAction SilentlyContinue")
print("  python main.py")