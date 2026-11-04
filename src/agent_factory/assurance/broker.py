"""Guarded local synthetic fixture broker. NEVER wire to real tools as-is."""
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from .grants import DemoGrantAuthority, GrantError
from .ledger import AuditLedger, AuditIntegrityError
from .models import ActionIntent, CapabilityGrant, DispatchResult, sha256
from .policy import SyntheticOnlyPolicy


class SyntheticFixtureAdapter:
    """One fixture file, fixed path, no arbitrary target selection or network."""

    def __init__(self, fixture_path: Path):
        self.path = Path(fixture_path)

    def apply(self, *, field: str, value: str) -> str:
        if self.path.is_symlink() or not self.path.exists() or not self.path.is_file():
            raise ValueError("Synthetic fixture is unavailable or not a regular file")
        before = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(before, dict) or field not in before:
            raise ValueError("Synthetic fixture schema mismatch")
        after = dict(before)
        after[field] = value
        # Atomic replacement within fixture directory; no user-supplied path.
        temp_name = None
        try:
            with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, prefix=".fixture-", suffix=".tmp", delete=False) as f:
                temp_name = f.name
                json.dump(after, f, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_name, self.path)
            temp_name = None
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)
        observed = json.loads(self.path.read_text(encoding="utf-8"))
        if observed.get(field) != value:
            raise RuntimeError("Fixture update was not observed")
        return sha256(observed)


class GuardedBroker:
    """Contract demonstration only; current process owns all components."""

    def __init__(self, policy: SyntheticOnlyPolicy, authority: DemoGrantAuthority, audit: AuditLedger, adapter: SyntheticFixtureAdapter):
        self.policy = policy
        self.authority = authority
        self.audit = audit
        self.adapter = adapter

    def dispatch(self, intent: ActionIntent, grant: CapabilityGrant | None = None, *, now: int | None = None) -> DispatchResult:
        decision = self.policy.evaluate(intent)
        # Do not dispatch if the audit database is missing, malformed, or compromised.
        self.audit.verify()
        if not decision.allowed:
            self.audit.append("blocked", {"run_id": intent.run_id, "action_id": intent.action_id, "rule_id": decision.rule_id})
            return DispatchResult(action_id=intent.action_id, status="blocked", reason=decision.rule_id)
        if grant is None:
            self.audit.append("blocked", {"run_id": intent.run_id, "action_id": intent.action_id, "reason": "missing_grant"})
            return DispatchResult(action_id=intent.action_id, status="blocked", reason="missing_grant")
        try:
            self.authority.consume(intent, grant, now=now)
        except GrantError as exc:
            self.audit.append("blocked", {"run_id": intent.run_id, "action_id": intent.action_id, "reason": str(exc)})
            return DispatchResult(action_id=intent.action_id, status="blocked", reason=str(exc))
        # Missing audit writer => no side effect. Grant remains consumed (safe failure).
        self.audit.append("dispatch_attempt", {"run_id": intent.run_id, "action_id": intent.action_id, "tool": intent.tool_id, "grant_id": grant.grant_id, "arguments_sha256": intent.arguments_sha256})
        try:
            state_hash = self.adapter.apply(field=intent.arguments["field"], value=intent.arguments["value"])
        except Exception as exc:
            try:
                self.audit.append("unknown_effect", {"run_id": intent.run_id, "action_id": intent.action_id, "error_type": type(exc).__name__})
            except Exception:
                pass
            return DispatchResult(action_id=intent.action_id, status="unknown_effect", reason="Adapter failed; investigate fixture and evidence")
        try:
            self.audit.append("observed_succeeded", {"run_id": intent.run_id, "action_id": intent.action_id, "observed_state_sha256": state_hash})
        except Exception:
            # The side effect may have occurred, but the receipt is not durable.
            return DispatchResult(action_id=intent.action_id, status="unknown_effect", reason="Audit receipt unavailable after side effect")
        return DispatchResult(action_id=intent.action_id, status="observed_succeeded", reason="Synthetic fixture state verified", observed_state_sha256=state_hash)
