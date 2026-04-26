from pathlib import Path
from uuid import uuid4

from agent_factory.action_queue import ActionQueue, read_jsonl
from agent_factory.master_agent import AriadneMasterAgent
from agent_factory.schemas import AgentRunLog, ApprovalDecision, CriticReview, RecommendedAction, RoutingDecision, UserTask


def _test_path(filename: str) -> Path:
    path = Path("memory") / "test_review_console" / f"{uuid4()}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _action(
    action_type: str = "fill_field",
    risk_level: str = "low",
    app_name: str = "GPU Deal Evaluator",
) -> RecommendedAction:
    return RecommendedAction(
        action_type=action_type,
        description=f"Test {action_type}",
        app_name=app_name,
        field_name="Product",
        value="RTX 3090",
        risk_level=risk_level,
    )


def _run(actions: list[RecommendedAction]) -> AgentRunLog:
    return AgentRunLog(
        run_id=str(uuid4()),
        task=UserTask(text="Evaluate RTX 3090", mode="demo"),
        routing=RoutingDecision(task_type="browser_research", selected_agent="browser_agent", reason="test"),
        recommended_actions=actions,
        critic_review=CriticReview(summary="test"),
    )


class TrackingTron:
    def __init__(self, allowed: bool = True) -> None:
        self.called = False
        self.allowed = allowed

    def final_action_check(self, action: RecommendedAction) -> ApprovalDecision:
        self.called = True
        return ApprovalDecision(
            action=action,
            allowed=self.allowed,
            approval_required=not self.allowed,
            blocked_reason=None if self.allowed else "tracking tron blocked",
            status="allowed" if self.allowed else "blocked",
        )


def _queue(tron=None) -> ActionQueue:
    return ActionQueue(queue_path=_test_path("action_queue.jsonl"), event_path=_test_path("action_queue_events.jsonl"), tron=tron)


def test_master_agent_creates_pending_actions():
    ariadne = AriadneMasterAgent()
    ariadne.action_queue = _queue()

    run = ariadne.run(UserTask(text="Evaluate RTX 3090 listing price is 650 dollars 24 GB VRAM used", mode="demo"))
    records = ariadne.action_queue.list_records_for_run(run.run_id)

    assert records
    assert all(record.approval_status == "pending" for record in records)
    assert all(record.execution_status == "not_executed" for record in records)


def test_approval_status_changes():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action()]))[0]

    approved = queue.set_approval_status(record.action_id, "approved", notes="Safe local demo field.")

    assert approved.approval_status == "approved"
    assert approved.review_notes == "Safe local demo field."


def test_reject_action_updates_status():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action()]))[0]

    rejected = queue.set_approval_status(record.action_id, "rejected", notes="Not safe enough.")

    assert rejected.approval_status == "rejected"
    assert rejected.review_notes == "Not safe enough."


def test_needs_revision_updates_status():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action()]))[0]

    revised = queue.set_approval_status(record.action_id, "needs_revision", notes="Clarify value.")

    assert revised.approval_status == "needs_revision"
    assert revised.review_notes == "Clarify value."


def test_rejected_actions_cannot_execute():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action()]))[0]
    queue.set_approval_status(record.action_id, "rejected")

    result = queue.execute_action(record.action_id)

    assert result.execution_status == "blocked"
    assert result.execution_result["executed"] is False
    assert "approved" in result.execution_result["reason"]


def test_high_risk_actions_cannot_execute():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action(risk_level="high")]))[0]
    queue.set_approval_status(record.action_id, "approved")

    result = queue.execute_action(record.action_id)

    assert result.execution_status == "blocked"
    assert "low or medium" in result.execution_result["reason"]


def test_submit_form_cannot_execute_even_if_approved():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action(action_type="submit_form", risk_level="high")]))[0]
    queue.set_approval_status(record.action_id, "approved")

    result = queue.execute_action(record.action_id)

    assert result.execution_status == "blocked"
    assert "submit_form must never execute" in result.execution_result["reason"]


def test_approved_local_fill_field_action_can_execute():
    queue = _queue()
    record = queue.enqueue_run_actions(_run([_action()]))[0]
    queue.set_approval_status(record.action_id, "approved")

    result = queue.execute_action(record.action_id)

    assert result.execution_status == "executed"
    assert result.execution_result["executed"] is True
    assert result.execution_result["action_type"] == "fill_field"


def test_tron_final_check_runs_before_execution():
    tron = TrackingTron()
    queue = _queue(tron=tron)
    record = queue.enqueue_run_actions(_run([_action()]))[0]
    queue.set_approval_status(record.action_id, "approved")

    result = queue.execute_action(record.action_id)

    assert tron.called is True
    assert result.execution_status == "executed"


def test_action_execution_writes_audit_record():
    event_path = _test_path("action_queue_events.jsonl")
    queue = ActionQueue(queue_path=_test_path("action_queue.jsonl"), event_path=event_path)
    record = queue.enqueue_run_actions(_run([_action()]))[0]
    queue.set_approval_status(record.action_id, "approved")

    queue.execute_action(record.action_id)
    events = read_jsonl(event_path)

    assert [event["event_type"] for event in events] == [
        "queue_created",
        "approval_decision",
        "execution_attempt",
        "execution_result",
    ]

    result_event = events[-1]
    assert result_event["action_id"] == record.action_id
    assert result_event["run_id"] == record.run_id
    assert result_event["timestamp_utc"]
    assert result_event["attempted_by"] == "James"
    assert result_event["result"] == "executed"
    assert result_event["blocked_reason"] is None
    assert result_event["tron_final_check_result"]["allowed"] is True


def test_blocked_execution_is_logged():
    event_path = _test_path("action_queue_events.jsonl")
    queue = ActionQueue(queue_path=_test_path("action_queue.jsonl"), event_path=event_path)
    record = queue.enqueue_run_actions(_run([_action(action_type="submit_form", risk_level="high")]))[0]
    queue.set_approval_status(record.action_id, "approved")

    queue.execute_action(record.action_id, attempted_by="James")
    result_event = read_jsonl(event_path)[-1]

    assert result_event["event_type"] == "execution_result"
    assert result_event["result"] == "blocked"
    assert result_event["blocked_reason"] == "submit_form must never execute in v0.6.1."
