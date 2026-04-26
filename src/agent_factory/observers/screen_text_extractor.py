from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class OcrTextResult:
    screenshot_path: str
    screenshot_exists: bool
    observed_text: Optional[str]
    confidence: str
    engine: str
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
            text = pytesseract.image_to_string(image).strip()
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

        if not text:
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=True,
                observed_text=None,
                confidence="low",
                engine="pytesseract",
                limitations=["OCR ran but found no visible text."],
                executable_actions=[],
            )

        return OcrTextResult(
            screenshot_path=str(path),
            screenshot_exists=True,
            observed_text=text,
            confidence="medium",
            engine="pytesseract",
            limitations=[],
            metadata={"character_count": len(text)},
            executable_actions=[],
        )
