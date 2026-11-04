"""AA-002 read-only monitor coverage tests; all fixtures are synthetic."""
from __future__ import annotations

import json
import secrets
import sqlite3

import pytest

from agent_factory.assurance import (
    ActionIntent, AssuranceReconciler, AuditIntegrityError, AuditLedger,
    DemoGrantAuthority, GuardedBroker, ReviewDecision, SyntheticFixtureAdapter,
    SyntheticOnlyPolicy,
)


def action(*, aid="a1"):
    return ActionIntent(run_id="synthetic-run", action_id=aid,
                        proposer_agent="demo", tool_id="synthetic_fixture",
                        operation="write_fixture_field", target="healthcare_intake",
                        arguments={"field": "status", "value": "reviewed"})


def review(intent):
    return ReviewDecision(run_id=intent.run_id, action_id=intent.action_id,
                          arguments_sha256=intent.arguments_sha256,
                          reviewer_principal="demo:tester",
                          review_source="synthetic_test_fixture", decision="approved")


@pytest.fixture
def components(tmp_path):
    path = tmp_path / "intake.json"
    path.write_text(json.dumps({"feature_name": "Synthetic Feature", "owner": "Test Owner", "status": "pending"}))
    policy = SyntheticOnlyPolicy()
    authority = DemoGrantAuthority(tmp_path / "grants.db", secret=secrets.token_bytes(32), policy=policy)
    audit = AuditLedger(tmp_path / "audit.db")
    broker = GuardedBroker(policy, authority, audit, SyntheticFixtureAdapter(path))
    return broker, AssuranceReconciler(audit, authority)


def codes(report):
    return {finding.code for finding in report.findings}


def test_complete_valid_dispatch_reconciles(components):
    broker, monitor = components
    a = action()
    assert broker.dispatch(a, broker.authority.issue(a, review(a))).status == "observed_succeeded"
    result = monitor.inspect()
    assert result.healthy
    assert result.checked_events == 2
    assert result.checked_grants == 1


def test_prohibited_action_only_is_not_a_dispatch(components):
    broker, monitor = components
    denied = action().model_copy(update={"operation": "send_message"})
    assert broker.dispatch(denied).status == "blocked"
    assert monitor.inspect().healthy


def test_consumed_grant_missing_dispatch_is_detected(components):
    broker, monitor = components
    a = action()
    grant = broker.authority.issue(a, review(a))
    broker.authority.consume(a, grant)
    assert "CONSUMED_GRANT_WITHOUT_DISPATCH_EVENT" in codes(monitor.inspect())


def test_dispatch_without_terminal_receipt_is_detected(components):
    broker, monitor = components
    a = action()
    grant = broker.authority.issue(a, review(a))
    broker.authority.consume(a, grant)
    broker.audit.append("dispatch_attempt", {
        "run_id": a.run_id, "action_id": a.action_id, "grant_id": grant.grant_id,
    })
    assert "MISSING_TERMINAL_RECEIPT" in codes(monitor.inspect())


def test_terminal_without_attempt_is_detected(components):
    broker, monitor = components
    a = action()
    broker.audit.append("observed_succeeded", {"run_id": a.run_id, "action_id": a.action_id})
    assert "ORPHAN_TERMINAL_RECEIPT" in codes(monitor.inspect())


def test_duplicate_attempt_and_double_use_are_detected(components):
    broker, monitor = components
    a = action()
    grant = broker.authority.issue(a, review(a))
    broker.authority.consume(a, grant)
    payload = {"run_id": a.run_id, "action_id": a.action_id, "grant_id": grant.grant_id}
    broker.audit.append("dispatch_attempt", payload)
    broker.audit.append("dispatch_attempt", payload)
    broker.audit.append("observed_succeeded", {"run_id": a.run_id, "action_id": a.action_id})
    issues = codes(monitor.inspect())
    assert "DUPLICATE_DISPATCH_ATTEMPT" in issues
    assert "GRANT_USED_FOR_MULTIPLE_DISPATCHES" in issues


def test_multiple_terminal_receipts_are_detected(components):
    broker, monitor = components
    a = action()
    grant = broker.authority.issue(a, review(a))
    broker.authority.consume(a, grant)
    broker.audit.append("dispatch_attempt", {"run_id": a.run_id, "action_id": a.action_id, "grant_id": grant.grant_id})
    broker.audit.append("observed_failed", {"run_id": a.run_id, "action_id": a.action_id})
    broker.audit.append("observed_succeeded", {"run_id": a.run_id, "action_id": a.action_id})
    assert "MULTIPLE_TERMINAL_RECEIPTS" in codes(monitor.inspect())


def test_unknown_effect_requires_manual_review(components):
    broker, monitor = components
    a = action()
    grant = broker.authority.issue(a, review(a))
    broker.authority.consume(a, grant)
    broker.audit.append("dispatch_attempt", {"run_id": a.run_id, "action_id": a.action_id, "grant_id": grant.grant_id})
    broker.audit.append("unknown_effect", {"run_id": a.run_id, "action_id": a.action_id})
    result = monitor.inspect()
    assert not result.healthy
    assert result.requires_review
    assert "UNKNOWN_EFFECT_REQUIRES_REVIEW" in codes(result)


def test_unknown_grant_is_detected(components):
    broker, monitor = components
    broker.audit.append("dispatch_attempt", {"run_id": "synthetic-run", "action_id": "a1", "grant_id": "not-known"})
    assert "DISPATCH_WITH_UNKNOWN_GRANT" in codes(monitor.inspect())


def test_unconsumed_grant_with_dispatch_is_detected(components):
    broker, monitor = components
    a = action()
    grant = broker.authority.issue(a, review(a))
    broker.audit.append("dispatch_attempt", {"run_id": a.run_id, "action_id": a.action_id, "grant_id": grant.grant_id})
    assert "DISPATCH_WITHOUT_CONSUMED_GRANT" in codes(monitor.inspect())


def test_corruption_aborts_monitor_without_false_healthy(components):
    broker, monitor = components
    broker.audit.append("blocked", {"run_id": "r", "action_id": "a"})
    with sqlite3.connect(broker.audit._path) as db:
        db.execute("UPDATE events SET payload='{}' WHERE seq=1")
    with pytest.raises(AuditIntegrityError):
        monitor.inspect()


def test_non_json_valid_hash_still_not_accepted_as_valid_evidence(components):
    broker, monitor = components
    # Authorized append can hash arbitrary payload strings only if code is compromised.
    # Simulate by changing payload plus recomputing hash as the active DB owner.
    from agent_factory.assurance.ledger import GENESIS
    broker.audit.append("dispatch_attempt", {"run_id": "r", "action_id": "a"})
    with sqlite3.connect(broker.audit._path) as db:
        seq, at, kind = db.execute("SELECT seq,time_utc,kind FROM events WHERE seq=1").fetchone()
        forged = "invalid JSON"
        chainhash = broker.audit._event_hash(seq, at, kind, forged, GENESIS)
        db.execute("UPDATE events SET payload=?, event_hash=? WHERE seq=1", (forged, chainhash))
    with pytest.raises(ValueError, match="Invalid audit event JSON"):
        monitor.inspect()
