"""Searchable document archive — every OCR result is stored in SQLite so users
can search across all digitized Kannada documents (corpus-level search)."""
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "archive.db"
_lock = threading.Lock()
_initialized = False


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    text TEXT NOT NULL,
                    transliteration TEXT,
                    word_count INTEGER DEFAULT 0,
                    char_count INTEGER DEFAULT 0,
                    engine_used TEXT,
                    model_used TEXT,
                    handwriting INTEGER DEFAULT 0,
                    kannada_share REAL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC)"
            )
            conn.commit()
        finally:
            conn.close()


def _ensure_db() -> None:
    """Lazy init: the DB file is only created when a database function is
    actually called (routes stay 404 and OCR never saves when the archive
    feature is disabled, so no file is created at all)."""
    global _initialized
    if not _initialized:
        init_db()
        _initialized = True


def save_document(
    filename: str,
    text: str,
    word_count: int = 0,
    char_count: int = 0,
    engine_used: Optional[str] = None,
    model_used: Optional[str] = None,
    handwriting: bool = False,
    kannada_share: float = 0.0,
) -> Dict[str, Any]:
    """Persist one OCR result. Returns the saved row (with id)."""
    _ensure_db()
    created_at = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO documents
                    (filename, text, word_count, char_count, engine_used, model_used,
                     handwriting, kannada_share, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    filename or "untitled",
                    text,
                    word_count,
                    char_count,
                    engine_used,
                    model_used,
                    1 if handwriting else 0,
                    kannada_share,
                    created_at,
                ),
            )
            conn.commit()
            doc_id = cur.lastrowid
        finally:
            conn.close()
    return get_document(doc_id)


def get_document(doc_id: int) -> Optional[Dict[str, Any]]:
    _ensure_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def search_documents(query: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List recent documents, or full-text LIKE search when query is given.
    Returns rows WITHOUT the full text body (preview only) for light payloads."""
    _ensure_db()
    conn = _connect()
    try:
        if query and query.strip():
            like = f"%{query.strip()}%"
            rows = conn.execute(
                """
                SELECT id, filename, word_count, char_count, engine_used, handwriting,
                       kannada_share, created_at,
                       substr(text, 1, 200) AS preview
                FROM documents
                WHERE text LIKE ? OR filename LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, filename, word_count, char_count, engine_used, handwriting,
                       kannada_share, created_at,
                       substr(text, 1, 200) AS preview
                FROM documents
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_document(doc_id: int) -> bool:
    _ensure_db()
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def archive_stats() -> Dict[str, Any]:
    _ensure_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS doc_count, COALESCE(SUM(char_count), 0) AS total_chars FROM documents"
        ).fetchone()
        return {"doc_count": row["doc_count"], "total_chars": row["total_chars"]}
    finally:
        conn.close()
