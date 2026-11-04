"""Hash-chained SQLite evidence for a standalone synthetic demonstration.

Not tamper-proof: without OS-separated credentials and an external checkpoint,
an attacker with write access could rewrite the database and its hashes.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import canonical_json

GENESIS = "0" * 64


class AuditIntegrityError(RuntimeError):
    pass


class AuditLedger:
    def __init__(self, path: Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                time_utc TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL)""")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5, isolation_level=None)

    @staticmethod
    def _event_hash(seq: int, time_utc: str, kind: str, payload: str, prev_hash: str) -> str:
        raw = canonical_json({"seq": seq, "time_utc": time_utc, "kind": kind, "payload": payload, "prev_hash": prev_hash})
        return hashlib.sha256(raw).hexdigest()

    def verify(self) -> None:
        with self._connect() as db:
            rows = db.execute("SELECT seq, time_utc, kind, payload, prev_hash, event_hash FROM events ORDER BY seq").fetchall()
        prev = GENESIS
        for count, (seq, at, kind, payload, prev_hash, event_hash) in enumerate(rows, start=1):
            if seq != count or prev_hash != prev or self._event_hash(seq, at, kind, payload, prev_hash) != event_hash:
                raise AuditIntegrityError(f"Event hash chain invalid at sequence {seq}")
            prev = event_hash

    def append(self, kind: str, payload: dict[str, object]) -> str:
        # Synchronous durable record before dispatch. Failures propagate to broker.
        data = canonical_json(payload).decode("utf-8")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            last = db.execute("SELECT seq, event_hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            seq = (last[0] + 1) if last else 1
            prev_hash = last[1] if last else GENESIS
            at = datetime.now(timezone.utc).isoformat()
            event_hash = self._event_hash(seq, at, kind, data, prev_hash)
            db.execute("INSERT INTO events (seq, time_utc, kind, payload, prev_hash, event_hash) VALUES (?,?,?,?,?,?)", (seq, at, kind, data, prev_hash, event_hash))
            db.commit()
        return event_hash

    def read_verified_events(self) -> list[dict[str, object]]:
        """Read a consistent verified snapshot; never return unverified evidence."""
        with self._connect() as db:
            db.execute("BEGIN")
            rows = db.execute(
                "SELECT seq, time_utc, kind, payload, prev_hash, event_hash "
                "FROM events ORDER BY seq"
            ).fetchall()
            previous = GENESIS
            for count, (seq, at, kind, payload, prev_hash, event_hash) in enumerate(rows, start=1):
                if (seq != count or prev_hash != previous
                    or self._event_hash(seq, at, kind, payload, prev_hash) != event_hash):
                    raise AuditIntegrityError(f"Event hash chain invalid at sequence {seq}")
                previous = event_hash
            db.commit()
        return [
            {"seq": seq, "time_utc": at, "kind": kind, "payload": payload,
             "prev_hash": prev_hash, "event_hash": event_hash}
            for seq, at, kind, payload, prev_hash, event_hash in rows
        ]

    def events(self) -> list[tuple[int, str]]:
        return [(int(row["seq"]), str(row["kind"])) for row in self.read_verified_events()]
