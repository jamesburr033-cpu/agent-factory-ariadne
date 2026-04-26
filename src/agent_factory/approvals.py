from __future__ import annotations

from .config_loader import config_path, load_yaml
from .schemas import ApprovalDecision, RecommendedAction


class ApprovalGate:
    def __init__(self) -> None:
        self.rules = load_yaml(config_path("approval_rules.yaml"))
        self.app_allowlist = load_yaml(config_path("app_allowlist.yaml"))
        self.field_allowlist = load_yaml(config_path("field_allowlist.yaml"))

    def evaluate(self, action: RecommendedAction, mode: str = "advisor") -> ApprovalDecision:
        action_rules = self.rules.get("actions", {})
        rule = action_rules.get(action.action_type)
        if rule is None:
            return ApprovalDecision(
                action=action,
                allowed=False,
                approval_required=True,
                blocked_reason=f"Unknown action type: {action.action_type}",
                status="blocked",
            )

        allowed = bool(rule.get("allowed", False))
        approval_required = bool(rule.get("approval_required", True))
        failed: list[str] = []

        for condition in rule.get("conditions", []) or []:
            if not self._condition_passes(condition, action, mode):
                failed.append(condition)

        if failed:
            return ApprovalDecision(
                action=action,
                allowed=False,
                approval_required=True,
                blocked_reason="Approval rule conditions failed.",
                conditions_failed=failed,
                status="blocked",
            )

        status = "allowed"
        if not allowed:
            status = "blocked"
        elif approval_required:
            status = "requires_approval_before_execution"

        return ApprovalDecision(
            action=action,
            allowed=allowed,
            approval_required=approval_required,
            blocked_reason=None if allowed else "Action is blocked by rule.",
            status=status,
        )

    def evaluate_many(self, actions: list[RecommendedAction], mode: str = "advisor") -> list[ApprovalDecision]:
        return [self.evaluate(action, mode=mode) for action in actions]

    def _condition_passes(self, condition: str, action: RecommendedAction, mode: str) -> bool:
        if condition == "app_is_allowlisted":
            return self._app_is_allowlisted(action.app_name, mode)
        if condition == "field_is_allowlisted":
            return self._field_is_allowlisted(action.app_name, action.field_name)
        if condition == "mode_is_assisted_fill_or_demo":
            return mode in {"assisted_fill", "demo"}
        if condition == "button_is_non_consequential":
            return action.risk_level in {"low", "medium"} and action.reversible
        return False

    def _app_is_allowlisted(self, app_name: str | None, mode: str) -> bool:
        if not app_name:
            return False
        app_name_lower = app_name.lower()
        for app in self.app_allowlist.get("apps", []) or []:
            names = [app.get("name", ""), *(app.get("aliases", []) or [])]
            if app_name_lower in {name.lower() for name in names}:
                return mode in set(app.get("modes_allowed", []) or [])
        return False

    def _field_is_allowlisted(self, app_name: str | None, field_name: str | None) -> bool:
        if not app_name or not field_name:
            return False
        fields_by_app = self.field_allowlist.get("fields", {}) or {}
        allowed_fields = fields_by_app.get(app_name, [])
        return field_name in allowed_fields
