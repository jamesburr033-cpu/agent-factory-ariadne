"""Synthetic-only standalone demo. NO network calls, credentials, or external actions."""
import json
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_factory.assurance import (
    ActionIntent, AssuranceReconciler, AuditLedger, DemoGrantAuthority, GuardedBroker,
    ReviewDecision, SyntheticFixtureAdapter, SyntheticOnlyPolicy,
)


def main():
    with TemporaryDirectory(prefix="ariadne-aa001-") as directory:
        root = Path(directory)
        fixture = root / "intake.json"
        fixture.write_text(json.dumps({"feature_name": "Synthetic AI Intake", "owner": "Test Reviewer", "status": "pending"}))
        policy = SyntheticOnlyPolicy()
        authority = DemoGrantAuthority(root / "grants.db", secret=secrets.token_bytes(32), policy=policy)
        audit = AuditLedger(root / "audit.db")
        broker = GuardedBroker(policy, authority, audit, SyntheticFixtureAdapter(fixture))
        allowed = ActionIntent(run_id="demo-1", action_id="action-1", proposer_agent="ariadne-demo", tool_id="synthetic_fixture", operation="write_fixture_field", target="healthcare_intake", arguments={"field": "status", "value": "reviewed"})
        decision = ReviewDecision(run_id=allowed.run_id, action_id=allowed.action_id, arguments_sha256=allowed.arguments_sha256, reviewer_principal="demo:fixture-reviewer", review_source="synthetic_test_fixture", decision="approved")
        grant = authority.issue(allowed, decision)
        allowed_result = broker.dispatch(allowed, grant)
        forbidden = allowed.model_copy(update={"action_id": "action-2", "operation": "send_message"})
        blocked_result = broker.dispatch(forbidden)
        audit.verify()
        reconciliation = AssuranceReconciler(audit, authority).inspect()
        print(json.dumps({
            "demo_only": True,
            "allowed_result": allowed_result.model_dump(),
            "forbidden_result": blocked_result.model_dump(),
            "observed_fixture": json.loads(fixture.read_text()),
            "audit_events": audit.events(),
            "monitor": {
                "healthy": reconciliation.healthy,
                "checked_events": reconciliation.checked_events,
                "checked_grants": reconciliation.checked_grants,
                "findings": [item.__dict__ for item in reconciliation.findings],
            },
        }, indent=2))


if __name__ == "__main__":
    main()
