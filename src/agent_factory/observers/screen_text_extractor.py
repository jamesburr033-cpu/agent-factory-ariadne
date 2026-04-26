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
    ocr_scope: str = "full_screen"
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    text_quality: dict[str, Any] = field(default_factory=dict)
    executable_actions: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OcrTextExtractor:
    """Read-only OCR extractor.

    This class does not click, type, submit, send, buy, delete, or control the screen.
    It only attempts to read text from an existing screenshot file.
    """

    def extract(
        self,
        screenshot_path: str,
        crop_box: Optional[dict[str, int]] = None,
    ) -> OcrTextResult:
        path = Path(screenshot_path)
        ocr_scope = "active_window_crop" if crop_box else "full_screen"

        if not path.exists():
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=False,
                observed_text=None,
                confidence="low",
                engine="none",
                ocr_scope=ocr_scope,
                limitations=["Screenshot file does not exist."],
                text_quality=self.score_text_quality(None),
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
                ocr_scope=ocr_scope,
                limitations=[
                    "OCR dependencies are not installed or not available.",
                    "Install Tesseract OCR and pytesseract to enable text extraction.",
                ],
                text_quality=self.score_text_quality(None),
                executable_actions=[],
            )

        try:
            image = Image.open(path)

            if crop_box:
                image = self._crop_image(image, crop_box)

            raw_text = pytesseract.image_to_string(image).strip()
        except Exception as exc:
            return OcrTextResult(
                screenshot_path=str(path),
                screenshot_exists=True,
                observed_text=None,
                confidence="low",
                engine="pytesseract",
                ocr_scope=ocr_scope,
                limitations=[f"OCR failed safely: {exc}"],
                text_quality=self.score_text_quality(None),
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
                ocr_scope=ocr_scope,
                limitations=["OCR ran but found no visible text."],
                text_quality=self.score_text_quality(None),
                executable_actions=[],
            )

        cleaned_text = self.clean_text(raw_text)
        text_quality = self.score_text_quality(cleaned_text)

        return OcrTextResult(
            screenshot_path=str(path),
            screenshot_exists=True,
            observed_text=cleaned_text,
            confidence=self._confidence_from_quality(text_quality),
            engine="pytesseract",
            raw_observed_text=raw_text,
            cleaned_observed_text=cleaned_text,
            ocr_scope=ocr_scope,
            limitations=[] if cleaned_text else ["OCR found text, but cleanup removed all usable content."],
            metadata={
                "character_count": len(raw_text),
                "cleaned_character_count": len(cleaned_text or ""),
                "line_count": len([line for line in raw_text.splitlines() if line.strip()]),
                "cleaned_line_count": len([line for line in (cleaned_text or "").splitlines() if line.strip()]),
                "crop_box": crop_box,
            },
            text_quality=text_quality,
            executable_actions=[],
        )

    def _crop_image(self, image: Any, crop_box: dict[str, int]) -> Any:
        left = max(0, int(crop_box["left"]))
        top = max(0, int(crop_box["top"]))
        right = min(image.width, int(crop_box["right"]))
        bottom = min(image.height, int(crop_box["bottom"]))

        if right <= left or bottom <= top:
            return image

        return image.crop((left, top, right, bottom))

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

    def score_text_quality(self, text: Optional[str]) -> dict[str, Any]:
        if not text:
            return {
                "score": 0.0,
                "rating": "unavailable",
                "warnings": ["No cleaned OCR text available."],
            }

        warnings: list[str] = []
        total_chars = len(text)
        alpha_chars = sum(char.isalpha() for char in text)
        digit_chars = sum(char.isdigit() for char in text)
        symbol_chars = sum(not char.isalnum() and not char.isspace() for char in text)
        lines = [line for line in text.splitlines() if line.strip()]
        alpha_ratio = alpha_chars / max(total_chars, 1)
        symbol_ratio = symbol_chars / max(total_chars, 1)

        score = 1.0

        if total_chars < 20:
            score -= 0.25
            warnings.append("Very short OCR text.")

        if alpha_ratio < 0.45:
            score -= 0.30
            warnings.append("Low alphabetic character ratio.")

        if symbol_ratio > 0.25:
            score -= 0.25
            warnings.append("High symbol noise ratio.")

        if any(token in text for token in ["\\", "|", "[]", "@@"]):
            score -= 0.15
            warnings.append("Possible OCR substitutions or UI noise detected.")

        if len(lines) > 25:
            score -= 0.10
            warnings.append("Large multi-line OCR output may include unrelated UI text.")

        if warnings:
            score = min(score, 0.79)

        score = round(max(0.0, min(1.0, score)), 2)

        if score >= 0.80:
            rating = "good"
        elif score >= 0.55:
            rating = "usable"
        elif score >= 0.30:
            rating = "noisy"
        else:
            rating = "poor"

        return {
            "score": score,
            "rating": rating,
            "warnings": warnings,
            "character_count": total_chars,
            "line_count": len(lines),
            "alpha_ratio": round(alpha_ratio, 2),
            "symbol_ratio": round(symbol_ratio, 2),
            "digit_count": digit_chars,
        }

    def _confidence_from_quality(self, text_quality: dict[str, Any]) -> str:
        rating = text_quality.get("rating")

        if rating == "good":
            return "high"
        if rating == "usable":
            return "medium"
        return "low"

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
