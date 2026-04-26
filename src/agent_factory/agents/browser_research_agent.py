from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from ..audit_log import JsonlAuditLog
from ..config_loader import MEMORY_DIR, config_path, load_yaml
from ..pattern_memory import PatternMemory
from ..schemas import BrowserResearchListing, BrowserResearchRun, RecommendedAction
from .tron import TronCriticAgent


NEVER_CLICK_OR_SUBMIT_TERMS = {
    "buy",
    "bid",
    "contact",
    "send",
    "message",
    "checkout",
    "submit",
    "login",
    "log in",
    "sign in",
}

NAVIGATION_TEXT_PATTERNS = (
    "skip to main content",
    "sign in",
    "register",
    "daily deals",
    "brand outlet",
    "help & contact",
    "sell",
    "watchlist",
    "expand cart",
    "shop by category",
    "all categories",
    "breadcrumb",
    "footer",
    "header",
    "navigation",
    "privacy",
    "terms",
    "copyright",
    "sponsored",
)


class BrowserResearchAgent:
    """Read-only browser research for approved non-work listing pages."""

    def __init__(
        self,
        tron: TronCriticAgent | None = None,
        audit_log: JsonlAuditLog | None = None,
        pattern_memory: PatternMemory | None = None,
    ) -> None:
        self.tron = tron or TronCriticAgent()
        self.audit_log = audit_log or JsonlAuditLog("browser_research_runs.jsonl")
        self.pattern_memory = pattern_memory or PatternMemory()
        self.allowlist = load_yaml(config_path("browser_allowlist.yaml"))
        self.screenshot_dir = MEMORY_DIR / "browser_research_screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def research_url(
        self,
        url: str,
        run_id: str | None = None,
        visible_text: str | None = None,
        screenshot_path: str | None = None,
    ) -> BrowserResearchRun:
        domain = self.domain_for_url(url)
        allowed, blocked_reason = self.is_allowed_url(url)
        if not allowed:
            result = BrowserResearchRun(
                research_id=str(uuid4()),
                run_id=run_id,
                url=url,
                domain=domain,
                allowed=False,
                blocked_reason=blocked_reason,
            )
            self.audit_log.append(result)
            return result

        page_text = visible_text
        captured_screenshot = screenshot_path
        if page_text is None:
            page_text, captured_screenshot = self._read_visible_text_with_playwright(url)

        patterns = self.pattern_memory.relevant_patterns(f"{url} {page_text or ''}")
        if run_id:
            self.pattern_memory.log_usage(run_id, patterns)
        listing = self.extract_listing(page_text or "", url, patterns=patterns)
        tron_review = self.tron.review_listing(listing, patterns=patterns)
        proposed_actions = self.proposed_actions_for_listing(listing, patterns=patterns)
        result = BrowserResearchRun(
            research_id=str(uuid4()),
            run_id=run_id,
            url=url,
            domain=domain,
            allowed=True,
            listing=listing,
            visible_text_excerpt=(page_text or "")[:1000],
            screenshot_path=captured_screenshot,
            tron_review=tron_review,
            proposed_actions=proposed_actions,
        )
        self.audit_log.append(result)
        return result

    def is_allowed_url(self, url: str) -> tuple[bool, str | None]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False, "Only http and https URLs are allowed for read-only browser research."
        domain = self.domain_for_url(url)
        if self._domain_in_config(domain, "domains"):
            return True, None
        if self._domain_in_config(domain, "restricted_domains"):
            return True, "Restricted read-only domain. Continue only if accessible without login."
        return False, f"Domain is not allowlisted for browser research: {domain}"

    def domain_for_url(self, url: str) -> str:
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host

    def extract_listing(
        self,
        visible_text: str,
        url: str,
        patterns: list[Any] | None = None,
    ) -> BrowserResearchListing:
        patterns = patterns or []
        lines = self._content_lines(visible_text)
        text = "\n".join(lines)
        title = self._first_likely_title(lines)
        price = self._first_match(text, r"(?<!\w)\$\s?\d[\d,]*(?:\.\d{2})?")
        location = self._field_value(lines, "location")
        condition = self._field_value(lines, "condition") or self._condition_from_text(text)
        seller_notes = self._notes_from_lines(lines)
        red_flags = self._red_flags(text)
        for pattern in patterns:
            if pattern.title not in red_flags:
                red_flags.append(pattern.title)
        recommended = self._recommended_next_step(red_flags, seller_notes, patterns=patterns)
        return BrowserResearchListing(
            title=title,
            price=price,
            location=location,
            condition=condition,
            seller_notes=seller_notes,
            listing_url=url,
            red_flags=red_flags,
            recommended_next_step=recommended,
        )

    def proposed_actions_for_listing(
        self,
        listing: BrowserResearchListing,
        patterns: list[Any] | None = None,
    ) -> list[RecommendedAction]:
        patterns = patterns or []
        draft = (
            "Draft only - do not send: Hi, is this GPU still available? Could you share timestamped photos, "
            "a GPU-Z screenshot, and a benchmark or stress-test video with temperatures visible?"
        )
        if patterns:
            draft += " I am also checking this against my saved GPU buying checklist."
        return [
            RecommendedAction(
                action_type="send_message",
                description="Draft seller message for human review only. Do not send.",
                app_name="Browser Research Sandbox",
                field_name="Draft seller message",
                value=draft,
                risk_level="high",
                reversible=False,
            )
        ]

    def _domain_in_config(self, domain: str, key: str) -> bool:
        for row in self.allowlist.get(key, []) or []:
            allowed_domain = str(row.get("domain", "")).lower()
            if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                return True
        return False

    def _read_visible_text_with_playwright(self, url: str) -> tuple[str, str | None]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Playwright is required for live read-only research. Install browser support with: "
                'python -m pip install -e ".[browser]"'
            ) from exc

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        screenshot_path = self.screenshot_dir / f"browser_research_{stamp}.png"
        with sync_playwright() as p:  # pragma: no cover - live browser dependent
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1200})
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            text = page.locator("body").inner_text(timeout=5000)
            page.screenshot(path=str(screenshot_path), full_page=True)
            browser.close()
        return text, str(screenshot_path)

    def _first_likely_title(self, lines: list[str]) -> str | None:
        for line in lines:
            lowered = line.lower()
            if (
                len(line) > 8
                and not lowered.startswith(("price", "condition", "location", "$"))
                and not self._is_navigation_line(line)
            ):
                return line
        return lines[0] if lines else None

    def _first_match(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        return match.group(0).replace(" ", "") if match else None

    def _field_value(self, lines: list[str], field_name: str) -> str | None:
        prefix = f"{field_name}:"
        for line in lines:
            if line.lower().startswith(prefix):
                return line.split(":", 1)[1].strip()
        return None

    def _condition_from_text(self, text: str) -> str | None:
        lower = text.lower()
        for value in ("new", "used", "open box", "for parts"):
            if value in lower:
                return value.title()
        return None

    def _notes_from_lines(self, lines: list[str]) -> str | None:
        if not lines:
            return None
        return " ".join(lines[:12])

    def _content_lines(self, visible_text: str) -> list[str]:
        lines = [line.strip() for line in visible_text.splitlines() if line.strip()]
        return [line for line in lines if not self._is_navigation_line(line)]

    def _is_navigation_line(self, line: str) -> bool:
        lowered = " ".join(line.lower().split())
        if lowered in NAVIGATION_TEXT_PATTERNS:
            return True
        if any(pattern in lowered for pattern in NAVIGATION_TEXT_PATTERNS):
            return True
        if len(lowered) <= 3:
            return True
        return False

    def _red_flags(self, text: str) -> list[str]:
        lower = text.lower()
        red_flags: list[str] = []
        if not any(term in lower for term in ["benchmark", "gpu-z", "stress test", "receipt", "timestamp"]):
            red_flags.append("Missing benchmark, GPU-Z, receipt, or timestamped proof.")
        if any(term in lower for term in ["deposit", "wire", "gift card", "ship only", "cashapp", "zelle"]):
            red_flags.append("Payment or shipping language may be risky.")
        if any(term in lower for term in ["no returns", "as-is", "for parts"]):
            red_flags.append("Listing includes as-is/no-return language.")
        if any(term in lower for term in NEVER_CLICK_OR_SUBMIT_TERMS):
            red_flags.append("Page contains contact/buy/login terms; Ariadne must remain read-only.")
        return red_flags

    def _recommended_next_step(self, red_flags: list[str], seller_notes: str | None, patterns: list[Any] | None = None) -> str:
        pattern_titles = [pattern.title for pattern in patterns or []]
        if red_flags:
            return (
                "Do not contact or buy. Save a draft question for human review and request proof only after approval. "
                f"Relevant approved patterns: {', '.join(pattern_titles)}"
                if pattern_titles
                else "Do not contact or buy. Save a draft question for human review and request proof only after approval."
            )
        if seller_notes:
            return "Prepare a draft proof-request message for human review. Do not send."
        return "No action beyond review."
