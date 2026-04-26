from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from agent_factory.action_queue import ActionQueue
from agent_factory.config_loader import MEMORY_DIR
from agent_factory.pattern_memory import PatternMemory
from agent_factory.observers.screen_understanding import ScreenUnderstandingArtifact
from agent_factory.schemas import ActionQueueRecord


ReviewDecision = Literal["approved", "rejected", "needs_revision"]
RunFilter = Literal[
    "all runs",
    "browser research runs",
    "browser demo runs",
    "self-improvement runs",
    "runs with high-risk actions",
]

RUN_LOG_PATH = MEMORY_DIR / "agent_runs.jsonl"
SCREENSHOT_DIR = MEMORY_DIR / "screenshots"
REVIEW_DECISIONS_PATH = MEMORY_DIR / "review_decisions.jsonl"
LESSONS_LEARNED_PATH = MEMORY_DIR / "lessons_learned.jsonl"

HIGH_RISK_ACTION_TYPES = {
    "submit_form",
    "send_message",
    "save_record",
    "purchase_item",
    "delete_data",
    "enter_credentials",
    "deploy",
    "production_change",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL in {path} at line {line_number}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL rows must be objects in {path} at line {line_number}")
            rows.append(payload)
    return rows


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def latest_run(path: Path = RUN_LOG_PATH) -> dict[str, Any] | None:
    runs = read_jsonl(path)
    if not runs:
        return None
    return runs[-1]


def short_text(value: str, max_length: int = 70) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."


def action_value_preview(value: Any, max_length: int = 48) -> str:
    if value is None:
        return ""
    return short_text(str(value).replace("\n", " "), max_length=max_length)


def run_label(run: dict[str, Any]) -> str:
    run_id = str(run.get("run_id", "unknown"))
    timestamp = str(run.get("timestamp_utc", "no timestamp"))
    task = run.get("task", {})
    task_text = task.get("text", "") if isinstance(task, dict) else ""
    routing = run.get("routing", {})
    routing = routing if isinstance(routing, dict) else {}
    task_type = str(routing.get("task_type", "unknown"))
    selected_agent = str(routing.get("selected_agent", "unknown"))
    return f"{timestamp} | {run_id} | {task_type} | {selected_agent} | {short_text(task_text)}"


def run_selector_options(runs: list[dict[str, Any]]) -> list[str]:
    return [run_label(run) for run in runs]


def browser_demo_artifact(run: dict[str, Any]) -> dict[str, Any]:
    artifacts = run.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return {}
    browser_demo = artifacts.get("browser_demo", {})
    if not isinstance(browser_demo, dict):
        return {}
    return browser_demo


def browser_demo_executed(run: dict[str, Any]) -> bool:
    return browser_demo_artifact(run).get("executed") is True


def has_browser_research(run: dict[str, Any]) -> bool:
    return bool(browser_research_for_display(run))


def action_is_high_risk(action: dict[str, Any]) -> bool:
    action_type = str(action.get("action_type", "")).lower()
    return action_type in HIGH_RISK_ACTION_TYPES


def run_has_high_risk_actions(run: dict[str, Any]) -> bool:
    actions = run.get("recommended_actions", [])
    if not isinstance(actions, list):
        return False
    return any(isinstance(action, dict) and action_is_high_risk(action) for action in actions)


def filter_runs(runs: list[dict[str, Any]], run_filter: RunFilter) -> list[dict[str, Any]]:
    if run_filter == "all runs":
        return runs
    if run_filter == "browser research runs":
        return [run for run in runs if has_browser_research(run)]
    if run_filter == "browser demo runs":
        return [run for run in runs if browser_demo_executed(run)]
    if run_filter == "self-improvement runs":
        return [
            run
            for run in runs
            if isinstance(run.get("routing"), dict)
            and run["routing"].get("selected_agent") == "self_improvement_agent"
        ]
    if run_filter == "runs with high-risk actions":
        return [run for run in runs if run_has_high_risk_actions(run)]
    raise ValueError(f"Unsupported run filter: {run_filter}")


def default_run_index(runs: list[dict[str, Any]]) -> int:
    if not runs:
        return 0
    for index in range(len(runs) - 1, -1, -1):
        if has_browser_research(runs[index]):
            return index
    for index in range(len(runs) - 1, -1, -1):
        if browser_demo_executed(runs[index]):
            return index
    return len(runs) - 1


def build_review_decision(
    run: dict[str, Any],
    decision: ReviewDecision,
    reviewer: str = "James",
    notes: str = "",
) -> dict[str, Any]:
    if decision not in {"approved", "rejected", "needs_revision"}:
        raise ValueError(f"Unsupported review decision: {decision}")
    return {
        "review_id": f"review-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
        "run_id": run.get("run_id"),
        "decision": decision,
        "notes": notes,
        "executes_actions": False,
        "high_risk_actions_present": run_has_high_risk_actions(run),
        "safety_note": "Human review console records decisions only; it does not submit, send, save records, purchase, or execute browser actions.",
    }


def write_review_decision(
    run: dict[str, Any],
    decision: ReviewDecision,
    notes: str = "",
    path: Path = REVIEW_DECISIONS_PATH,
) -> dict[str, Any]:
    payload = build_review_decision(run, decision=decision, notes=notes)
    append_jsonl(path, payload)
    return payload


def build_lesson_learned(
    run: dict[str, Any],
    lesson_text: str,
    reviewer: str = "James",
) -> dict[str, Any]:
    lesson_text = lesson_text.strip()
    if not lesson_text:
        raise ValueError("Lesson learned text is required.")
    return {
        "lesson_id": f"lesson-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "reviewer": reviewer,
        "run_id": run.get("run_id"),
        "task_text": (run.get("task") or {}).get("text") if isinstance(run.get("task"), dict) else None,
        "lesson": lesson_text,
        "executes_actions": False,
    }


def write_lesson_learned(
    run: dict[str, Any],
    lesson_text: str,
    path: Path = LESSONS_LEARNED_PATH,
) -> dict[str, Any]:
    payload = build_lesson_learned(run, lesson_text=lesson_text)
    append_jsonl(path, payload)
    return payload


def promote_lesson_to_pattern(
    lesson: dict[str, Any],
    title: str | None = None,
    keywords: list[str] | None = None,
    memory: PatternMemory | None = None,
) -> dict[str, Any]:
    memory = memory or PatternMemory()
    return memory.promote_lesson_to_pattern(lesson, title=title, keywords=keywords).model_dump(mode="json")


def create_approved_pattern(
    title: str,
    description: str,
    keywords: list[str] | None = None,
    memory: PatternMemory | None = None,
) -> dict[str, Any]:
    memory = memory or PatternMemory()
    return memory.create_pattern(title=title, description=description, keywords=keywords).model_dump(mode="json")


def deactivate_pattern(pattern_id: str, memory: PatternMemory | None = None) -> dict[str, Any]:
    memory = memory or PatternMemory()
    return memory.deactivate_pattern(pattern_id).model_dump(mode="json")


def browser_demo_screenshots(run: dict[str, Any]) -> dict[str, Path]:
    browser_demo = browser_demo_artifact(run)
    screenshots: dict[str, Path] = {}
    for key in ("before_screenshot", "after_screenshot"):
        value = browser_demo.get(key)
        if not value:
            continue
        path = Path(str(value))
        if path.exists():
            screenshots[key] = path
    return screenshots


def improvement_proposals_for_display(run: dict[str, Any]) -> list[dict[str, Any]]:
    proposals = run.get("improvement_proposals", [])
    if not isinstance(proposals, list):
        return []
    return [proposal for proposal in proposals if isinstance(proposal, dict)]


def browser_research_for_display(run: dict[str, Any]) -> dict[str, Any]:
    artifacts = run.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return {}
    research = artifacts.get("browser_research", {})
    if not isinstance(research, dict):
        return {}
    return research


def browser_research_artifacts_for_display(run: dict[str, Any]) -> dict[str, Any]:
    research = browser_research_for_display(run)
    if not research:
        return {}
    return {
        "research_id": research.get("research_id"),
        "url": research.get("url"),
        "domain": research.get("domain"),
        "allowed": research.get("allowed"),
        "blocked_reason": research.get("blocked_reason"),
        "read_only": research.get("read_only"),
        "listing": research.get("listing"),
        "visible_text_excerpt": research.get("visible_text_excerpt"),
        "screenshot_path": research.get("screenshot_path"),
        "tron_review": research.get("tron_review"),
        "proposed_actions": research.get("proposed_actions"),
    }


def browser_research_screenshot_path(run: dict[str, Any]) -> Path | None:
    research = browser_research_for_display(run)
    screenshot = research.get("screenshot_path")
    if not screenshot:
        return None
    path = Path(str(screenshot))
    return path if path.exists() else None


def queue_records_for_display(run_id: str, queue: ActionQueue | None = None) -> list[dict[str, Any]]:
    queue = queue or ActionQueue()
    return [record.model_dump(mode="json") for record in queue.list_records_for_run(run_id)]


def action_queue_row_label(record: ActionQueueRecord) -> str:
    parts = [record.action.action_type]
    if record.action.field_name:
        parts.append(record.action.field_name)
    preview = action_value_preview(record.action.value)
    if preview:
        parts.append(preview)
    parts.extend([record.approval_status, record.execution_status])
    return " | ".join(parts)


def action_queue_detail(record: ActionQueueRecord) -> dict[str, Any]:
    action = record.action
    return {
        "action_id": record.action_id,
        "run_id": record.run_id,
        "action_type": action.action_type,
        "app_name": action.app_name,
        "field_name": action.field_name,
        "value": action.value,
        "risk_level": action.risk_level,
        "reversible": action.reversible,
        "approval_status": record.approval_status,
        "execution_status": record.execution_status,
        "reviewer": record.reviewer,
        "review_notes": record.review_notes,
        "execution_result": record.execution_result,
    }


def _json_block(label: str, value: Any) -> None:
    import streamlit as st

    st.subheader(label)
    st.json(value)


def render_app() -> None:
    import streamlit as st

    st.set_page_config(page_title="Ariadne Human Review Console", layout="wide")
    st.title("Ariadne Human Review Console")
    st.caption("Local-only review of Ariadne runs. Records decisions and lessons; does not execute actions.")

    runs = read_jsonl(RUN_LOG_PATH)
    lessons = read_jsonl(LESSONS_LEARNED_PATH)
    pattern_memory = PatternMemory()
    if not runs:
        st.info(f"No runs found at {RUN_LOG_PATH}. Run Ariadne first, then refresh this console.")
        return

    run_filter = st.selectbox(
        "Filter",
        ["all runs", "browser research runs", "browser demo runs", "self-improvement runs", "runs with high-risk actions"],
        index=0,
    )
    visible_runs = filter_runs(runs, run_filter)  # type: ignore[arg-type]
    if not visible_runs:
        st.info(f"No runs match filter: {run_filter}")
        return

    labels = run_selector_options(visible_runs)
    selected_label = st.selectbox("Run", labels, index=default_run_index(visible_runs))
    run = visible_runs[labels.index(selected_label)]

    task = run.get("task", {}) if isinstance(run.get("task"), dict) else {}
    routing = run.get("routing", {})
    observation = run.get("screen_observation", {})
    actions = run.get("recommended_actions", [])
    approvals = run.get("approval_decisions", [])
    critic = run.get("critic_review", {})
    improvement_proposals = improvement_proposals_for_display(run)
    browser_research = browser_research_for_display(run)
    action_queue = ActionQueue()
    queued_actions = action_queue.list_records_for_run(str(run.get("run_id", "")))

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Run")
        st.write(f"**run_id:** {run.get('run_id', 'unknown')}")
        st.write(f"**timestamp:** {run.get('timestamp_utc', 'unknown')}")
        st.write(f"**task:** {task.get('text', '')}")

        _json_block("Routing Decision", routing)
        _json_block("Screen Observation", observation)
        _json_block("Recommended Actions", actions)
        _json_block("Approval Decisions", approvals)
        _json_block("Tron Critic Review", critic)
        if improvement_proposals:
            _json_block("Improvement Proposals", improvement_proposals)
        if browser_research:
            _json_block("Browser Research Summary", browser_research_artifacts_for_display(run))

        st.subheader("Action Queue")
        if not queued_actions:
            st.info("No queued actions found for this run.")
        for record in queued_actions:
            action = record.action
            can_execute, execute_reason = action_queue.can_execute(record)
            high_risk_or_never = action.action_type in {
                "submit_form",
                "send_message",
                "save_record",
                "delete_data",
                "purchase_item",
                "credential_access",
                "deploy",
                "production_change",
            } or action.risk_level in {"high", "critical"}
            with st.expander(action_queue_row_label(record)):
                st.json(action_queue_detail(record))
                if high_risk_or_never:
                    st.warning(f"Execution blocked: {execute_reason}")
                queue_notes = st.text_input("Queue review notes", key=f"queue_notes_{record.action_id}")
                cols = st.columns(4)
                with cols[0]:
                    if st.button("Approve action", key=f"approve_{record.action_id}", use_container_width=True):
                        action_queue.set_approval_status(record.action_id, "approved", notes=queue_notes)
                        st.success("Action approved.")
                with cols[1]:
                    if st.button("Reject action", key=f"reject_{record.action_id}", use_container_width=True):
                        action_queue.set_approval_status(record.action_id, "rejected", notes=queue_notes)
                        st.warning("Action rejected.")
                with cols[2]:
                    if st.button("Mark needs revision", key=f"revise_{record.action_id}", use_container_width=True):
                        action_queue.set_approval_status(record.action_id, "needs_revision", notes=queue_notes)
                        st.info("Action marked for revision.")
                with cols[3]:
                    if st.button(
                        "Execute approved local demo action",
                        key=f"execute_{record.action_id}",
                        use_container_width=True,
                        disabled=not can_execute,
                        help=None if can_execute else execute_reason,
                    ):
                        result = action_queue.execute_action(record.action_id, attempted_by="James")
                        if result.execution_status == "executed":
                            st.success("Local demo action executed.")
                        else:
                            st.error(result.execution_result.get("blocked_reason", "Execution blocked."))

    with right:
        st.subheader("Review Controls")
        notes = st.text_area("Review notes", height=120)

        if st.button("Approve run", use_container_width=True):
            decision = write_review_decision(run, "approved", notes=notes)
            st.success(f"Recorded approval: {decision['review_id']}")
        if st.button("Reject run", use_container_width=True):
            decision = write_review_decision(run, "rejected", notes=notes)
            st.warning(f"Recorded rejection: {decision['review_id']}")
        if st.button("Mark needs revision", use_container_width=True):
            decision = write_review_decision(run, "needs_revision", notes=notes)
            st.info(f"Recorded revision request: {decision['review_id']}")

        st.divider()
        lesson_text = st.text_area("Lesson learned", height=140)
        if st.button("Save lesson learned", use_container_width=True):
            try:
                lesson = write_lesson_learned(run, lesson_text)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Saved lesson: {lesson['lesson_id']}")

        if lessons:
            with st.expander("Recent lessons"):
                for lesson in lessons[-5:][::-1]:
                    st.write(f"**{lesson.get('timestamp_utc', 'unknown')}**")
                    st.write(lesson.get("lesson", ""))
                    if st.button("Promote lesson to approved pattern", key=f"promote_{lesson.get('lesson_id', lesson.get('timestamp_utc'))}"):
                        pattern = promote_lesson_to_pattern(lesson, memory=pattern_memory)
                        st.success(f"Promoted pattern: {pattern['title']}")

        with st.expander("Pattern Memory"):
            st.write("Approved patterns inform recommendations only.")
            pattern_title = st.text_input("New pattern title")
            pattern_description = st.text_area("New pattern description", height=90)
            pattern_keywords = st.text_input("Keywords, comma-separated")
            if st.button("Create new approved pattern", use_container_width=True):
                if not pattern_title.strip() or not pattern_description.strip():
                    st.error("Pattern title and description are required.")
                else:
                    pattern = create_approved_pattern(
                        pattern_title,
                        pattern_description,
                        keywords=[item.strip() for item in pattern_keywords.split(",") if item.strip()] or None,
                        memory=pattern_memory,
                    )
                    st.success(f"Created pattern: {pattern['title']}")

            active_patterns = pattern_memory.approved_patterns()
            if active_patterns:
                selected_pattern = st.selectbox(
                    "Deactivate pattern",
                    [f"{pattern.pattern_id} | {pattern.title}" for pattern in active_patterns],
                )
                if st.button("Deactivate pattern", use_container_width=True):
                    pattern_id = selected_pattern.split(" | ", 1)[0]
                    pattern = deactivate_pattern(pattern_id, memory=pattern_memory)
                    st.warning(f"Deactivated pattern: {pattern['title']}")

        st.divider()
        st.subheader("Safety")
        st.write("No submit, send, save-record, purchase, delete, credential, deployment, or production action is executed.")
        st.write(f"High-risk actions present in plan: **{run_has_high_risk_actions(run)}**")

    st.subheader("Browser Research Artifacts")
    research_artifacts = browser_research_artifacts_for_display(run)
    if research_artifacts:
        st.json(research_artifacts)
        research_screenshot = browser_research_screenshot_path(run)
        if research_screenshot:
            st.image(str(research_screenshot), caption=str(research_screenshot), use_container_width=True)
    else:
        st.info("No browser research artifacts are referenced by the selected run.")

    st.subheader("Browser Demo Artifacts")
    screenshots = browser_demo_screenshots(run)
    if screenshots:
        cols = st.columns(2)
        if "before_screenshot" in screenshots:
            with cols[0]:
                st.write("**Before screenshot**")
                st.image(
                    str(screenshots["before_screenshot"]),
                    caption=str(screenshots["before_screenshot"]),
                    use_container_width=True,
                )
        if "after_screenshot" in screenshots:
            with cols[1]:
                st.write("**After screenshot**")
                st.image(
                    str(screenshots["after_screenshot"]),
                    caption=str(screenshots["after_screenshot"]),
                    use_container_width=True,
                )
    else:
        st.info("No browser demo screenshots are referenced by the selected run.")

    with st.expander("Raw Run JSON"):
        st.json(run)


def _running_inside_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except Exception:
        return False
    return get_script_run_ctx() is not None


def main() -> None:
    try:
        import streamlit  # noqa: F401
    except Exception as exc:
        raise SystemExit(
            "Streamlit is not installed. Install the optional UI dependencies with: "
            'python -m pip install -e ".[ui]"'
        ) from exc

    if _running_inside_streamlit():
        render_app()
        return

    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(Path(__file__).resolve()),
            "--server.address",
            "localhost",
            "--server.headless",
            "true",
        ],
        check=False,
    )


if __name__ == "__main__":
    main()


def render_screen_understanding(artifact: ScreenUnderstandingArtifact) -> str:
    observed_text = artifact.observed_text or "<not available>"
    file_size = artifact.file_size_bytes if artifact.file_size_bytes is not None else "<unknown>"

    lines = [
        "=== Screen Understanding Artifact ===",
        f"Screenshot: {artifact.screenshot_path}",
        f"Screenshot exists: {artifact.screenshot_exists}",
        f"File size bytes: {file_size}",
        f"Summary: {artifact.screen_summary}",
        f"Confidence: {artifact.confidence}",
        f"Observed text: {observed_text}",
        "Limitations:",
    ]

    for limitation in artifact.limitations:
        lines.append(f"- {limitation}")

    lines.append(f"Executable actions: {artifact.executable_actions}")

    return "\n".join(lines)

