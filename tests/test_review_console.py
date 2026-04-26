import json
from pathlib import Path
from uuid import uuid4

import pytest

from agent_factory.review_console import (
    action_queue_detail,
    action_queue_row_label,
    action_is_high_risk,
    browser_research_artifacts_for_display,
    browser_research_screenshot_path,
    browser_demo_screenshots,
    build_review_decision,
    default_run_index,
    filter_runs,
    improvement_proposals_for_display,
    latest_run,
    read_jsonl,
    run_selector_options,
    write_lesson_learned,
    write_review_decision,
)
from agent_factory.schemas import ActionQueueRecord, RecommendedAction


def _test_path(filename: str) -> Path:
    path = Path("memory") / "test_review_console" / f"{uuid4()}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _sample_run(run_id: str = "run-2"):
    return {
        "run_id": run_id,
        "timestamp_utc": "2026-04-25T20:39:47Z",
        "task": {"text": "Evaluate a local GPU listing", "mode": "demo"},
        "routing": {"selected_agent": "browser_agent", "task_type": "browser_research"},
        "recommended_actions": [
            {"action_type": "fill_field", "description": "Fill local demo field"},
            {"action_type": "submit_form", "description": "Submit form"},
        ],
        "approval_decisions": [],
        "critic_review": {"critic_name": "Tron", "summary": "Submit requires approval."},
        "artifacts": {"browser_demo": {"submit_clicked": False}},
    }


def _browser_demo_run(run_id: str = "browser-run", executed: bool = True, before: str | None = None, after: str | None = None):
    run = _sample_run(run_id)
    run["artifacts"] = {
        "browser_demo": {
            "executed": executed,
            "submit_clicked": False,
            "before_screenshot": before,
            "after_screenshot": after,
        }
    }
    return run


def _self_improvement_run(run_id: str = "self-run"):
    return {
        "run_id": run_id,
        "timestamp_utc": "2026-04-25T21:00:00Z",
        "task": {"text": "Review failed actions and self improve", "mode": "advisor"},
        "routing": {"selected_agent": "self_improvement_agent", "task_type": "self_improvement"},
        "recommended_actions": [],
        "approval_decisions": [],
        "critic_review": {"critic_name": "Tron", "summary": "Proposal only."},
        "improvement_proposals": [
            {
                "title": "Improve review notes",
                "problem_observed": "Reviewer notes were inconsistent.",
                "proposed_change": "Add a checklist.",
                "requires_human_approval": True,
                "may_apply_directly": False,
            }
        ],
        "artifacts": {},
    }


def _browser_research_run(run_id: str = "research-run", screenshot_path: str | None = None):
    run = _sample_run(run_id)
    run["timestamp_utc"] = "2026-04-25T22:00:00Z"
    run["task"] = {"text": "Read-only research https://www.ebay.com/itm/123", "mode": "demo"}
    run["artifacts"] = {
        "browser_research": {
            "research_id": "research-1",
            "url": "https://www.ebay.com/itm/123",
            "domain": "ebay.com",
            "allowed": True,
            "blocked_reason": None,
            "read_only": True,
            "listing": {
                "title": "RTX 3090 24GB",
                "price": "$650",
                "location": "Portland, OR",
                "condition": "Used",
                "seller_notes": "No benchmark posted.",
                "listing_url": "https://www.ebay.com/itm/123",
                "red_flags": ["Missing proof."],
                "recommended_next_step": "Draft proof request.",
            },
            "visible_text_excerpt": "RTX 3090 24GB $650",
            "screenshot_path": screenshot_path,
            "tron_review": {"critic_name": "Tron", "summary": "Contact requires approval."},
            "proposed_actions": [{"action_type": "send_message", "description": "Draft only"}],
        }
    }
    return run


def test_reading_latest_run():
    path = _test_path("agent_runs.jsonl")
    first = _sample_run("run-1")
    second = _sample_run("run-2")
    path.write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n", encoding="utf-8")

    assert latest_run(path)["run_id"] == "run-2"

def test_writing_review_decision():
    path = _test_path("review_decisions.jsonl")
    payload = write_review_decision(_sample_run(), "approved", notes="Looks safe.", path=path)

    rows = read_jsonl(path)
    assert len(rows) == 1
    assert rows[0] == payload
    assert rows[0]["run_id"] == "run-2"
    assert rows[0]["decision"] == "approved"
    assert rows[0]["executes_actions"] is False


def test_writing_lesson_learned():
    path = _test_path("lessons_learned.jsonl")
    payload = write_lesson_learned(_sample_run(), "Keep submit blocked in demos.", path=path)

    rows = read_jsonl(path)
    assert len(rows) == 1
    assert rows[0] == payload
    assert rows[0]["run_id"] == "run-2"
    assert rows[0]["lesson"] == "Keep submit blocked in demos."
    assert rows[0]["executes_actions"] is False


def test_empty_lesson_is_rejected():
    with pytest.raises(ValueError):
        write_lesson_learned(_sample_run(), "   ", path=_test_path("lessons_learned.jsonl"))


def test_review_console_does_not_execute_high_risk_actions():
    run = _sample_run()
    decision = build_review_decision(run, "approved", notes="Human approval recorded only.")

    assert action_is_high_risk({"action_type": "submit_form"}) is True
    assert decision["high_risk_actions_present"] is True
    assert decision["executes_actions"] is False
    assert "does not submit" in decision["safety_note"]


