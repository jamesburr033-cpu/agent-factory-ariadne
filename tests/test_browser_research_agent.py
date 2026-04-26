from pathlib import Path
from uuid import uuid4

from agent_factory.action_queue import ActionQueue, read_jsonl
from agent_factory.agents.browser_research_agent import BrowserResearchAgent
from agent_factory.audit_log import JsonlAuditLog
from agent_factory.master_agent import AriadneMasterAgent
from agent_factory.review_console import action_queue_row_label
from agent_factory.schemas import AgentRunLog, CriticReview, RecommendedAction, RoutingDecision, UserTask


def _test_path(filename: str) -> Path:
    path = Path("memory") / "test_review_console" / f"{uuid4()}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _agent() -> BrowserResearchAgent:
    return BrowserResearchAgent()


def _listing_text() -> str:
    return """
    EVGA RTX 3090 FTW3 Ultra 24GB
    $650
    Location: Portland, OR
    Condition: Used
    Seller notes: Works great, no benchmark posted yet. Local pickup.
    """


def _run_with_actions(actions: list[RecommendedAction]) -> AgentRunLog:
    return AgentRunLog(
        run_id=str(uuid4()),
        task=UserTask(text="https://www.ebay.com/itm/123", mode="demo"),
        routing=RoutingDecision(task_type="browser_research", selected_agent="browser_agent", reason="test"),
        recommended_actions=actions,
        critic_review=CriticReview(summary="test"),
    )


def test_blocked_non_allowlisted_domain():
    result = _agent().research_url("https://example.com/rtx-3090", visible_text=_listing_text())

    assert result.allowed is False
    assert "not allowlisted" in (result.blocked_reason or "")
    assert result.proposed_actions == []


def test_example_org_read_only_url_routes_then_allowlist_blocks_it():
    ariadne = AriadneMasterAgent()
    ariadne.action_queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))

    result = ariadne.run(
        UserTask(text="Read-only browser research this listing https://example.org/rtx-3090", mode="demo")
    )
    research = result.artifacts["browser_research"]

    assert result.routing.task_type == "browser_research"
    assert research["allowed"] is False
    assert "not allowlisted" in research["blocked_reason"]


def test_allowed_read_only_url():
    result = _agent().research_url("https://www.ebay.com/itm/123", visible_text=_listing_text())

    assert result.allowed is True
    assert result.read_only is True
    assert result.domain == "ebay.com"
    assert result.listing is not None
    assert result.listing.title == "EVGA RTX 3090 FTW3 Ultra 24GB"


def test_contact_send_buy_actions_blocked():
    queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))
    for action_type in ("send_message", "purchase_item"):
        action = RecommendedAction(
            action_type=action_type,
            description=f"Unsafe {action_type}",
            app_name="Browser Research Sandbox",
            risk_level="high",
            reversible=False,
        )
        record = queue.enqueue_run_actions(_run_with_actions([action]))[0]
        queue.set_approval_status(record.action_id, "approved")
        result = queue.execute_action(record.action_id)
        assert result.execution_status == "blocked"


def test_credential_fields_blocked():
    queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))
    action = RecommendedAction(
        action_type="credential_access",
        description="Enter password",
        app_name="Browser Research Sandbox",
        field_name="password",
        value="secret",
        risk_level="critical",
        reversible=False,
    )
    record = queue.enqueue_run_actions(_run_with_actions([action]))[0]
    queue.set_approval_status(record.action_id, "approved")

    result = queue.execute_action(record.action_id)

    assert result.execution_status == "blocked"
    assert "credential_access must never execute" in result.execution_result["blocked_reason"]


def test_extracted_listing_saved():
    path = _test_path("browser_research_runs.jsonl")
    agent = BrowserResearchAgent(audit_log=JsonlAuditLog(str(path)))
    result = agent.research_url("https://craigslist.org/listing/rtx3090", visible_text=_listing_text())

    assert result.listing is not None
    assert result.listing.price == "$650"
    assert agent.audit_log.path.exists()


