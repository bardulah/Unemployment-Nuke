"""SQLite persistence layer for careerforge.

Everything the app knows lives in one local SQLite file: the master profile,
target roles, generated analyses (gap / 14-day project / tailored CV),
applications with status, and follow-up reminders.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

APPLICATION_STATUSES = [
    "saved",
    "applied",
    "screening",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "on_hold",
]

RESULT_KINDS = ["gap", "project", "tailor"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    jd_text TEXT NOT NULL DEFAULT '',
    company_context TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER NOT NULL REFERENCES targets(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    mode TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER REFERENCES targets(id) ON DELETE SET NULL,
    role_title TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'saved',
    contact TEXT NOT NULL DEFAULT '',
    applied_at TEXT NOT NULL DEFAULT '',
    next_followup TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    due_date TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_results_target ON results(target_id, kind, id);
CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(done, due_date);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class Tracker:
    """Thin wrapper around a sqlite3 connection for the careerforge data dir."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "careerforge.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Tracker":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------ profile
    def get_profile(self) -> dict:
        row = self.conn.execute("SELECT data FROM profile WHERE id = 1").fetchone()
        return json.loads(row["data"]) if row else {}

    def set_profile(self, profile: dict) -> None:
        self.conn.execute(
            "INSERT INTO profile (id, data, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
            (json.dumps(profile, ensure_ascii=False, indent=2), utcnow()),
        )
        self.conn.commit()

    # ------------------------------------------------------------------ targets
    def add_target(
        self,
        title: str,
        company: str = "",
        url: str = "",
        location: str = "",
        jd_text: str = "",
        company_context: str = "",
        notes: str = "",
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO targets (title, company, url, location, jd_text, company_context, notes, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, company, url, location, jd_text, company_context, notes, utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_target(self, target_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM targets WHERE id = ?", (target_id,)).fetchone()
        return dict(row) if row else None

    def list_targets(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM targets ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def delete_target(self, target_id: int) -> None:
        self.conn.execute("DELETE FROM targets WHERE id = ?", (target_id,))
        self.conn.commit()

    # ------------------------------------------------------------------ results
    def save_result(self, target_id: int, kind: str, payload: dict, mode: str, model: str = "") -> int:
        if kind not in RESULT_KINDS:
            raise ValueError(f"unknown result kind: {kind}")
        cur = self.conn.execute(
            "INSERT INTO results (target_id, kind, mode, model, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (target_id, kind, mode, model, json.dumps(payload, ensure_ascii=False), utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_latest_result(self, target_id: int, kind: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM results WHERE target_id = ? AND kind = ? ORDER BY id DESC LIMIT 1",
            (target_id, kind),
        ).fetchone()
        if not row:
            return None
        return {"id": row["id"], "kind": row["kind"], "mode": row["mode"], "model": row["model"],
                "created_at": row["created_at"], "payload": json.loads(row["payload"])}

    def list_results(self, target_id: int | None = None, kind: str | None = None) -> list[dict]:
        sql = "SELECT * FROM results"
        clauses, params = [], []
        if target_id is not None:
            clauses.append("target_id = ?")
            params.append(target_id)
        if kind is not None:
            clauses.append("kind = ?")
            params.append(kind)
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # -------------------------------------------------------------- applications
    def add_application(
        self,
        status: str = "saved",
        target_id: int | None = None,
        role_title: str = "",
        company: str = "",
        contact: str = "",
        applied_at: str = "",
        next_followup: str = "",
        notes: str = "",
    ) -> int:
        if status not in APPLICATION_STATUSES:
            raise ValueError(f"status must be one of {APPLICATION_STATUSES}")
        cur = self.conn.execute(
            "INSERT INTO applications (target_id, role_title, company, status, contact, applied_at, next_followup, notes, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (target_id, role_title, company, status, contact, applied_at, next_followup, notes, utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def update_application(self, app_id: int, **fields) -> None:
        allowed = {"status", "contact", "applied_at", "next_followup", "notes", "role_title", "company", "target_id"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if "status" in updates and updates["status"] not in APPLICATION_STATUSES:
            raise ValueError(f"status must be one of {APPLICATION_STATUSES}")
        if not updates:
            return
        sql = "UPDATE applications SET " + ", ".join(f"{k} = ?" for k in updates) + " WHERE id = ?"
        self.conn.execute(sql, (*updates.values(), app_id))
        self.conn.commit()

    def get_application(self, app_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT a.*, t.title AS target_title FROM applications a LEFT JOIN targets t ON t.id = a.target_id WHERE a.id = ?",
            (app_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_applications(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT a.*, t.title AS target_title FROM applications a LEFT JOIN targets t ON t.id = a.target_id ORDER BY a.id"
        ).fetchall()
        return [dict(r) for r in rows]

    # ----------------------------------------------------------------- reminders
    def add_reminder(self, message: str, due_date: str, application_id: int | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO reminders (application_id, message, due_date, done, created_at) VALUES (?, ?, ?, 0, ?)",
            (application_id, message, due_date, utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def complete_reminder(self, reminder_id: int) -> None:
        self.conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
        self.conn.commit()

    def list_reminders(self, include_done: bool = False) -> list[dict]:
        sql = "SELECT * FROM reminders"
        if not include_done:
            sql += " WHERE done = 0"
        sql += " ORDER BY due_date, id"
        return [dict(r) for r in self.conn.execute(sql).fetchall()]

    def due_reminders(self, on_date: str | None = None) -> list[dict]:
        on_date = on_date or today()
        rows = self.conn.execute(
            "SELECT * FROM reminders WHERE done = 0 AND due_date <= ? ORDER BY due_date, id", (on_date,)
        ).fetchall()
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------- stats
    def stats(self) -> dict:
        targets = self.conn.execute("SELECT COUNT(*) c FROM targets").fetchone()["c"]
        apps = self.conn.execute("SELECT status, COUNT(*) c FROM applications GROUP BY status").fetchall()
        overdue = self.conn.execute(
            "SELECT COUNT(*) c FROM reminders WHERE done = 0 AND due_date <= ?", (today(),)
        ).fetchone()["c"]
        scores = self.conn.execute(
            "SELECT r.target_id, r.payload FROM results r JOIN (SELECT target_id, MAX(id) m FROM results WHERE kind='gap' GROUP BY target_id) latest ON latest.m = r.id"
        ).fetchall()
        match_scores = {}
        for row in scores:
            try:
                match_scores[row["target_id"]] = json.loads(row["payload"]).get("match_score")
            except (json.JSONDecodeError, AttributeError):
                pass
        return {
            "targets": targets,
            "applications_by_status": {r["status"]: r["c"] for r in apps},
            "overdue_reminders": overdue,
            "match_scores": match_scores,
        }
