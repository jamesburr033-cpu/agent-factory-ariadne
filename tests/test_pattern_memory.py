import json
from pathlib import Path
from uuid import uuid4

from agent_factory.agents.browser_agent import BrowserAgent
from agent_factory.master_agent import AriadneMasterAgent
from agent_factory.pattern_memory import PatternMemory, read_jsonl
from agent_factory.review_console import deactivate_pattern, promote_lesson_to_pattern
from agent_factory.schemas import UserTask


def _test_path(filename: str) -> Path:
    path = Path("memory") / "test_review_console" / f"{uuid4()}_{filename}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _pattern_row(pattern_id: str = "pattern-1", active: bool = True):
    return {
        "pattern_id": pattern_id,
        "title": "Require GPU-Z screenshot",
        "description": "Ask for GPU-Z proof before considering a GPU listing.",
        "keywords": ["gpu", "rtx", "listing", "gpu-z"],
        "source": "manual",
        "confidence": "high",
        "active": active,
        "created_by": "James",
    }


def _memory_with_patterns(*patterns: dict) -> PatternMemory:
    patterns_path = _test_path("patterns.jsonl")
    lessons_path = _test_path("lessons.jsonl")
    usage_path = _test_path("pattern_usage.jsonl")
    patterns_path.write_text("".join(json.dumps(pattern) + "\n" for pattern in patterns), encoding="utf-8")
    return PatternMemory(patterns_path=patterns_path, lessons_path=lessons_path, usage_path=usage_path)


def test_reads_approved_patterns():
    memory = _memory_with_patterns(_pattern_row())

    patterns = memory.approved_patterns()

    assert len(patterns) == 1
    assert patterns[0].title == "Require GPU-Z screenshot"


def test_ignores_deactivated_patterns():
    memory = _memory_with_patterns(_pattern_row(active=False))

    assert memory.approved_patterns() == []
    assert memory.relevant_patterns("RTX 3090 GPU listing") == []


def test_does_not_write_patterns_automatically_during_normal_run():
    memory = _memory_with_patterns(_pattern_row())
    before = memory.patterns_path.read_text(encoding="utf-8")
    ariadne = AriadneMasterAgent()
    ariadne.pattern_memory = memory
    ariadne.browser_agent.pattern_memory = memory
    ariadne.browser_research_agent.pattern_memory = memory

    ariadne.run(UserTask(text="Evaluate RTX 3090 listing price is 650 dollars 24 GB VRAM used", mode="demo"))

    assert memory.patterns_path.read_text(encoding="utf-8") == before


def test_relevant_gpu_patterns_are_applied_to_gpu_tasks():
    memory = _memory_with_patterns(_pattern_row())
    observation, actions = BrowserAgent(pattern_memory=memory).plan(
        UserTask(text="Evaluate RTX 3090 GPU listing", mode="demo"),
        run_id="run-1",
    )

    assert "Pattern applied: Require GPU-Z screenshot" in observation.notes
    red_flags = [action.value for action in actions if action.field_name == "Red flags"][0]
    assert "Require GPU-Z screenshot" in red_flags


def test_pattern_usage_is_logged():
    memory = _memory_with_patterns(_pattern_row())

    BrowserAgent(pattern_memory=memory).plan(UserTask(text="Evaluate RTX 4090 GPU listing", mode="demo"), run_id="run-1")
    rows = read_jsonl(memory.usage_path)

    assert rows
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["pattern_id"] == "pattern-1"
    assert rows[0]["pattern_title"] == "Require GPU-Z screenshot"
    assert rows[0]["source"] == "manual"
    assert rows[0]["confidence"] == "high"


def test_review_console_can_promote_lesson_to_pattern():
    memory = PatternMemory(
        patterns_path=_test_path("patterns.jsonl"),
        lessons_path=_test_path("lessons.jsonl"),
        usage_path=_test_path("usage.jsonl"),
    )
    lesson = {"lesson_id": "lesson-1", "lesson": "Always ask for timestamped photos on GPU deals.", "approved": True}

    pattern = promote_lesson_to_pattern(lesson, memory=memory)

    assert pattern["source"] == "lesson"
    assert pattern["source_lesson_id"] == "lesson-1"
    assert memory.approved_patterns()[0].description == lesson["lesson"]


def test_review_console_can_deactivate_pattern():
    memory = _memory_with_patterns(_pattern_row())

    deactivated = deactivate_pattern("pattern-1", memory=memory)

    assert deactivated["active"] is False
    assert memory.approved_patterns() == []
