"""
history.py – Persistent report storage for MarketPulse.

Provides a single ReportStore class that wraps a local SQLite database.
All public methods are thread-safe (each call opens/closes its own
connection so Streamlit's multi-threaded rerun model works correctly).

Schema
------
reports
  id            TEXT  PRIMARY KEY   (8-char run_id from RunMetadata)
  topic         TEXT  NOT NULL      (original search topic)
  title         TEXT  NOT NULL      (derived display title)
  competitors   TEXT  NOT NULL      (comma-joined competitor names)
  created_at    TEXT  NOT NULL      (ISO-8601 UTC timestamp)
  duration_sec  REAL               (run duration in seconds, may be NULL)
  total_sources INTEGER            (number of sources collected)
  briefing_json TEXT  NOT NULL      (full BriefingOutput dict serialised as JSON)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# Default DB location: user's home directory so Streamlit's file-watcher
# never sees it and won't raise "dictionary changed size during iteration".
_DEFAULT_DB_PATH = Path.home() / ".marketpulse" / "report_history.db"


class ReportStore:
    """SQLite-backed store for generated competitive intelligence reports."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = Path(db_path or _DEFAULT_DB_PATH)
        # Create parent directory if it doesn't exist yet
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(self._db_path)
        self._init_db()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row          # rows accessible by column name
        conn.execute("PRAGMA journal_mode=WAL")  # safer concurrent writes
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """Create the reports table if it does not already exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id            TEXT    PRIMARY KEY,
                    topic         TEXT    NOT NULL,
                    title         TEXT    NOT NULL,
                    competitors   TEXT    NOT NULL DEFAULT '',
                    created_at    TEXT    NOT NULL,
                    duration_sec  REAL,
                    total_sources INTEGER,
                    briefing_json TEXT    NOT NULL
                )
                """
            )
            conn.commit()

    # ── Derivation helpers ────────────────────────────────────────────────────

    @staticmethod
    def _derive_title(briefing: Dict[str, Any]) -> str:
        """
        Build a human-readable title from the briefing data.
        Preference order: topic → executive_summary first sentence → 'Untitled Report'.
        """
        meta = briefing.get("run_metadata") or {}
        topic = (meta.get("topic") or "").strip()
        if topic:
            # Capitalise nicely; truncate if very long
            return topic[:100].title() if len(topic) > 3 else topic

        summary = (briefing.get("executive_summary") or "").strip()
        if summary:
            first_sentence = summary.split(".")[0].strip()
            return (first_sentence[:100] + "…") if len(first_sentence) > 100 else first_sentence

        return "Untitled Report"

    @staticmethod
    def _derive_competitors(briefing: Dict[str, Any]) -> str:
        """
        Extract a sorted, deduplicated, comma-joined string of competitor names
        from pricing moves, product launches and market signals.
        """
        names: set[str] = set()
        for pm in briefing.get("competitor_pricing") or []:
            c = (pm.get("competitor") or "").strip()
            if c:
                names.add(c)
        for pl in briefing.get("product_launches") or []:
            c = (pl.get("competitor") or "").strip()
            if c:
                names.add(c)
        return ", ".join(sorted(names)) if names else ""

    # ── Public API ────────────────────────────────────────────────────────────

    def save(self, briefing: Dict[str, Any]) -> str:
        """
        Persist a briefing dict.  Returns the report id (run_id).
        If a report with the same id already exists it is replaced (idempotent).

        Parameters
        ----------
        briefing : dict
            A BriefingOutput serialised as a plain dict (as stored in
            st.session_state["briefing"]).

        Returns
        -------
        str  The report id stored in the database.
        """
        meta = briefing.get("run_metadata") or {}
        report_id = (meta.get("run_id") or "").strip() or _short_uuid()
        topic = (meta.get("topic") or "").strip()
        title = self._derive_title(briefing)
        competitors = self._derive_competitors(briefing)
        duration_sec = meta.get("duration_seconds")
        total_sources = meta.get("total_sources")

        # Use completed_at if available, else utcnow
        completed_at_raw = meta.get("completed_at")
        if completed_at_raw:
            try:
                if isinstance(completed_at_raw, datetime):
                    created_at = completed_at_raw.isoformat()
                else:
                    # Already a string — normalise to ISO-8601
                    created_at = str(completed_at_raw)
            except Exception:
                created_at = _utcnow_iso()
        else:
            created_at = _utcnow_iso()

        briefing_json = json.dumps(briefing, default=str)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO reports
                    (id, topic, title, competitors, created_at,
                     duration_sec, total_sources, briefing_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (report_id, topic, title, competitors, created_at,
                 duration_sec, total_sources, briefing_json),
            )
            conn.commit()

        return report_id

    def list_reports(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Return summary rows for all reports, newest first.

        Each row is a dict with keys:
            id, topic, title, competitors, created_at,
            duration_sec, total_sources
        (briefing_json is NOT included for performance.)
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, topic, title, competitors, created_at,
                       duration_sec, total_sources
                FROM   reports
                ORDER BY created_at DESC
                LIMIT  ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Full-text search on title, topic, and competitors (case-insensitive).
        Returns summary rows in the same format as list_reports().
        """
        q = f"%{query.strip()}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, topic, title, competitors, created_at,
                       duration_sec, total_sources
                FROM   reports
                WHERE  title      LIKE ? COLLATE NOCASE
                    OR topic      LIKE ? COLLATE NOCASE
                    OR competitors LIKE ? COLLATE NOCASE
                ORDER BY created_at DESC
                LIMIT  ?
                """,
                (q, q, q, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the full briefing dict for a single report.
        Returns None if the id is not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT briefing_json FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["briefing_json"])

    def delete(self, report_id: str) -> bool:
        """
        Delete a report by id.  Returns True if a row was deleted.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM reports WHERE id = ?", (report_id,)
            )
            conn.commit()
        return cursor.rowcount > 0

    def count(self) -> int:
        """Return the total number of stored reports."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()
        return row["n"] if row else 0


# ── Module-level singleton ────────────────────────────────────────────────────
# app.py imports this directly so there is exactly one store instance per
# process (Streamlit runs in a single process).
store = ReportStore()


# ── Private utilities ─────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_uuid() -> str:
    import uuid
    return str(uuid.uuid4())[:8]
