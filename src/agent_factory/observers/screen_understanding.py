from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class ScreenUnderstandingArtifact:
    screenshot_path: str
    screenshot_exists: bool
    file_size_bytes: Optional[int]
    screen_summary: str
    observed_text: Optional[str]
    confidence: str
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    executable_actions: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScreenUnderstandingAnalyzer:
    """Read-only screenshot artifact understanding.

    v0.7.1 intentionally does not perform OCR, vision-model calls, clicks,
    typing, submitting, sending, buying, deleting, or credential handling.
    """

    def analyze(
        self,
        screenshot_path: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ScreenUnderstandingArtifact:
        metadata = metadata or {}
        path = Path(screenshot_path)
        exists = path.exists()
        file_size = path.stat().st_size if exists else None

        active_window = metadata.get("active_window_title")
        app_name = metadata.get("app_name")

        limitations = [
            "No OCR or vision model is connected in v0.7.1.",
            "Understanding is based on artifact metadata only.",
        ]

        if not exists:
            limitations.append("Screenshot file does not exist.")
            summary = "Screenshot artifact was referenced, but the file could not be found."
            confidence = "low"
        elif active_window:
            summary = f"Screenshot artifact exists. Active window at capture time: {active_window}."
            confidence = "medium"
        elif app_name:
            summary = f"Screenshot artifact exists. Detected app at capture time: {app_name}."
            confidence = "medium"
        else:
            summary = "Screenshot artifact exists, but no screen metadata was provided."
            confidence = "low"

        return ScreenUnderstandingArtifact(
            screenshot_path=str(path),
            screenshot_exists=exists,
            file_size_bytes=file_size,
            screen_summary=summary,
            observed_text=None,
            confidence=confidence,
            limitations=limitations,
            metadata=metadata,
            executable_actions=[],
        )
