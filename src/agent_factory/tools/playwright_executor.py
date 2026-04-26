from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIELD_ID_MAP = {
    "Product": "product",
    "VRAM": "vram",
    "Price": "price",
    "Condition": "condition",
    "Missing proof": "missing_proof",
    "Red flags": "red_flags",
    "Recommended offer": "recommended_offer",
    "Draft message": "draft_message",
    "Final action": "final_action",
}


class PlaywrightDemoExecutor:
    """Safely fills the local GPU Deal Evaluator HTML form.

    This executor is intentionally narrow:
    - It only opens a local file.
    - It only fills allowlisted fields passed in field_values.
    - It never clicks submit.
    - It saves before/after screenshots for auditability.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()
        self.form_path = (self.project_root / "examples" / "gpu_deal_form.html").resolve()
        self.screenshot_dir = (self.project_root / "memory" / "screenshots").resolve()
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def fill_gpu_deal_form(self, field_values: dict[str, str | None]) -> dict[str, Any]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover, environment dependent
            raise RuntimeError(
                "Playwright is not installed. Run: python -m pip install -e \".[browser]\" "
                "then: python -m playwright install chromium"
            ) from exc

        if not self.form_path.exists():
            raise FileNotFoundError(f"Demo form not found: {self.form_path}")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        before_path = self.screenshot_dir / f"gpu_deal_before_{stamp}.png"
        after_path = self.screenshot_dir / f"gpu_deal_after_{stamp}.png"
        form_url = self.form_path.as_uri()
        filled_fields: list[str] = []
        skipped_fields: list[str] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1200})
            page.goto(form_url)
            page.screenshot(path=str(before_path), full_page=True)

            for field_name, value in field_values.items():
                field_id = FIELD_ID_MAP.get(field_name)
                if not field_id:
                    skipped_fields.append(field_name)
                    continue
                page.fill(f"#{field_id}", value or "")
                filled_fields.append(field_name)

            # Hard safety rule: do not click submit in this executor.
            page.screenshot(path=str(after_path), full_page=True)
            browser.close()

        return {
            "executed": True,
            "executor": "PlaywrightDemoExecutor",
            "form_url": form_url,
            "filled_fields": filled_fields,
            "skipped_fields": skipped_fields,
            "submit_clicked": False,
            "before_screenshot": str(before_path),
            "after_screenshot": str(after_path),
        }
