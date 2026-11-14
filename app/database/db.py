"""
app/database/db.py  —  Database initialisation & safe migration

Tables:
  users, questions, subjects, departments, exam_sessions,
  payment_receipts, admins, bank_accounts, giveaway_codes,
  giveaway_redemptions, free_subject_usage, subscriptions
"""
import aiosqlite
from config import DATABASE_PATH
from app.utils.logger import logger


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:

        # ── Users ─────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id          INTEGER UNIQUE NOT NULL,
                username             TEXT,
                full_name            TEXT,
                is_subscribed        INTEGER DEFAULT 0,
                subscription_expiry  TEXT,
                subscribed_exam_type TEXT,
                subscribed_stream    TEXT,
                subscribed_dept      TEXT,
                referral_code        TEXT UNIQUE,
                referred_by          TEXT,
                referral_count       INTEGER DEFAULT 0,
                total_exams          INTEGER DEFAULT 0,
                best_score           INTEGER DEFAULT 0,
                streak_days          INTEGER DEFAULT 0,
                last_exam_date       TEXT,
                created_at           TEXT DEFAULT (datetime('now'))
            )
        """)

        # Safe column additions for existing databases
        for col, defn in [
            ("is_subscribed",        "INTEGER DEFAULT 0"),
            ("subscription_expiry",  "TEXT"),
            ("subscribed_exam_type", "TEXT"),
            ("subscribed_stream",    "TEXT"),
            ("subscribed_dept",      "TEXT"),
            ("referral_code",        "TEXT"),
            ("referred_by",          "TEXT"),
            ("referral_count",       "INTEGER DEFAULT 0"),
            ("total_exams",          "INTEGER DEFAULT 0"),
            ("best_score",           "INTEGER DEFAULT 0"),
            ("streak_days",          "INTEGER DEFAULT 0"),
            ("last_exam_date",       "TEXT"),
        ]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # ── Questions ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type      TEXT NOT NULL,
                stream         TEXT,
                dept           TEXT,
                subject        TEXT,
                year           INTEGER,
                question_text  TEXT NOT NULL,
                option_a       TEXT NOT NULL,
                option_b       TEXT NOT NULL,
                option_c       TEXT NOT NULL,
                option_d       TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                explanation    TEXT,
                reference      TEXT,
                created_at     TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── Subjects ──────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_key  TEXT NOT NULL,
                subject_name TEXT NOT NULL,
                exam_type    TEXT NOT NULL,
                stream       TEXT,
                dept         TEXT,
                emoji        TEXT DEFAULT '📘',
                UNIQUE(subject_key, exam_type)
            )
        """)

        # ── Departments ───────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                dept_key  TEXT UNIQUE NOT NULL,
                dept_name TEXT NOT NULL,
                exam_type TEXT,
                emoji     TEXT DEFAULT '🏛️'
            )
        """)
        try:
            await db.execute("ALTER TABLE departments ADD COLUMN exam_type TEXT")
        except Exception:
            pass

        # ── Exam sessions ─────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                exam_type   TEXT NOT NULL,
                stream      TEXT,
                dept        TEXT,
                subject     TEXT,
                year        INTEGER,
                score       INTEGER DEFAULT 0,
                total       INTEGER DEFAULT 0,
                pct         REAL    DEFAULT 0,
                completed   INTEGER DEFAULT 0,
                started_at  TEXT DEFAULT (datetime('now')),
                finished_at TEXT
            )
        """)
        for col, defn in [("pct", "REAL DEFAULT 0"), ("finished_at", "TEXT")]:
            try:
                await db.execute(f"ALTER TABLE exam_sessions ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # ── Payment receipts ──────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_receipts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id  INTEGER NOT NULL,
                exam_type    TEXT,
                stream       TEXT,
                dept         TEXT,
                file_id      TEXT,
                status       TEXT DEFAULT 'pending',
                submitted_at TEXT DEFAULT (datetime('now')),
                reviewed_at  TEXT
            )
        """)

        # ── Admins ────────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                role        TEXT DEFAULT 'sub',
                added_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        # admin_users alias (some parts of code use this name)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name   TEXT,
                role        TEXT DEFAULT 'sub',
                added_by    INTEGER,
                added_at    TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── Bank accounts ─────────────────────────────────────────────────
        # Uses account_number + account_holder (subscription.py expects these names)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name      TEXT NOT NULL,
                account_number TEXT NOT NULL,
                account_holder TEXT,
                is_active      INTEGER DEFAULT 1
            )
        """)
        for col, defn in [
            ("account_number", "TEXT"),
            ("account_holder", "TEXT"),
            ("is_active",      "INTEGER DEFAULT 1"),
        ]:
            try:
                await db.execute(f"ALTER TABLE bank_accounts ADD COLUMN {col} {defn}")
            except Exception:
                pass

        # ── Giveaway codes ────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_codes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                code          TEXT UNIQUE NOT NULL,
                exam_type     TEXT,
                stream        TEXT,
                dept          TEXT,
                duration_days INTEGER DEFAULT 30,
                max_uses      INTEGER DEFAULT 1,
                used_count    INTEGER DEFAULT 0,
                created_by    INTEGER,
                created_at    TEXT DEFAULT (datetime('now')),
                expires_at    TEXT
            )
        """)

        # ── Giveaway redemptions ──────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_redemptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT NOT NULL,
                telegram_id INTEGER NOT NULL,
                redeemed_at TEXT DEFAULT (datetime('now')),
                UNIQUE(code, telegram_id)
            )
        """)

        # ── Free subject usage ────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS free_subject_usage (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                exam_type   TEXT NOT NULL,
                subject     TEXT NOT NULL,
                used_count  INTEGER DEFAULT 0,
                UNIQUE(telegram_id, exam_type, subject)
            )
        """)

        # ── Multi-subscriptions ───────────────────────────────────────────
        # One row per exam_type/stream/dept — users can hold multiple at once
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id   INTEGER NOT NULL,
                exam_type     TEXT NOT NULL,
                stream        TEXT,
                dept          TEXT,
                subscribed_at TEXT DEFAULT (datetime('now')),
                expiry_at     TEXT,
                is_active     INTEGER DEFAULT 1
            )
        """)

        # ── Indexes ───────────────────────────────────────────────────────
        await db.execute("CREATE INDEX IF NOT EXISTS idx_q_type    ON questions(exam_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_q_subject ON questions(subject)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ses_tid   ON exam_sessions(telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_rcpt_stat ON payment_receipts(status)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sub_tid   ON subscriptions(telegram_id)")

        await db.commit()
        logger.info("Database initialised / migrated successfully.")
