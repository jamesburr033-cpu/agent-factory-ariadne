from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any, Optional


@dataclass
class OcrTextResult:
    screenshot_path: str
    screenshot_exists: bool
    observed_text: Optional[str]
    confidence: str
    engine: str
    raw_observed_text: Optional[str] = None
    cleaned_observed_text: Optional[str] = None
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    executable_actions: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OcrTextExtractor:
    """Read-only OCR extractor.

    This class does not click, type, submit, send, buy, delete, or control the screen.
    It only attempts to read text from an existing screenshot file.
    """

    def extract(self, screenshot_path: str) -> OcrTextResult:
        path = Path(screenshot_path)

        if not path.exists():
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=False,
                observed_text=None,
                confidence="low",
                engine="none",
                limitations=["Screenshot file does not exist."],
                executable_actions=[],
            )

        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore
        except Exception:
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=True,
                observed_text=None,
                confidence="low",
                engine="none",
                limitations=[
                    "OCR dependencies are not installed or not available.",
                    "Install Tesseract OCR and pytesseract to enable text extraction.",
                ],
                executable_actions=[],
            )

        try:
            image = Image.open(path)
            raw_text = pytesseract.image_to_string(image).strip()
        except Exception as exc:
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=True,
                observed_text=None,
                confidence="low",
                engine="pytesseract",
                limitations=[f"OCR failed safely: {exc}"],
                executable_actions=[],
            )

        if not raw_text:
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=True,
                observed_text=None,
                confidence="low",
                engine="pytesseract",
                raw_observed_text="",
                cleaned_observed_text=None,
                limitations=["OCR ran but found no visible text."],
                executable_actions=[],
            )

        cleaned_text = self.clean_text(raw_text)

        return OcrTextResult(
            screenshot_path=str(path),
            screenshot_exists=True,
            observed_text=cleaned_text,
            confidence="medium" if cleaned_text else "low",
            engine="pytesseract",
            raw_observed_text=raw_text,
            cleaned_observed_text=cleaned_text,
            limitations=[] if cleaned_text else ["OCR found text, but cleanup removed all usable content."],
            metadata={
                "character_count": len(raw_text),
                "cleaned_character_count": len(cleaned_text or ""),
                "line_count": len([line for line in raw_text.splitlines() if line.strip()]),
                "cleaned_line_count": len([line for line in (cleaned_text or "").splitlines() if line.strip()]),
            },
            executable_actions=[],
        )

    def clean_text(self, text: str) -> Optional[str]:
        lines: list[str] = []

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            line = self._normalize_line(line)

            if self._is_noise_line(line):
                continue

            lines.append(line)

        cleaned = "\n".join(lines).strip()
        return cleaned or None

    def _normalize_line(self, line: str) -> str:
        line = line.replace("“", '"').replace("”", '"').replace("’", "'")
        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"[^\w\s.,:;!?@#/$%&()+=\-_'\"\\[\]{}<>|]", "", line)
        return line.strip()

    def _is_noise_line(self, line: str) -> bool:
        lowered = line.lower()

        if len(line) <= 2:
            return True

        noise_markers = {
            "chatgpt can make mistakes",
            "normal text file",
            "windows crlf",
            "utf-8",
            "ins",
        }

        if any(marker in lowered for marker in noise_markers):
            return True

        alpha_count = sum(char.isalpha() for char in line)
        if alpha_count == 0:
            return True

        symbol_count = sum(not char.isalnum() and not char.isspace() for char in line)
        if symbol_count > alpha_count * 2:
            return True

        return False
