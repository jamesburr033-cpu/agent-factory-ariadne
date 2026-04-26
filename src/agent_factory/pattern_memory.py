from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from .config_loader import MEMORY_DIR
from .schemas import PatternConfidence, PatternSource, WorkflowPattern


PATTERNS_PATH = MEMORY_DIR / "patterns.jsonl"
LESSONS_PATH = MEMORY_DIR / "lessons_learned.jsonl"
PATTERN_USAGE_PATH = MEMORY_DIR / "pattern_usage.jsonl"


def append_jsonl(path: Path, item: dict[str, Any] | BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = item.model_dump(mode="json") if isinstance(item, BaseModel) else item
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                payload = json.loads(line)
                if isinstance(payload, dict):
                    rows.append(payload)
    return rows


class PatternMemory:
    """Read-only advisory memory for normal agent runs.

    Normal agent runs may read patterns and log usage. Pattern creation and deactivation
    are explicit review-console actions only.
    """

    def __init__(
        self,
        patterns_path: Path = PATTERNS_PATH,
        lessons_path: Path = LESSONS_PATH,
        usage_path: Path = PATTERN_USAGE_PATH,
    ) -> None:
        self.patterns_path = patterns_path
        self.lessons_path = lessons_path
        self.usage_path = usage_path

    def approved_patterns(self) -> list[WorkflowPattern]:
        latest: dict[str, WorkflowPattern] = {}
        for row in read_jsonl(self.patterns_path):
            pattern = WorkflowPattern.model_validate(row)
            latest[pattern.pattern_id] = pattern
        return [pattern for pattern in latest.values() if pattern.active]

    def approved_lessons(self) -> list[dict[str, Any]]:
        lessons: list[dict[str, Any]] = []
        for row in read_jsonl(self.lessons_path):
            approved = row.get("approved") is True or row.get("status") == "approved"
            if approved and row.get("lesson"):
                lessons.append(row)
        return lessons

    def relevant_patterns(self, task_text: str, limit: int = 8) -> list[WorkflowPattern]:
        text = task_text.lower()
        scored: list[tuple[int, WorkflowPattern]] = []
        for pattern in self.approved_patterns():
            haystack = " ".join([pattern.title, pattern.description, *pattern.keywords]).lower()
            score = sum(1 for keyword in pattern.keywords if keyword.lower() in text)
            if score == 0 and any(token in haystack for token in text.split()):
                score = 1
            if score > 0:
                scored.append((score, pattern))
        scored.sort(key=lambda item: (item[0], item[1].confidence == "high"), reverse=True)
        return [pattern for _, pattern in scored[:limit]]

    def log_usage(self, run_id: str, patterns: list[WorkflowPattern]) -> None:
        for pattern in patterns:
            append_jsonl(
                self.usage_path,
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                    "pattern_id": pattern.pattern_id,
                    "pattern_title": pattern.title,
                    "source": pattern.source,
                    "confidence": pattern.confidence,
                },
            )

    def promote_lesson_to_pattern(
        self,
        lesson: dict[str, Any],
        title: str | None = None,
        keywords: list[str] | None = None,
        confidence: PatternConfidence = "medium",
        created_by: str = "James",
    ) -> WorkflowPattern:
        pattern = WorkflowPattern(
            pattern_id=f"pattern-{uuid4()}",
            title=title or str(lesson.get("lesson", "Lesson pattern"))[:80],
            description=str(lesson.get("lesson", "")),
            keywords=keywords or self._keywords_from_text(str(lesson.get("lesson", ""))),
            source="lesson",
            confidence=confidence,
            active=True,
            created_by=created_by,
            source_lesson_id=lesson.get("lesson_id"),
        )
        append_jsonl(self.patterns_path, pattern)
        return pattern

    def create_pattern(
        self,
        title: str,
        description: str,
        keywords: list[str] | None = None,
        source: PatternSource = "manual",
        confidence: PatternConfidence = "medium",
        created_by: str = "James",
    ) -> WorkflowPattern:
        pattern = WorkflowPattern(
            pattern_id=f"pattern-{uuid4()}",
            title=title.strip(),
            description=description.strip(),
            keywords=keywords or self._keywords_from_text(f"{title} {description}"),
            source=source,
            confidence=confidence,
            active=True,
            created_by=created_by,
        )
        append_jsonl(self.patterns_path, pattern)
        return pattern

    def deactivate_pattern(self, pattern_id: str, deactivated_by: str = "James") -> WorkflowPattern:
        latest = {pattern.pattern_id: pattern for pattern in self.approved_patterns()}
        if pattern_id not in latest:
            raise ValueError(f"Unknown active pattern: {pattern_id}")
        pattern = latest[pattern_id].model_copy(update={"active": False, "created_by": deactivated_by})
        append_jsonl(self.patterns_path, pattern)
        return pattern

    def _keywords_from_text(self, text: str) -> list[str]:
        words = [
            word.strip(".,:;!?()[]{}").lower()
            for word in text.split()
            if len(word.strip(".,:;!?()[]{}")) >= 4
        ]
        seen: list[str] = []
        for word in words:
            if word not in seen:
                seen.append(word)
        return seen[:12]
