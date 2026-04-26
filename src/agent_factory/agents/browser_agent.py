from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..pattern_memory import PatternMemory
from ..schemas import RecommendedAction, ScreenObservation, UserTask
from ..tools.playwright_executor import PlaywrightDemoExecutor


GPU_APP_NAME = "GPU Deal Evaluator"


class BrowserAgent:
    """Browser agent for safe local demo workflows.

    v0.2 adds a local GPU Deal Evaluator form. Real external websites remain blocked.
    """

    def __init__(self, pattern_memory: PatternMemory | None = None) -> None:
        self.pattern_memory = pattern_memory or PatternMemory()

    def plan(self, task: UserTask, run_id: str | None = None) -> tuple[ScreenObservation, list[RecommendedAction]]:
        text = task.text.lower()
        if any(k in text for k in ["gpu", "rtx", "3090", "4090", "5090", "listing", "deal"]):
            return self._plan_gpu_deal(task, run_id=run_id)
        return self._plan_generic_browser(task)

    def _plan_gpu_deal(self, task: UserTask, run_id: str | None = None) -> tuple[ScreenObservation, list[RecommendedAction]]:
        patterns = self.pattern_memory.relevant_patterns(task.text)
        if run_id:
            self.pattern_memory.log_usage(run_id, patterns)
        values = self._extract_gpu_deal_values(task.text, patterns=patterns)
        observation = ScreenObservation(
            screen_type="Local GPU Deal Evaluator form",
            app_name=GPU_APP_NAME,
            visible_fields=list(values.keys()),
            notes=[
                "v0.2 local demo form only.",
                "No seller contact, no purchase, no external website submission.",
                "Submit/send remains approval-gated and is not executed by the demo executor.",
                *[f"Pattern applied: {pattern.title}" for pattern in patterns],
            ],
            confidence="medium",
        )
        actions: list[RecommendedAction] = [
            RecommendedAction(
                action_type="suggest_values",
                description="Evaluate listing details and generate safe recommendation fields.",
                app_name=GPU_APP_NAME,
                risk_level="low",
            )
        ]
        for field_name, value in values.items():
            actions.append(
                RecommendedAction(
                    action_type="fill_field",
                    description=f"Fill local GPU Deal Evaluator field: {field_name}.",
                    app_name=GPU_APP_NAME,
                    field_name=field_name,
                    value=value,
                    risk_level="medium" if field_name in {"Draft message", "Final action"} else "low",
                    reversible=True,
                )
            )
        actions.append(
            RecommendedAction(
                action_type="submit_form",
                description="Submit the local GPU Deal Evaluator form. Blocked from execution in v0.2; approval required.",
                app_name=GPU_APP_NAME,
                field_name="Submit",
                risk_level="high",
                reversible=False,
            )
        )
        return observation, actions

    def _plan_generic_browser(self, task: UserTask) -> tuple[ScreenObservation, list[RecommendedAction]]:
        observation = ScreenObservation(
            screen_type="Browser research or form workflow, inferred",
            app_name="Browser",
            visible_fields=["Search", "Message draft"],
            notes=["External browser execution is not enabled in v0.2. Use local demo forms only."],
            confidence="medium",
        )
        actions = [
            RecommendedAction(
                action_type="suggest_values",
                description="Create a browser research plan and identify likely sources.",
                app_name="Browser",
                field_name="Search",
                risk_level="low",
            ),
            RecommendedAction(
                action_type="fill_field",
                description="Fill a search box in demo/assisted mode only.",
                app_name="Browser",
                field_name="Search",
                value=task.text,
                risk_level="medium",
            ),
            RecommendedAction(
                action_type="send_message",
                description="Send or submit a browser message. Must stop for approval.",
                app_name="Browser",
                field_name="Message draft",
                risk_level="high",
                reversible=False,
            ),
        ]
        return observation, actions

    def execute_gpu_demo_form(
        self,
        actions: list[RecommendedAction],
        project_root: Path | None = None,
    ) -> dict[str, Any]:
        field_values = {
            action.field_name: action.value
            for action in actions
            if action.action_type == "fill_field"
            and action.app_name == GPU_APP_NAME
            and action.field_name is not None
        }
        executor = PlaywrightDemoExecutor(project_root=project_root)
        return executor.fill_gpu_deal_form(field_values)

    def _extract_gpu_deal_values(self, text: str, patterns: list[Any] | None = None) -> dict[str, str]:
        patterns = patterns or []
        lower = text.lower()
        product_match = re.search(r"rtx\s*(30[0-9]0|40[0-9]0|50[0-9]0|3090|4090|5090)", lower)
        product = f"RTX {product_match.group(1)}".upper().replace("RTX ", "RTX ") if product_match else "GPU listing"

        vram_match = re.search(r"(\d+)\s*(gb|gib)\s*(vram)?", lower)
        vram = f"{vram_match.group(1)} GB" if vram_match else "Unknown"

        price_match = re.search(r"(?:\$|price is\s*)(\d{2,5})", lower)
        price = f"${price_match.group(1)}" if price_match else "Unknown"

        condition = "Used" if "used" in lower else "Unknown"
        missing_proof_items = []
        if "benchmark" in lower and any(k in lower for k in ["not", "no", "has not", "without"]):
            missing_proof_items.append("Benchmarks or stress-test results not provided")
        if "local pickup" in lower:
            missing_proof_items.append("Need in-person verification before payment")
        if not missing_proof_items:
            missing_proof_items.append("Ask for timestamped photos, GPU-Z screenshot, and benchmark/stress-test video")

        red_flags = [
            "No benchmark/stress-test proof yet",
            "Need timestamped photos with seller name/date",
            "Need to verify ports, fan noise, temperatures, and artifact-free output",
            "Avoid deposits, shipping pressure, or off-platform payment requests",
        ]
        for pattern in patterns:
            if pattern.title not in red_flags:
                red_flags.append(pattern.title)

        offer = self._recommended_offer(price)
        if any("discount" in pattern.title.lower() or "proof" in pattern.description.lower() for pattern in patterns):
            offer = f"{offer} if proof is missing"
        draft_message = (
            "Hi, is the card still available? Before I come out, could you send a timestamped photo, "
            "a GPU-Z screenshot, and a short video of a benchmark or stress test running with temps visible? "
            f"If everything checks out, would you consider {offer}?"
        )
        if any("draft" in pattern.title.lower() for pattern in patterns):
            draft_message = f"Draft only - do not send: {draft_message}"

        return {
            "Product": product,
            "VRAM": vram,
            "Price": price,
            "Condition": condition,
            "Missing proof": "; ".join(missing_proof_items),
            "Red flags": "; ".join(red_flags),
            "Recommended offer": offer,
            "Draft message": draft_message,
            "Final action": "Apply approved GPU deal patterns. Do not send message or buy until proof is reviewed and human approval is given.",
        }

    def _recommended_offer(self, price: str) -> str:
        if price.startswith("$") and price[1:].isdigit():
            amount = int(price[1:])
            low = max(amount - 100, 0)
            high = max(amount - 50, low)
            return f"${low}-${high}"
        return "Request proof first, then negotiate below asking price"
