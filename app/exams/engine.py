"""
app/exams/engine.py
────────────────────
All queries filter by BOTH exam_type AND stream.
seed_sample_questions() stub kept for main.py compatibility.
"""
import aiosqlite, os
from datetime import datetime, timedelta
from config import DATABASE_PATH
from app.utils.logger import logger


async def seed_sample_questions():
    """Stub — keeps main.py import working. No sample data inserted."""
    pass


async def get_questions(exam_type, stream, subject, year=None, limit=None):
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if year:
            sql    = "SELECT * FROM questions WHERE exam_type=? AND stream=? AND subject=? AND year=? ORDER BY RANDOM()"
            params = (exam_type, stream, subject, year)
        else:
            sql    = "SELECT * FROM questions WHERE exam_type=? AND stream=? AND subject=? ORDER BY RANDOM()"
            params = (exam_type, stream, subject)
        if limit:
            sql += f" LIMIT {int(limit)}"
        cur = await db.execute(sql, params)
        return [dict(r) for r in await cur.fetchall()]


async def get_all_questions_for_subject(exam_type, stream, subject, year=None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if year:
            cur = await db.execute(
                "SELECT * FROM questions WHERE exam_type=? AND stream=? AND subject=? AND year=? ORDER BY id",
                (exam_type, stream, subject, year))
        else:
            cur = await db.execute(
                "SELECT * FROM questions WHERE exam_type=? AND stream=? AND subject=? ORDER BY id",
                (exam_type, stream, subject))
        return [dict(r) for r in await cur.fetchall()]


async def count_questions(exam_type, stream, subject, year=None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        if year:
            cur = await db.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_type=? AND stream=? AND subject=? AND year=?",
                (exam_type, stream, subject, year))
        else:
            cur = await db.execute(
                "SELECT COUNT(*) FROM questions WHERE exam_type=? AND stream=? AND subject=?",
                (exam_type, stream, subject))
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_years_for_subject(exam_type, stream, subject):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT DISTINCT year FROM questions "
            "WHERE exam_type=? AND stream=? AND subject=? AND year IS NOT NULL ORDER BY year DESC",
            (exam_type, stream, subject))
        return [r[0] for r in await cur.fetchall()]


async def bulk_insert_questions(questions, exam_type, stream, subject):
    """Insert questions with correct exam_type+stream+subject. Returns (saved, skipped)."""
    saved = skipped = 0
    async with aiosqlite.connect(DATABASE_PATH) as db:
        for q in questions:
            if not all([q.get("question_text"), q.get("option_a"), q.get("option_b"),
                        q.get("option_c"), q.get("option_d"), q.get("correct_answer")]):
                skipped += 1
                continue
            cur = await db.execute(
                "SELECT id FROM questions WHERE exam_type=? AND stream=? AND subject=? AND question_text=?",
                (exam_type, stream, subject, q["question_text"]))
            if await cur.fetchone():
                skipped += 1
                continue
            await db.execute(
                "INSERT INTO questions (exam_type,stream,subject,year,question_text,"
                "option_a,option_b,option_c,option_d,correct_answer,explanation,reference) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (exam_type, stream, subject, q.get("year"),
                 q["question_text"], q["option_a"], q["option_b"],
                 q["option_c"], q["option_d"], q["correct_answer"].upper(),
                 q.get("explanation") or None, q.get("reference") or None))
            saved += 1
        await db.commit()
    logger.info(f"bulk_insert: exam={exam_type} stream={stream} subject={subject} saved={saved} skipped={skipped}")
    return saved, skipped


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


async def update_streak(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT streak_days,last_exam_date FROM users WHERE telegram_id=?", (telegram_id,))
        row = await cur.fetchone()
        if not row:
            return 1
        streak, last_date = row[0] or 0, row[1] or ""
        today     = datetime.utcnow().date().isoformat()
        yesterday = (datetime.utcnow().date() - timedelta(days=1)).isoformat()
        if last_date == today:
            return streak
        streak = streak + 1 if last_date == yesterday else 1
        await db.execute("UPDATE users SET streak_days=?,last_exam_date=? WHERE telegram_id=?",
                         (streak, today, telegram_id))
        await db.commit()
        return streak


async def get_leaderboard(limit=10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "SELECT u.full_name, COUNT(e.id), AVG(CAST(e.score AS FLOAT)/NULLIF(e.total,0)*100) "
            "FROM users u JOIN exam_sessions e ON u.telegram_id=e.telegram_id "
            "WHERE e.completed=1 AND e.total>0 GROUP BY u.telegram_id ORDER BY 3 DESC LIMIT ?",
            (limit,))
        return await cur.fetchall()