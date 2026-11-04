"""Demo one-shot HMAC grants with atomic SQLite consumption.

The HMAC key and ledger MUST move to a protected, separately authenticated
service before any real tool is connected. Here they demonstrate the contract.
"""
from __future__ import annotations

import hmac
import secrets
import sqlite3
import time
from hashlib import sha256 as hashlib_sha256
from pathlib import Path
from uuid import uuid4

from .models import ActionIntent, CapabilityGrant, ReviewDecision, canonical_json
from .policy import SyntheticOnlyPolicy


class GrantError(RuntimeError):
    pass


class DemoGrantAuthority:
    def __init__(self, ledger_path: Path, *, secret: bytes, policy: SyntheticOnlyPolicy | None = None):
        if len(secret) < 32:
            raise ValueError("Demo MAC key must be at least 32 bytes")
        self._secret = secret
        self._path = Path(ledger_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._policy = policy or SyntheticOnlyPolicy()
        with self._connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS grants (id TEXT PRIMARY KEY, consumed INTEGER NOT NULL DEFAULT 0, revoked INTEGER NOT NULL DEFAULT 0)")

    def _connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5, isolation_level=None)

    def _mac(self, payload: dict[str, object]) -> str:
        return hmac.new(self._secret, canonical_json(payload), hashlib_sha256).hexdigest()

    def issue(self, intent: ActionIntent, review: ReviewDecision, *, ttl_seconds: int = 60, now: int | None = None) -> CapabilityGrant:
        if not 1 <= ttl_seconds <= 300:
            raise GrantError("Grant lifetime must be 1–300 seconds")
        if review.review_source != "synthetic_test_fixture" or not review.reviewer_principal.startswith("demo:"):
            raise GrantError("Only synthetic test identities can approve demo grants")
        if review.decision != "approved" or review.run_id != intent.run_id or review.action_id != intent.action_id or review.arguments_sha256 != intent.arguments_sha256:
            raise GrantError("Review decision is missing, denied, or not bound to this action")
        if not self._policy.evaluate(intent).allowed:
            raise GrantError("Policy forbids issuing this grant")
        issued_at = int(time.time()) if now is None else now
        fields = dict(
            grant_id=str(uuid4()), run_id=intent.run_id, action_id=intent.action_id,
            arguments_sha256=intent.arguments_sha256,
            tool_id=intent.tool_id, operation=intent.operation, target=intent.target,
            issued_at=issued_at, expires_at=issued_at + ttl_seconds,
        )
        # Build validated payload so serialization exactly matches later verification.
        unsigned = CapabilityGrant(**fields, signature="")
        grant = unsigned.model_copy(update={"signature": self._mac(unsigned.signed_payload())})
        with self._connection() as db:
            db.execute("INSERT INTO grants(id) VALUES (?)", (grant.grant_id,))
        return grant

    def revoke(self, grant_id: str) -> None:
        with self._connection() as db:
            db.execute("UPDATE grants SET revoked=1 WHERE id=?", (grant_id,))

    def grant_snapshot(self) -> list[tuple[str, bool, bool]]:
        """Read-only status for the synthetic assurance reconciler."""
        with self._connection() as db:
            db.execute("BEGIN")
            rows = db.execute("SELECT id, consumed, revoked FROM grants ORDER BY id").fetchall()
            db.commit()
        return [(row[0], bool(row[1]), bool(row[2])) for row in rows]

    def consume(self, intent: ActionIntent, grant: CapabilityGrant, *, now: int | None = None) -> None:
        expected = self._mac(grant.signed_payload())
        if not hmac.compare_digest(expected, grant.signature):
            raise GrantError("Invalid grant signature")
        if (
            grant.run_id, grant.action_id, grant.arguments_sha256, grant.tool_id,
            grant.operation, grant.target, grant.policy_version
        ) != (
            intent.run_id, intent.action_id, intent.arguments_sha256, intent.tool_id,
            intent.operation, intent.target, self._policy.version
        ):
            raise GrantError("Grant not bound to this exact action")
        actual_now = int(time.time()) if now is None else now
        if actual_now < grant.issued_at or actual_now >= grant.expires_at:
            raise GrantError("Grant expired or not yet valid")
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("UPDATE grants SET consumed=1 WHERE id=? AND consumed=0 AND revoked=0", (grant.grant_id,))
            if cur.rowcount != 1:
                db.rollback()
                raise GrantError("Grant unknown, used, or revoked")
            db.commit()
