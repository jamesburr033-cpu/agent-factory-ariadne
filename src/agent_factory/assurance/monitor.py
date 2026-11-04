"""Read-only, synthetic-only evidence reconciliation (AA-002 prototype).

This does not run as a protected monitoring service. An attacker with database
write permission may rewrite a chain, delete its tail, or edit grant records.
Never treat this report as proof of tamper resistance or external execution.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from .grants import DemoGrantAuthority
from .ledger import AuditLedger


@dataclass(frozen=True)
class ReconciliationFinding:
    code: str
    severity: Literal["warning", "critical"]
    run_id: str | None = None
    action_id: str | None = None
    grant_id: str | None = None


@dataclass(frozen=True)
class ReconciliationReport:
    checked_events: int
    checked_grants: int
    findings: tuple[ReconciliationFinding, ...]

    @property
    def healthy(self) -> bool:
        return not self.findings

    @property
    def requires_review(self) -> bool:
        return bool(self.findings)


class AssuranceReconciler:
    """Verify hash chain, grant consumption and dispatch-to-receipt coverage.

    This is intentionally not connected to an executable tool. It flags gaps
    rather than repairing them or automatically retrying an unknown effect.
    """

    _terminal = frozenset({"observed_succeeded", "observed_failed", "unknown_effect"})

    def __init__(self, audit: AuditLedger, authority: DemoGrantAuthority):
        self._audit = audit
        self._authority = authority

    def inspect(self) -> ReconciliationReport:
        # Invariant violations in the ledger raise AuditIntegrityError and must
        # never be quietly converted into an empty or successful report.
        events = self._audit.read_verified_events()
        grants = self._authority.grant_snapshot()
        findings: list[ReconciliationFinding] = []
        attempts: dict[tuple[str, str], list[dict]] = defaultdict(list)
        terminals: dict[tuple[str, str], list[str]] = defaultdict(list)
        attempted_grants: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for entry in events:
            kind = entry["kind"]
            raw = entry["payload"]
            try:
                payload = json.loads(raw)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid audit event JSON at {entry['seq']}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Invalid audit event payload at {entry['seq']}")
            if kind not in {"dispatch_attempt", *self._terminal}:
                continue
            run_id, action_id = payload.get("run_id"), payload.get("action_id")
            if not isinstance(run_id, str) or not run_id or not isinstance(action_id, str) or not action_id:
                findings.append(ReconciliationFinding("MISSING_ACTION_IDENTITY", "critical"))
                continue
            key = (run_id, action_id)
            if kind == "dispatch_attempt":
                attempts[key].append(payload)
                grant_id = payload.get("grant_id")
                if not isinstance(grant_id, str) or not grant_id:
                    findings.append(ReconciliationFinding("MISSING_DISPATCH_GRANT", "critical", run_id, action_id))
                else:
                    attempted_grants[grant_id].append(key)
            else:
                terminals[key].append(kind)
                if kind == "unknown_effect":
                    findings.append(ReconciliationFinding("UNKNOWN_EFFECT_REQUIRES_REVIEW", "warning", run_id, action_id))

        for key in sorted(attempts.keys() | terminals.keys()):
            at_count = len(attempts[key])
            terminal_count = len(terminals[key])
            if at_count > 1:
                findings.append(ReconciliationFinding("DUPLICATE_DISPATCH_ATTEMPT", "critical", *key))
            if at_count == 0 and terminal_count:
                findings.append(ReconciliationFinding("ORPHAN_TERMINAL_RECEIPT", "critical", *key))
            if at_count and not terminal_count:
                findings.append(ReconciliationFinding("MISSING_TERMINAL_RECEIPT", "critical", *key))
            if terminal_count > 1:
                findings.append(ReconciliationFinding("MULTIPLE_TERMINAL_RECEIPTS", "critical", *key))

        for grant_id, consumed, revoked in grants:
            uses = attempted_grants.get(grant_id, [])
            if consumed and not uses:
                findings.append(ReconciliationFinding("CONSUMED_GRANT_WITHOUT_DISPATCH_EVENT", "critical", grant_id=grant_id))
            if uses and not consumed:
                findings.append(ReconciliationFinding("DISPATCH_WITHOUT_CONSUMED_GRANT", "critical", grant_id=grant_id))
            if len(uses) > 1:
                findings.append(ReconciliationFinding("GRANT_USED_FOR_MULTIPLE_DISPATCHES", "critical", grant_id=grant_id))
        grant_ids = {row[0] for row in grants}
        for grant_id in attempted_grants:
            if grant_id not in grant_ids:
                findings.append(ReconciliationFinding("DISPATCH_WITH_UNKNOWN_GRANT", "critical", grant_id=grant_id))

        return ReconciliationReport(
            checked_events=len(events), checked_grants=len(grants), findings=tuple(findings)
        )
