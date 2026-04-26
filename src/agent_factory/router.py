from __future__ import annotations

from .schemas import RoutingDecision, UserTask


URL_MARKERS = ("http://", "https://")
BROWSER_RESEARCH_HINTS = (
    "research",
    "read-only",
    "read only",
    "browser research",
    "listing",
    "gpu listing",
    "ebay",
    "craigslist",
    "offerup",
    "amazon",
)
FORM_FILL_HINTS = ("servicenow", "snow", "ticket", "form", "field", "fill")
NEGATIVE_FORM_PHRASES = (
    "do not submit form",
    "do not submit forms",
    "don't submit form",
    "don't submit forms",
    "no form submission",
    "no form submissions",
    "must not submit form",
    "must not submit forms",
)


class TaskRouter:
    def route(self, task: UserTask) -> RoutingDecision:
        text = task.text.lower()
        missing_inputs: list[str] = []

        has_url = any(marker in text for marker in URL_MARKERS)
        if has_url and any(hint in text for hint in BROWSER_RESEARCH_HINTS):
            return RoutingDecision(
                task_type="browser_research",
                selected_agent="browser_agent",
                reason="Task contains a URL and read-only/listing research hints. Route to browser research before form-fill handling.",
                confidence="high",
                missing_inputs=missing_inputs,
            )

        form_text = text
        for phrase in NEGATIVE_FORM_PHRASES:
            form_text = form_text.replace(phrase, "")
        if any(k in form_text for k in FORM_FILL_HINTS):
            return RoutingDecision(
                task_type="form_fill",
                selected_agent="screen_advisor_agent",
                reason="Task mentions form/ticket/field filling, so start in safe screen-advisor mode.",
                confidence="high",
                missing_inputs=missing_inputs,
            )

        if any(k in text for k in ["gpu", "listing", "search", "browser", "web", "deal", "price", "http://", "https://"]):
            return RoutingDecision(
                task_type="browser_research",
                selected_agent="browser_agent",
                reason="Task appears to require browser research or listing comparison.",
                confidence="medium",
                missing_inputs=missing_inputs,
            )

        if any(k in text for k in ["epic", "hyperspace", "ini", "build", "change ticket"]):
            missing_inputs.append("Relevant ticket text, screenshots, or approved reference docs if exact build steps are needed.")
            return RoutingDecision(
                task_type="epic_build_advice",
                selected_agent="screen_advisor_agent",
                reason="Task appears related to Epic build guidance. Use advisory mode unless approved sandbox context is provided.",
                confidence="medium",
                missing_inputs=missing_inputs,
            )

        if any(k in text for k in ["self improve", "improvement", "learn from", "failed", "failure"]):
            return RoutingDecision(
                task_type="self_improvement",
                selected_agent="self_improvement_agent",
                reason="Task asks for learning from failures or proposing improvements.",
                confidence="high",
                missing_inputs=missing_inputs,
            )

        if any(k in text for k in ["windows", "desktop", "click", "type", "app"]):
            return RoutingDecision(
                task_type="desktop_automation",
                selected_agent="windows_app_agent",
                reason="Task mentions Windows or desktop interaction. Keep disabled/advisory in v0.1.",
                confidence="medium",
                missing_inputs=missing_inputs,
            )

        return RoutingDecision(
            task_type="general_strategy",
            selected_agent="recommendation_agent",
            reason="No specialized route matched. Use recommendation strategy mode.",
            confidence="low",
            missing_inputs=missing_inputs,
        )
