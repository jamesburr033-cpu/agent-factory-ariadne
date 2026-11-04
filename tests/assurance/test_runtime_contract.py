"""Synthetic-only AA-001 security/assurance contract regression tests."""
from __future__ import annotations

import json
import secrets
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_factory.assurance import (
    ActionIntent, AuditIntegrityError, AuditLedger, CapabilityGrant, DemoGrantAuthority,
    GrantError, GuardedBroker, ReviewDecision, SyntheticFixtureAdapter, SyntheticOnlyPolicy,
)


def intent(**changes):
    base = dict(run_id="synthetic-run-1", action_id="a1", proposer_agent="fixture-agent", tool_id="synthetic_fixture", operation="write_fixture_field", target="healthcare_intake", arguments={"field": "status", "value": "reviewed"})
    base.update(changes)
    return ActionIntent(**base)


def review(action, *, decision="approved", principal="demo:tester"):
    return ReviewDecision(run_id=action.run_id, action_id=action.action_id, arguments_sha256=action.arguments_sha256, reviewer_principal=principal, review_source="synthetic_test_fixture", decision=decision)


@pytest.fixture
def system(tmp_path):
    fixture = tmp_path / "synthetic_healthcare_intake.json"
    fixture.write_text(json.dumps({"feature_name": "Synthetic Feature", "owner": "Test Owner", "status": "pending"}), encoding="utf-8")
    policy = SyntheticOnlyPolicy()
    authority = DemoGrantAuthority(tmp_path / "grants.db", secret=secrets.token_bytes(32), policy=policy)
    audit = AuditLedger(tmp_path / "audit.db")
    adapter = SyntheticFixtureAdapter(fixture)
    return GuardedBroker(policy, authority, audit, adapter), fixture


def test_allowed_action_is_once_and_observed(system):
    broker, fixture = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    result = broker.dispatch(action, grant)
    assert result.status == "observed_succeeded"
    assert result.observed_state_sha256
    assert json.loads(fixture.read_text())["status"] == "reviewed"
    assert [k for _, k in broker.audit.events()] == ["dispatch_attempt", "observed_succeeded"]
    second = broker.dispatch(action, grant)
    assert second.status == "blocked"
    assert "used" in second.reason
    assert [k for _, k in broker.audit.events()][-1] == "blocked"


@pytest.mark.parametrize("operation", ["send_message", "purchase_item", "delete_data", "deploy", "submit_form", "credential_access", "production_change"])
def test_forbidden_operations_never_dispatch_even_with_requested_approval(system, operation):
    broker, fixture = system
    action = intent(operation=operation)
    with pytest.raises(GrantError):
        broker.authority.issue(action, review(action))
    result = broker.dispatch(action)
    assert result.status == "blocked"
    assert json.loads(fixture.read_text())["status"] == "pending"


@pytest.mark.parametrize("changes", [
    {"tool_id": "email"}, {"target": "C:\\Users\\private"},
    {"operation": "run_shell"}, {"arguments": {"field": "secret", "value": "bad"}},
    {"arguments": {"field": "status", "value": "a", "extra": "bad"}},
    {"arguments": {"field": "status", "value": ""}},
])
def test_policy_default_denies_unknown_or_malformed_actions(system, changes):
    broker, _ = system
    result = broker.dispatch(intent(**changes))
    assert result.status == "blocked"


def test_argument_mutation_invalidates_grant(system):
    broker, fixture = system
    original = intent()
    grant = broker.authority.issue(original, review(original))
    changed = intent(arguments={"field": "status", "value": "approved"})
    result = broker.dispatch(changed, grant)
    assert result.status == "blocked"
    assert json.loads(fixture.read_text())["status"] == "pending"


def test_missing_grant_and_unapproved_decision_are_denied(system):
    broker, _ = system
    action = intent()
    assert broker.dispatch(action).status == "blocked"
    with pytest.raises(GrantError):
        broker.authority.issue(action, review(action, decision="rejected"))
    with pytest.raises(GrantError):
        broker.authority.issue(action, review(action, principal="James"))


def test_expired_grant_denied(system):
    broker, _ = system
    action = intent()
    grant = broker.authority.issue(action, review(action), ttl_seconds=1, now=10)
    assert broker.dispatch(action, grant, now=11).status == "blocked"


def test_revoked_grant_denied(system):
    broker, _ = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    broker.authority.revoke(grant.grant_id)
    assert broker.dispatch(action, grant).status == "blocked"


def test_signature_tamper_denied(system):
    broker, fixture = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    bad = grant.model_copy(update={"expires_at": grant.expires_at + 100})
    assert broker.dispatch(action, bad).status == "blocked"
    assert json.loads(fixture.read_text())["status"] == "pending"


def test_cross_run_grant_reuse_denied(system):
    broker, _ = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    assert broker.dispatch(intent(run_id="other-run"), grant).status == "blocked"


def test_approval_hash_mismatch_denied(system):
    broker, _ = system
    action = intent()
    mismatched = review(intent(arguments={"field": "status", "value": "else"}))
    with pytest.raises(GrantError):
        broker.authority.issue(action, mismatched)


def test_tampered_audit_fails_closed(system):
    broker, fixture = system
    first = intent()
    broker.dispatch(first)  # intentionally denied, creates audit receipt
    with sqlite3.connect(broker.audit._path) as db:
        db.execute("UPDATE events SET kind='forged' WHERE seq=1")
    with pytest.raises(AuditIntegrityError):
        broker.dispatch(first)
    assert json.loads(fixture.read_text())["status"] == "pending"


def test_missing_audit_database_fails_closed(system):
    broker, fixture = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    broker.audit._path.unlink()
    with pytest.raises(sqlite3.OperationalError):
        broker.dispatch(action, grant)
    assert json.loads(fixture.read_text())["status"] == "pending"


def test_two_workers_cannot_consume_single_grant(system):
    broker, fixture = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: broker.dispatch(action, grant).status, range(2)))
    assert results.count("observed_succeeded") == 1
    assert results.count("blocked") == 1
    assert json.loads(fixture.read_text())["status"] == "reviewed"
    broker.audit.verify()


def test_schema_rejects_unexpected_fields():
    with pytest.raises(Exception):
        intent(untrusted="unknown")


def test_synthetic_fixture_not_silent_success_when_missing(system):
    broker, fixture = system
    action = intent()
    grant = broker.authority.issue(action, review(action))
    fixture.unlink()
    result = broker.dispatch(action, grant)
    assert result.status == "unknown_effect"
    assert result.observed_state_sha256 is None
    assert [k for _, k in broker.audit.events()] == ["dispatch_attempt", "unknown_effect"]
