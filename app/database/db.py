"""
app/database/db.py  — COMPLETE REWRITE
========================================
CHANGES:
1. Exit exam: departments only — no subject breakdown.
   When student picks a department, they go straight to year → questions.
   stream = dept_key in questions table (same as before).

2. Entrance exam: correct Ethiopian Grade 12 subjects including Aptitude.
   Natural: Math, Physics, Chemistry, Biology, English, Aptitude
   Social:  History, Geography, Economics, Civics, English, Aptitude

3. Remedial: correct Ethiopian remedial subjects.
   Natural: Math, English, Physics, Biology, Chemistry
   Social:  English, History, Geography, Economics, Civics

4. COC: full Ethiopian TVET COC department list.
5. Driving: standard Ethiopian driving licence subjects.
6. All new departments added per Ethiopian university standard.
"""
import aiosqlite
import os
from config import DATABASE_PATH
from app.utils.logger import logger


async def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id          INTEGER UNIQUE NOT NULL,
                username             TEXT,
                full_name            TEXT,
                exam_type            TEXT,
                stream               TEXT,
                department           TEXT,
                is_subscribed        INTEGER DEFAULT 0,
                subscribed_exam_type TEXT,
                subscribed_stream    TEXT,
                subscribed_dept      TEXT,
                subscription_expiry  TEXT,
                free_access_expiry   TEXT,
                is_admin             INTEGER DEFAULT 0,
                referral_code        TEXT UNIQUE,
                referred_by          TEXT,
                referral_count       INTEGER DEFAULT 0,
                streak_days          INTEGER DEFAULT 0,
                last_exam_date       TEXT,
                created_at           TEXT DEFAULT (datetime('now')),
                last_active          TEXT DEFAULT (datetime('now'))
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT,
                role        TEXT DEFAULT 'sub',
                added_by    INTEGER,
                created_at  TEXT DEFAULT (datetime('now'))
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS free_subject_usage (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                subject     TEXT NOT NULL,
                used_count  INTEGER DEFAULT 0,
                UNIQUE(telegram_id, subject)
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                exam_type   TEXT,
                stream      TEXT,
                subject     TEXT,
                year        INTEGER,
                score       INTEGER DEFAULT 0,
                total       INTEGER DEFAULT 0,
                completed   INTEGER DEFAULT 0,
                started_at  TEXT DEFAULT (datetime('now')),
                finished_at TEXT
            )""")

        # questions.stream stores:
        #   entrance/remedial → "natural" | "social"
        #   exit/coc          → dept_key  e.g. "computer_science"
        #   driving           → "general"
        # questions.subject stores the subject_key (same as subjects.subject_key)
        # For EXIT exam, subject = dept_key (no sub-subjects)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type      TEXT NOT NULL,
                stream         TEXT NOT NULL DEFAULT '',
                subject        TEXT NOT NULL,
                year           INTEGER,
                question_text  TEXT NOT NULL,
                option_a       TEXT NOT NULL,
                option_b       TEXT NOT NULL,
                option_c       TEXT NOT NULL,
                option_d       TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation    TEXT,
                reference      TEXT
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type    TEXT NOT NULL,
                stream       TEXT,
                subject_key  TEXT NOT NULL UNIQUE,
                subject_name TEXT NOT NULL,
                emoji        TEXT DEFAULT '📘'
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type TEXT NOT NULL DEFAULT 'exit',
                dept_key  TEXT NOT NULL UNIQUE,
                dept_name TEXT NOT NULL,
                emoji     TEXT DEFAULT '🏛️'
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id     INTEGER NOT NULL,
                full_name       TEXT,
                amount          REAL DEFAULT 50,
                bank            TEXT,
                receipt_file_id TEXT,
                status          TEXT DEFAULT 'pending',
                exam_type       TEXT,
                stream          TEXT,
                dept            TEXT,
                reviewed_by     INTEGER,
                created_at      TEXT DEFAULT (datetime('now'))
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_codes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                code          TEXT UNIQUE NOT NULL,
                duration_days INTEGER NOT NULL,
                max_uses      INTEGER DEFAULT 1,
                used_count    INTEGER DEFAULT 0,
                created_by    INTEGER,
                created_at    TEXT DEFAULT (datetime('now'))
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_uses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT NOT NULL,
                telegram_id INTEGER NOT NULL,
                used_at     TEXT DEFAULT (datetime('now'))
            )""")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name      TEXT UNIQUE NOT NULL,
                account_number TEXT NOT NULL,
                account_name   TEXT NOT NULL,
                is_active      INTEGER DEFAULT 1
            )""")

        await db.commit()
        await _run_migrations(db)
        await _seed_defaults(db)
        logger.info("✅ Database initialized.")


async def _run_migrations(db):
    """Safe schema migrations for existing databases."""
    migrations = [
        ("ALTER TABLE questions ADD COLUMN stream TEXT NOT NULL DEFAULT ''",),
        ("ALTER TABLE exam_sessions ADD COLUMN year INTEGER",),
        ("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0",),
        ("ALTER TABLE users ADD COLUMN subscribed_exam_type TEXT",),
        ("ALTER TABLE users ADD COLUMN subscribed_stream TEXT",),
        ("ALTER TABLE users ADD COLUMN subscribed_dept TEXT",),
        ("ALTER TABLE users ADD COLUMN free_access_expiry TEXT",),
        ("ALTER TABLE users ADD COLUMN referral_code TEXT",),
        ("ALTER TABLE users ADD COLUMN referred_by TEXT",),
        ("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0",),
        ("ALTER TABLE users ADD COLUMN streak_days INTEGER DEFAULT 0",),
        ("ALTER TABLE users ADD COLUMN last_exam_date TEXT",),
    ]
    for (sql,) in migrations:
        try:
            await db.execute(sql)
            await db.commit()
        except Exception:
            pass

    # Ensure free_subject_usage table exists on databases created before it was added
    await db.execute("""
        CREATE TABLE IF NOT EXISTS free_subject_usage (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            subject     TEXT NOT NULL,
            used_count  INTEGER DEFAULT 0,
            UNIQUE(telegram_id, subject)
        )""")
    await db.commit()

    # Fix driving questions with empty stream
    await db.execute("""
        UPDATE questions SET stream='general'
        WHERE exam_type='driving' AND (stream='' OR stream IS NULL)""")
    await db.commit()


async def _seed_defaults(db):
    # ── SUBJECTS ──────────────────────────────────────────────────────────────
    cur = await db.execute("SELECT COUNT(*) FROM subjects")
    if (await cur.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO subjects "
            "(exam_type,stream,subject_key,subject_name,emoji) VALUES (?,?,?,?,?)",
            [
                # ── ENTRANCE — Natural Science (Grade 12) ─────────────────────
                # Ethiopian university entrance exam subjects for natural stream
                ("entrance","natural","ent_math",       "Mathematics",        "🧮"),
                ("entrance","natural","ent_physics",     "Physics",            "⚡"),
                ("entrance","natural","ent_chemistry",   "Chemistry",          "⚗️"),
                ("entrance","natural","ent_biology",     "Biology",            "🔬"),
                ("entrance","natural","ent_english",     "English",            "🌍"),
                ("entrance","natural","ent_aptitude",    "Aptitude",           "🧠"),

                # ── ENTRANCE — Social Science (Grade 12) ──────────────────────
                ("entrance","social","ent_soc_english",  "English",            "🌍"),
                ("entrance","social","ent_soc_aptitude", "Aptitude",           "🧠"),
                ("entrance","social","ent_history",      "History",            "📜"),
                ("entrance","social","ent_geography",    "Geography",          "🗺️"),
                ("entrance","social","ent_economics",    "Economics",          "💰"),
                ("entrance","social","ent_civics",       "Civics & Ethics",    "⚖️"),

                # ── REMEDIAL — Natural Science ────────────────────────────────
                ("remedial","natural","rem_math",        "Mathematics",        "🧮"),
                ("remedial","natural","rem_english",     "English",            "🌍"),
                ("remedial","natural","rem_physics",     "Physics",            "⚡"),
                ("remedial","natural","rem_chemistry",   "Chemistry",          "⚗️"),
                ("remedial","natural","rem_biology",     "Biology",            "🔬"),

                # ── REMEDIAL — Social Science ─────────────────────────────────
                ("remedial","social","rem_soc_english",  "English",            "🌍"),
                ("remedial","social","rem_history",      "History",            "📜"),
                ("remedial","social","rem_geography",    "Geography",          "🗺️"),
                ("remedial","social","rem_economics",    "Economics",          "💰"),
                ("remedial","social","rem_civics",       "Civics & Ethics",    "⚖️"),

                # ── DRIVING LICENCE ───────────────────────────────────────────
                ("driving","general","drv_traffic_law",  "Traffic Law",        "🚦"),
                ("driving","general","drv_road_signs",   "Road Signs",         "🛑"),
                ("driving","general","drv_first_aid",    "First Aid",          "🏥"),
                ("driving","general","drv_vehicle_mech", "Vehicle Mechanics",  "🔧"),
                ("driving","general","drv_driving_skill","Driving Skills",     "🚗"),

                # ── EXIT EXAM — subject_key = dept_key (no sub-subjects) ──────
                # Each department IS its own subject. Upload questions with
                # subject = dept_key, stream = dept_key.
                ("exit","computer_science",  "exit_cs",         "Computer Science",        "💻"),
                ("exit","accounting",        "exit_acc",        "Accounting & Finance",    "📊"),
                ("exit","law",               "exit_law",        "Law",                     "⚖️"),
                ("exit","medicine",          "exit_med",        "Medicine",                "🏥"),
                ("exit","engineering",       "exit_eng",        "Engineering",             "⚙️"),
                ("exit","business",          "exit_bus",        "Business Management",     "💼"),
                ("exit","agriculture",       "exit_agr",        "Agriculture",             "🌾"),
                ("exit","education",         "exit_edu",        "Education",               "📖"),
                ("exit","nursing",           "exit_nur",        "Nursing",                 "🩺"),
                ("exit","pharmacy",          "exit_pha",        "Pharmacy",                "💊"),
                ("exit","public_health",     "exit_ph",         "Public Health",           "🏨"),
                ("exit","economics",         "exit_eco",        "Economics",               "💰"),
                ("exit","management",        "exit_mgt",        "Management",              "📋"),
                ("exit","information_tech",  "exit_it",         "Information Technology",  "🖥️"),
                ("exit","civil_engineering", "exit_civil",      "Civil Engineering",       "🏗️"),
                ("exit","electrical_eng",    "exit_elec",       "Electrical Engineering",  "⚡"),
                ("exit","mechanical_eng",    "exit_mech_eng",   "Mechanical Engineering",  "⚙️"),
                ("exit","architecture",      "exit_arch",       "Architecture",            "🏛️"),
                ("exit","psychology",        "exit_psych",      "Psychology",              "🧠"),
                ("exit","social_work",       "exit_sw",         "Social Work",             "🤝"),
                ("exit","journalism",        "exit_jour",       "Journalism & Comm.",      "📰"),
                ("exit","statistics",        "exit_stat",       "Statistics",              "📈"),
                ("exit","mathematics",       "exit_maths",      "Mathematics",             "🧮"),
                ("exit","physics_dept",      "exit_phys",       "Physics",                 "⚡"),
                ("exit","chemistry_dept",    "exit_chem",       "Chemistry",               "⚗️"),
                ("exit","biology_dept",      "exit_bio",        "Biology",                 "🔬"),
                ("exit","veterinary",        "exit_vet",        "Veterinary Medicine",     "🐄"),
                ("exit","natural_resource",  "exit_nr",         "Natural Resource Mgmt",   "🌿"),
                ("exit","urban_planning",    "exit_urb",        "Urban Planning",          "🏙️"),
                ("exit","sport_science",     "exit_sport",      "Sport Science",           "🏃"),

                # ── COC — subject_key = dept_key (no sub-subjects) ────────────
                ("coc","coc_electrical",     "coc_elec",        "Electrical Installation", "⚡"),
                ("coc","coc_construction",   "coc_constr",      "Construction",            "🏗️"),
                ("coc","coc_mechanical",     "coc_mech",        "Mechanical",              "⚙️"),
                ("coc","coc_it",             "coc_it",          "IT & Computer",           "💻"),
                ("coc","coc_automotive",     "coc_auto",        "Automotive",              "🚗"),
                ("coc","coc_accounting",     "coc_acc",         "Accounting",              "📊"),
                ("coc","coc_management",     "coc_mgmt",        "Management",              "💼"),
                ("coc","coc_hotel",          "coc_hotel",       "Hotel Management",        "🏨"),
                ("coc","coc_marketing",      "coc_mkt",         "Marketing",               "📣"),
                ("coc","coc_welding",        "coc_weld",        "Welding",                 "🔥"),
                ("coc","coc_garment",        "coc_garm",        "Garment Manufacturing",   "🧵"),
                ("coc","coc_wood",           "coc_wood",        "Woodwork & Furniture",    "🪵"),
                ("coc","coc_health",         "coc_health",      "Health Extension",        "🏥"),
                ("coc","coc_agriculture",    "coc_agr",         "Agriculture",             "🌾"),
                ("coc","coc_plumbing",       "coc_plumb",       "Plumbing",                "🔧"),
                ("coc","coc_electronics",    "coc_elecs",       "Electronics",             "📡"),
            ])

    # ── DEPARTMENTS ───────────────────────────────────────────────────────────
    cur2 = await db.execute("SELECT COUNT(*) FROM departments")
    if (await cur2.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO departments "
            "(exam_type,dept_key,dept_name,emoji) VALUES (?,?,?,?)",
            [
                # Exit exam — Ethiopian universities (MoE standard)
                ("exit","computer_science",  "Computer Science",        "💻"),
                ("exit","accounting",        "Accounting & Finance",    "📊"),
                ("exit","law",               "Law",                     "⚖️"),
                ("exit","medicine",          "Medicine",                "🏥"),
                ("exit","engineering",       "Engineering (General)",   "⚙️"),
                ("exit","civil_engineering", "Civil Engineering",       "🏗️"),
                ("exit","electrical_eng",    "Electrical Engineering",  "⚡"),
                ("exit","mechanical_eng",    "Mechanical Engineering",  "⚙️"),
                ("exit","architecture",      "Architecture",            "🏛️"),
                ("exit","business",          "Business Management",     "💼"),
                ("exit","management",        "Management",              "📋"),
                ("exit","economics",         "Economics",               "💰"),
                ("exit","agriculture",       "Agriculture",             "🌾"),
                ("exit","veterinary",        "Veterinary Medicine",     "🐄"),
                ("exit","natural_resource",  "Natural Resource Mgmt",   "🌿"),
                ("exit","education",         "Education",               "📖"),
                ("exit","nursing",           "Nursing",                 "🩺"),
                ("exit","pharmacy",          "Pharmacy",                "💊"),
                ("exit","public_health",     "Public Health",           "🏨"),
                ("exit","information_tech",  "Information Technology",  "🖥️"),
                ("exit","statistics",        "Statistics",              "📈"),
                ("exit","mathematics",       "Mathematics",             "🧮"),
                ("exit","physics_dept",      "Physics",                 "⚡"),
                ("exit","chemistry_dept",    "Chemistry",               "⚗️"),
                ("exit","biology_dept",      "Biology",                 "🔬"),
                ("exit","psychology",        "Psychology",              "🧠"),
                ("exit","social_work",       "Social Work",             "🤝"),
                ("exit","journalism",        "Journalism & Comm.",      "📰"),
                ("exit","urban_planning",    "Urban Planning",          "🏙️"),
                ("exit","sport_science",     "Sport Science",           "🏃"),
                # COC departments
                ("coc","coc_electrical",     "Electrical Installation", "⚡"),
                ("coc","coc_construction",   "Construction",            "🏗️"),
                ("coc","coc_mechanical",     "Mechanical",              "⚙️"),
                ("coc","coc_it",             "IT & Computer",           "💻"),
                ("coc","coc_automotive",     "Automotive",              "🚗"),
                ("coc","coc_accounting",     "Accounting",              "📊"),
                ("coc","coc_management",     "Management",              "💼"),
                ("coc","coc_hotel",          "Hotel Management",        "🏨"),
                ("coc","coc_marketing",      "Marketing",               "📣"),
                ("coc","coc_welding",        "Welding",                 "🔥"),
                ("coc","coc_garment",        "Garment Manufacturing",   "🧵"),
                ("coc","coc_wood",           "Woodwork & Furniture",    "🪵"),
                ("coc","coc_health",         "Health Extension",        "🏥"),
                ("coc","coc_agriculture",    "Agriculture",             "🌾"),
                ("coc","coc_plumbing",       "Plumbing",                "🔧"),
                ("coc","coc_electronics",    "Electronics",             "📡"),
                # Remedial
                ("remedial","remedial_natural","Natural Science",       "🔬"),
                ("remedial","remedial_social", "Social Science",        "📚"),
                # Driving
                ("driving","driving_general",  "General",               "🚗"),
            ])

    # ── BANK ACCOUNTS ─────────────────────────────────────────────────────────
    cur3 = await db.execute("SELECT COUNT(*) FROM bank_accounts")
    if (await cur3.fetchone())[0] == 0:
        await db.executemany(
            "INSERT OR IGNORE INTO bank_accounts "
            "(bank_name,account_number,account_name) VALUES (?,?,?)",
            [
                ("CBE",      "1000482304102","Yohanes Alemu Mengesha"),
                ("Awash",    "1000482304102","Yohanes Alemu Mengesha"),
                ("Dashen",   "1000482304102","Yohanes Alemu Mengesha"),
                ("Telebirr", "0912345678",   "Yohanes Alemu Mengesha"),
            ])

    await db.commit()


def get_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    return aiosqlite.connect(DATABASE_PATH)