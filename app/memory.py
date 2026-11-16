"""长期记忆存储层（SQLite 版）。

存两类东西：
- profile：用户画像（JSON），如 {"name": "王阿姨", "health": "高血压"}
- summary：对话摘要，把早期对话压缩成一段文字
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "memory.db"

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                session_id TEXT PRIMARY KEY,
                profile    TEXT,
                summary    TEXT
            )
        """)
        _conn.commit()
    return _conn

def get(session_id: str) -> tuple[dict, str]:
    """返回 (画像 dict, 摘要 str)；没有记录时返回 ({}, "")。"""
    row = _get_conn().execute(
        "SELECT profile, summary FROM memories WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if row is None:
        return {}, ""
    profile = json.loads(row["profile"]) if row["profile"] else {}
    return profile, row["summary"] or ""


def save_profile(session_id: str, profile: dict) -> None:
    _get_conn().execute(
        """INSERT INTO memories (session_id, profile) VALUES (?, ?)
           ON CONFLICT(session_id) DO UPDATE SET profile = excluded.profile""",
        (session_id, json.dumps(profile, ensure_ascii=False)),
    )
    _get_conn().commit()


def save_summary(session_id: str, summary: str) -> None:
    _get_conn().execute(
        """INSERT INTO memories (session_id, summary) VALUES (?, ?)
           ON CONFLICT(session_id) DO UPDATE SET summary = excluded.summary""",
        (session_id, summary),
    )
    _get_conn().commit()


def clear(session_id: str) -> None:
    _get_conn().execute("DELETE FROM memories WHERE session_id = ?", (session_id,))
    _get_conn().commit()