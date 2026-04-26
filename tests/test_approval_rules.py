from agent_factory.approvals import ApprovalGate
from agent_factory.schemas import RecommendedAction


def test_submit_requires_approval():
    gate = ApprovalGate()
    decision = gate.evaluate(
        RecommendedAction(action_type="submit_form", description="Submit", app_name="ServiceNow", risk_level="high"),
        mode="assisted_fill",
    )
    assert decision.allowed is True
    assert decision.approval_required is True
    assert decision.status == "requires_approval_before_execution"


def test_fill_field_blocked_in_advisor_mode():
    gate = ApprovalGate()
    decision = gate.evaluate(
        RecommendedAction(
            action_type="fill_field",
            description="Fill short description",
            app_name="ServiceNow",
            field_name="Short description",
            value="Test",
        ),
        mode="advisor",
    )
    assert decision.allowed is False
    assert decision.approval_required is True
    assert decision.status == "blocked"
    assert "mode_is_assisted_fill_or_demo" in decision.conditions_failed


def test_fill_field_allowed_in_assisted_mode_when_allowlisted():
    gate = ApprovalGate()
    decision = gate.evaluate(
        RecommendedAction(
            action_type="fill_field",
            description="Fill short description",
            app_name="ServiceNow",
            field_name="Short description",
            value="Test",
        ),
        mode="assisted_fill",
    )
    assert decision.allowed is True
    assert decision.approval_required is False
    assert decision.status == "allowed"


def test_production_epic_change_blocked():
    gate = ApprovalGate()
    decision = gate.evaluate(
        RecommendedAction(
            action_type="production_epic_change",
            description="Change Epic production build",
            app_name="Epic",
            risk_level="critical",
            reversible=False,
        ),
        mode="assisted_fill",
    )
    assert decision.allowed is False
    assert decision.approval_required is True
    assert decision.status == "blocked"