def test_proposed_seller_message_queued_but_not_sent():
    ariadne = AriadneMasterAgent()
    ariadne.action_queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))

    result = ariadne.run(
        UserTask(text="https://www.ebay.com/itm/123", mode="demo", metadata={"visible_text": _listing_text()})
    )
    queued = ariadne.action_queue.list_records_for_run(result.run_id)

    assert any(record.action.action_type == "send_message" for record in queued)
    assert all(record.approval_status == "pending" for record in queued)
    assert all(record.execution_status == "not_executed" for record in queued)


def test_browser_research_proposed_actions_are_queued_with_required_shape():
    ariadne = AriadneMasterAgent()
    ariadne.action_queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))

    result = ariadne.run(
        UserTask(text="https://www.ebay.com/itm/123", mode="demo", metadata={"visible_text": _listing_text()})
    )
    queued = ariadne.action_queue.list_records_for_run(result.run_id)
    draft = next(record for record in queued if record.action.action_type == "send_message")

    assert draft.action_id
    assert draft.run_id == result.run_id
    assert draft.timestamp_utc
    assert draft.approval_status == "pending"
    assert draft.execution_status == "not_executed"
    assert draft.reviewer is None
    assert draft.review_notes == ""
    assert draft.execution_result == {}
    assert draft.action.risk_level == "high"


def test_draft_seller_message_appears_in_action_queue_label():
    ariadne = AriadneMasterAgent()
    ariadne.action_queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))
    result = ariadne.run(
        UserTask(text="https://www.ebay.com/itm/123", mode="demo", metadata={"visible_text": _listing_text()})
    )
    draft = ariadne.action_queue.list_records_for_run(result.run_id)[0]

    label = action_queue_row_label(draft)

    assert "send_message" in label
    assert "Draft seller message" in label
    assert "pending" in label
    assert "not_executed" in label


def test_approving_send_message_does_not_allow_execution_and_logs_block():
    event_path = _test_path("events.jsonl")
    ariadne = AriadneMasterAgent()
    ariadne.action_queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=event_path)
    result = ariadne.run(
        UserTask(text="https://www.ebay.com/itm/123", mode="demo", metadata={"visible_text": _listing_text()})
    )
    draft = ariadne.action_queue.list_records_for_run(result.run_id)[0]

    approved = ariadne.action_queue.set_approval_status(draft.action_id, "approved")
    executed = ariadne.action_queue.execute_action(approved.action_id)
    events = read_jsonl(event_path)

    assert approved.approval_status == "approved"
    assert executed.execution_status == "blocked"
    assert executed.execution_result["executed"] is False
    assert "send_message must never execute" in executed.execution_result["blocked_reason"]
    assert events[-1]["event_type"] == "execution_result"
    assert events[-1]["result"] == "blocked"
    assert events[-1]["action_id"] == draft.action_id


def test_no_send_contact_buy_submit_action_executes():
    queue = ActionQueue(queue_path=_test_path("queue.jsonl"), event_path=_test_path("events.jsonl"))
    for action_type in ("send_message", "contact_seller", "buy_now", "submit_form"):
        action = RecommendedAction(
            action_type=action_type,
            description=f"Unsafe {action_type}",
            app_name="Browser Research Sandbox",
            risk_level="high",
            reversible=False,
        )
        record = queue.enqueue_run_actions(_run_with_actions([action]))[0]
        queue.set_approval_status(record.action_id, "approved")

        result = queue.execute_action(record.action_id)

        assert result.execution_status == "blocked"
        assert result.execution_result["executed"] is False


def test_tron_review_generated():
    result = _agent().research_url("https://offerup.com/item/rtx-3090", visible_text=_listing_text())

    assert result.tron_review is not None
    assert result.tron_review.critic_name == "Tron"
    assert "send_message" in result.tron_review.required_approvals


def test_navigation_text_is_not_used_as_listing_title():
    text = """
    Skip to main content
    Sign in
    Register
    Shop by category
    MSI RTX 4090 SUPRIM X 24GB Graphics Card
    $1,450
    Condition: Used
    """

    listing = _agent().extract_listing(text, "https://www.ebay.com/itm/4090")

    assert listing.title == "MSI RTX 4090 SUPRIM X 24GB Graphics Card"
