"""Hard-coded deny-by-default policy for one local synthetic adapter.

This intentionally does not read agent-writable configuration files.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import ActionIntent


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    rule_id: str
    reason: str


class SyntheticOnlyPolicy:
    """No network, arbitrary filesystem paths, shell commands, or real messages."""

    version = "aa-001-synthetic-v1"
    _fields = frozenset({"feature_name", "owner", "status"})
    _deny_types = frozenset({"send_message", "purchase_item", "delete_data", "deploy", "submit_form", "credential_access", "production_change"})

    def evaluate(self, intent: ActionIntent) -> PolicyDecision:
        if intent.operation in self._deny_types:
            return PolicyDecision(False, "AA_DENY_PROHIBITED", "Prohibited action type")
        if (intent.tool_id, intent.operation, intent.target) != (
            "synthetic_fixture", "write_fixture_field", "healthcare_intake"
        ):
            return PolicyDecision(False, "AA_DENY_NOT_ALLOWLISTED", "Unknown tool, operation, or target")
        if set(intent.arguments) != {"field", "value"}:
            return PolicyDecision(False, "AA_DENY_ARGUMENTS", "Expected field and value only")
        if intent.arguments["field"] not in self._fields:
            return PolicyDecision(False, "AA_DENY_FIELD", "Field is not allowed")
        if not 1 <= len(intent.arguments["value"]) <= 128:
            return PolicyDecision(False, "AA_DENY_VALUE", "Value must be 1–128 characters")
        return PolicyDecision(True, "AA_ALLOW_SYNTHETIC", "Allowlisted local synthetic fixture update")