def test_run_selector_options_include_required_metadata():
    options = run_selector_options([_sample_run()])

    assert len(options) == 1
    assert "2026-04-25T20:39:47Z" in options[0]
    assert "run-2" in options[0]
    assert "browser_research" in options[0]
    assert "browser_agent" in options[0]
    assert "Evaluate a local GPU listing" in options[0]


def test_default_selection_prefers_latest_executed_browser_demo():
    runs = [
        _sample_run("old-normal"),
        _browser_demo_run("old-browser", executed=True),
        _sample_run("latest-normal"),
    ]

    assert default_run_index(runs) == 1


def test_default_selection_prefers_latest_browser_research_over_browser_demo():
    runs = [
        _browser_demo_run("old-browser", executed=True),
        _sample_run("normal"),
        _browser_research_run("latest-research"),
    ]

    assert default_run_index(runs) == 2


def test_default_selection_uses_latest_run_when_no_browser_demo_executed():
    runs = [
        _sample_run("old-normal"),
        _browser_demo_run("not-executed", executed=False),
        _sample_run("latest-normal"),
    ]

    assert default_run_index(runs) == 2


def test_artifact_filtering_uses_selected_run_only():
    selected_before = _test_path("selected_before.png")
    selected_after = _test_path("selected_after.png")
    other_before = _test_path("other_before.png")
    for path in (selected_before, selected_after, other_before):
        path.write_bytes(b"fake image bytes")

    selected_run = _browser_demo_run("selected", before=str(selected_before), after=str(selected_after))
    other_run = _browser_demo_run("other", before=str(other_before))

    screenshots = browser_demo_screenshots(selected_run)

    assert screenshots == {"before_screenshot": selected_before, "after_screenshot": selected_after}
    assert other_before not in screenshots.values()
    assert browser_demo_screenshots(other_run) == {"before_screenshot": other_before}


def test_self_improvement_run_does_not_show_unrelated_gpu_screenshots():
    unrelated = _test_path("gpu_deal_before_unrelated.png")
    unrelated.write_bytes(b"fake image bytes")

    assert browser_demo_screenshots(_self_improvement_run()) == {}


def test_improvement_proposals_display_data_is_available():
    proposals = improvement_proposals_for_display(_self_improvement_run())

    assert len(proposals) == 1
    assert proposals[0]["title"] == "Improve review notes"
    assert proposals[0]["requires_human_approval"] is True


def test_run_filters():
    browser_run = _browser_demo_run("browser", executed=True)
    research_run = _browser_research_run("research")
    self_run = _self_improvement_run()
    high_risk_run = _sample_run("high-risk")
    runs = [browser_run, research_run, self_run, high_risk_run]

    assert filter_runs(runs, "all runs") == runs
    assert filter_runs(runs, "browser research runs") == [research_run]
    assert filter_runs(runs, "browser demo runs") == [browser_run]
    assert filter_runs(runs, "self-improvement runs") == [self_run]
    assert filter_runs(runs, "runs with high-risk actions") == [browser_run, research_run, high_risk_run]


def test_browser_research_runs_appear_in_selector():
    options = run_selector_options([_browser_research_run()])

    assert "browser_research" in options[0]
    assert "browser_agent" in options[0]
    assert "Read-only research" in options[0]


def test_browser_research_screenshot_path_is_shown():
    screenshot = _test_path("research.png")
    screenshot.write_bytes(b"fake image bytes")

    run = _browser_research_run(screenshot_path=str(screenshot))
    artifacts = browser_research_artifacts_for_display(run)

    assert artifacts["screenshot_path"] == str(screenshot)
    assert browser_research_screenshot_path(run) == screenshot


def test_old_browser_demo_screenshots_not_shown_for_browser_research_runs():
    demo_screenshot = _test_path("gpu_deal_before_old.png")
    demo_screenshot.write_bytes(b"fake image bytes")
    run = _browser_research_run()

    assert browser_demo_screenshots(run) == {}


def test_action_queue_row_label_includes_field_name_and_value_preview():
    record = ActionQueueRecord(
        action_id="action-1",
        run_id="run-1",
        action=RecommendedAction(
            action_type="fill_field",
            description="Fill offer",
            app_name="GPU Deal Evaluator",
            field_name="Recommended offer",
            value="$550-$600",
            risk_level="low",
        ),
    )

    assert action_queue_row_label(record) == "fill_field | Recommended offer | $550-$600 | pending | not_executed"


def test_action_queue_detail_includes_required_fields():
    record = ActionQueueRecord(
        action_id="action-1",
        run_id="run-1",
        action=RecommendedAction(
            action_type="fill_field",
            description="Fill offer",
            app_name="GPU Deal Evaluator",
            field_name="Recommended offer",
            value="$550-$600",
            risk_level="low",
            reversible=True,
        ),
        approval_status="approved",
        reviewer="James",
        review_notes="Looks safe.",
        execution_result={"executed": False},
    )

    detail = action_queue_detail(record)

    assert detail["action_id"] == "action-1"
    assert detail["run_id"] == "run-1"
    assert detail["action_type"] == "fill_field"
    assert detail["app_name"] == "GPU Deal Evaluator"
    assert detail["field_name"] == "Recommended offer"
    assert detail["value"] == "$550-$600"
    assert detail["risk_level"] == "low"
    assert detail["reversible"] is True
    assert detail["approval_status"] == "approved"
    assert detail["execution_status"] == "not_executed"
    assert detail["reviewer"] == "James"
    assert detail["review_notes"] == "Looks safe."
    assert detail["execution_result"] == {"executed": False}
