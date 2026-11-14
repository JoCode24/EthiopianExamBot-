"""
app/database/db.py  —  Database initialisation & migration
Supports:
- Fresh installs (creates all tables)
- Existing DBs (safe ALTER TABLE for new columns — never crashes if already exists)

New columns added in this version:
  users.streak_days      INTEGER DEFAULT 0
  users.last_exam_date   TEXT
"""
import aiosqlite
from config import DATABASE_PATH
from app.utils.logger import logger


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # ── Core user table ───────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id         INTEGER UNIQUE NOT NULL,
                username            TEXT,
                full_name           TEXT,
                is_subscribed       INTEGER DEFAULT 0,
                subscription_expiry TEXT,
                subscribed_exam_type TEXT,
                subscribed_stream   TEXT,
                subscribed_dept     TEXT,
                referral_code       TEXT UNIQUE,
                referred_by         TEXT,
                referral_count      INTEGER DEFAULT 0,
                total_exams         INTEGER DEFAULT 0,
                best_score          INTEGER DEFAULT 0,
                streak_days         INTEGER DEFAULT 0,
                last_exam_date      TEXT,
                created_at          TEXT DEFAULT (datetime('now'))
            )
        """)

        # ── Safe migrations: add columns that may be missing on existing DBs ──
        _safe_migrations = [
            ("users", "streak_days",    "INTEGER DEFAULT 0"),
            ("users", "last_exam_date", "TEXT"),
            # Keep subscription columns for older schemas
            ("users", "is_subscribed",        "INTEGER DEFAULT 0"),
            ("users", "subscription_expiry",  "TEXT"),
            ("users", "subscribed_exam_type", "TEXT"),
            ("users", "subscribed_stream",    "TEXT"),
            ("users", "subscribed_dept",      "TEXT"),
            ("users", "referral_code",        "TEXT"),
            ("users", "referred_by",          "TEXT"),
            ("users", "referral_count",       "INTEGER DEFAULT 0"),
            ("users", "total_exams",          "INTEGER DEFAULT 0"),
            ("users", "best_score",           "INTEGER DEFAULT 0"),
        ]
        for table, col, col_def in _safe_migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            except Exception:
                pass  # Column already exists — not an error

        # ── Questions ─────────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_type   TEXT NOT NULL,
                stream      TEXT,
                dept        TEXT,
                subject     TEXT,
                year        INTEGER,
                question    TEXT NOT NULL,
                option_a    TEXT NOT NULL,
                option_b    TEXT NOT NULL,
                option_c    TEXT NOT NULL,
                option_d    TEXT NOT NULL,
                answer      TEXT NOT NULL,
                explanation TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
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
                emoji     TEXT DEFAULT '🏛️'
            )
        """)

        # ── Exam sessions ─────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id   INTEGER NOT NULL,
                exam_type     TEXT NOT NULL,
                stream        TEXT,
                dept          TEXT,
                subject       TEXT,
                year          INTEGER,
                score         INTEGER DEFAULT 0,
                total         INTEGER DEFAULT 0,
                pct           REAL    DEFAULT 0,
                completed     INTEGER DEFAULT 0,
                started_at    TEXT DEFAULT (datetime('now')),
                finished_at   TEXT
            )
        """)
        # Safe migrations for exam_sessions
        for col, col_def in [("pct", "REAL DEFAULT 0"), ("finished_at", "TEXT")]:
            try:
                await db.execute(f"ALTER TABLE exam_sessions ADD COLUMN {col} {col_def}")
            except Exception:
                pass

        # ── Payment receipts ──────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_receipts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                exam_type   TEXT,
                stream      TEXT,
                dept        TEXT,
                file_id     TEXT,
                status      TEXT DEFAULT 'pending',
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

        # ── Bank accounts ─────────────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name    TEXT NOT NULL,
                account_no   TEXT NOT NULL,
                account_name TEXT,
                is_active    INTEGER DEFAULT 1
            )
        """)

        # ── Giveaway / promo codes ────────────────────────────────────────
        await db.execute("""
            CREATE TABLE IF NOT EXISTS giveaway_codes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                code         TEXT UNIQUE NOT NULL,
                exam_type    TEXT,
                stream       TEXT,
                dept         TEXT,
                duration_days INTEGER DEFAULT 30,
                max_uses     INTEGER DEFAULT 1,
                used_count   INTEGER DEFAULT 0,
                created_by   INTEGER,
                created_at   TEXT DEFAULT (datetime('now')),
                expires_at   TEXT
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

        # ── Free subject usage (for free-tier limits per subject) ─────────
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

        # ── Useful indexes ────────────────────────────────────────────────
        await db.execute("CREATE INDEX IF NOT EXISTS idx_questions_type   ON questions(exam_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_tid      ON exam_sessions(telegram_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_receipts_status   ON payment_receipts(status)")

        await db.commit()
        logger.info("Database initialised / migrated successfully.")
