from __future__ import annotations

from typing import Any

from ..schemas import ApprovalDecision, BrowserResearchListing, CriticReview, RecommendedAction, RoutingDecision


NEVER_EXECUTE_ACTION_TYPES = {
    "submit_form",
    "contact_seller",
    "send_message",
    "bid",
    "buy_now",
    "save_record",
    "delete_data",
    "purchase_item",
    "credential_access",
    "enter_credentials",
    "deploy",
    "production_change",
    "production_epic_change",
}


class TronCriticAgent:
    """Critic and safety review agent."""

    name = "Tron"

    def review(
        self,
        routing: RoutingDecision,
        actions: list[RecommendedAction],
        decisions: list[ApprovalDecision],
    ) -> CriticReview:
        risks: list[str] = []
        required_approvals: list[str] = []

        for decision in decisions:
            action = decision.action
            if decision.approval_required:
                required_approvals.append(action.action_type)
            if not decision.allowed:
                risks.append(
                    f"Blocked or disallowed action: {action.action_type}. Reason: {decision.blocked_reason or 'unspecified'}"
                )
            elif action.risk_level in {"high", "critical"}:
                risks.append(f"High-risk action present: {action.action_type}")

        if routing.task_type == "epic_build_advice":
            risks.append("Epic guidance requires approved documentation and should remain advisory unless explicitly in sandbox/governed workflow.")

        blocked = any(not d.allowed for d in decisions)
        confidence = "high" if not risks else "medium"

        summary = "Action plan is reviewable."
        if blocked:
            summary = "One or more actions are blocked by safety rules."
        elif required_approvals:
            summary = "Action plan contains steps that require human approval before execution."

        return CriticReview(
            critic_name=self.name,
            summary=summary,
            risks=risks,
            required_approvals=sorted(set(required_approvals)),
            blocked=blocked,
            confidence=confidence,
        )

    def final_action_check(self, action: RecommendedAction) -> ApprovalDecision:
        if action.action_type in NEVER_EXECUTE_ACTION_TYPES:
            return ApprovalDecision(
                action=action,
                allowed=False,
                approval_required=True,
                blocked_reason=f"{action.action_type} must never execute in v0.4.",
                status="blocked",
            )
        if action.risk_level in {"high", "critical"}:
            return ApprovalDecision(
                action=action,
                allowed=False,
                approval_required=True,
                blocked_reason="High-risk actions remain blocked from queue execution in v0.4.",
                status="blocked",
            )
        return ApprovalDecision(action=action, allowed=True, approval_required=False, status="allowed")

    def review_listing(self, listing: BrowserResearchListing, patterns: list[Any] | None = None) -> CriticReview:
        risks: list[str] = []
        required_approvals = ["send_message", "purchase_item"]

        if listing.red_flags:
            risks.extend(listing.red_flags)
        notes = (listing.seller_notes or "").lower()
        if not any(token in notes for token in ["benchmark", "gpu-z", "stress", "receipt", "timestamp"]):
            risks.append("Missing proof: ask for timestamped photos, GPU-Z screenshot, and benchmark or stress-test evidence.")
        if listing.price is None:
            risks.append("Price reasonableness cannot be checked because price was not visible.")
        elif any(token in listing.price.lower() for token in ["free", "$0"]):
            risks.append("Scam risk: price appears unusually low.")
        for pattern in patterns or []:
            risks.append(f"Approved pattern context: {pattern.title}")

        summary = "Read-only listing review complete. Contact or purchase requires human approval."
        return CriticReview(
            critic_name=self.name,
            summary=summary,
            risks=risks,
            required_approvals=sorted(set(required_approvals)),
            blocked=False,
            confidence="medium" if risks else "high",
        )
