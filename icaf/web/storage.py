from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class RunStore:
    """Small SQLite persistence layer for local ICAF web runs."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    clause TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    dut_host TEXT NOT NULL,
                    ssh_user TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    error_message TEXT,
                    artifact_dir TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    label TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS evidence_run_id_idx ON evidence(run_id);
                """
            )

    def create_run(self, run: dict[str, str]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (id, clause, profile, dut_host, ssh_user, status,
                                  created_at, artifact_dir)
                VALUES (:id, :clause, :profile, :dut_host, :ssh_user, :status,
                        :created_at, :artifact_dir)
                """,
                run,
            )

    def update_run(self, run_id: str, **values: Optional[str]) -> None:
        if not values:
            return
        assignments = ", ".join(f"{column} = ?" for column in values)
        with self._connect() as connection:
            connection.execute(
                f"UPDATE runs SET {assignments} WHERE id = ?",
                [*values.values(), run_id],
            )

    def add_evidence(
        self,
        run_id: str,
        kind: str,
        label: str,
        relative_path: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evidence (run_id, kind, label, relative_path, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    kind,
                    label,
                    relative_path,
                    utc_now(),
                    json.dumps(metadata or {}),
                ),
            )

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM runs ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self._connect() as connection:
            run = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if run is None:
                return None
            evidences = connection.execute(
                "SELECT * FROM evidence WHERE run_id = ? ORDER BY id", (run_id,)
            ).fetchall()
        data = dict(run)
        data["evidence"] = [
            {**dict(item), "metadata": json.loads(item["metadata_json"])}
            for item in evidences
        ]
        return data


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
