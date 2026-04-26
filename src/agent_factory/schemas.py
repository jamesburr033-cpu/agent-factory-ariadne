from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


TaskType = Literal[
    "screen_advice",
    "form_fill",
    "browser_research",
    "desktop_automation",
    "self_improvement",
    "epic_build_advice",
    "general_strategy",
]

RiskLevel = Literal["low", "medium", "high", "critical"]
ApprovalStatus = Literal["allowed", "requires_approval_before_execution", "blocked"]
ActionApprovalState = Literal["pending", "approved", "rejected", "needs_revision"]
ActionExecutionState = Literal["not_executed", "executed", "blocked", "failed"]
PatternSource = Literal["seed", "lesson", "manual"]
PatternConfidence = Literal["low", "medium", "high"]


class UserTask(BaseModel):
    text: str
    mode: Literal["advisor", "assisted_fill", "demo"] = "advisor"
    screenshot_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentDefinition(BaseModel):
    name: str
    display_name: str | None = None
    purpose: str
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    requires_approval_for: list[str] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    task_type: TaskType
    selected_agent: str
    reason: str
    confidence: Literal["low", "medium", "high"] = "medium"
    missing_inputs: list[str] = Field(default_factory=list)


class ScreenObservation(BaseModel):
    screen_type: str
    app_name: str
    visible_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class RecommendedAction(BaseModel):
    action_type: str
    description: str
    app_name: str | None = None
    field_name: str | None = None
    value: str | None = None
    risk_level: RiskLevel = "low"
    reversible: bool = True


class ApprovalDecision(BaseModel):
    action: RecommendedAction
    allowed: bool
    approval_required: bool
    blocked_reason: str | None = None
    conditions_failed: list[str] = Field(default_factory=list)
    status: ApprovalStatus = "allowed"


class CriticReview(BaseModel):
    critic_name: str = "Tron"
    summary: str
    risks: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    blocked: bool = False
    confidence: Literal["low", "medium", "high"] = "medium"


class ImprovementProposal(BaseModel):
    title: str
    problem_observed: str
    proposed_change: str
    files_or_configs_to_change: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True
    may_apply_directly: bool = False


class AgentRunLog(BaseModel):
    run_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    machine_name: str = "Ariadne"
    task: UserTask
    routing: RoutingDecision
    screen_observation: ScreenObservation | None = None
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    approval_decisions: list[ApprovalDecision] = Field(default_factory=list)
    critic_review: CriticReview
    improvement_proposals: list[ImprovementProposal] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)

    @property
    def requires_human_approval(self) -> bool:
        return any(d.approval_required for d in self.approval_decisions)

    @property
    def blocked(self) -> bool:
        return self.critic_review.blocked or any(not d.allowed for d in self.approval_decisions)


class QueuedAction(BaseModel):
    action_id: str
    run_id: str
    action: RecommendedAction


class ActionQueueRecord(BaseModel):
    action_id: str
    run_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: RecommendedAction
    approval_status: ActionApprovalState = "pending"
    execution_status: ActionExecutionState = "not_executed"
    reviewer: str | None = None
    review_notes: str = ""
    execution_result: dict[str, Any] = Field(default_factory=dict)


class BrowserResearchListing(BaseModel):
    title: str | None = None
    price: str | None = None
    location: str | None = None
    condition: str | None = None
    seller_notes: str | None = None
    listing_url: str
    red_flags: list[str] = Field(default_factory=list)
    recommended_next_step: str


class BrowserResearchRun(BaseModel):
    research_id: str
    run_id: str | None = None
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    url: str
    domain: str
    allowed: bool
    blocked_reason: str | None = None
    read_only: bool = True
    listing: BrowserResearchListing | None = None
    visible_text_excerpt: str = ""
    screenshot_path: str | None = None
    tron_review: CriticReview | None = None
    proposed_actions: list[RecommendedAction] = Field(default_factory=list)


class WorkflowPattern(BaseModel):
    pattern_id: str
    title: str
    description: str
    keywords: list[str] = Field(default_factory=list)
    source: PatternSource = "manual"
    confidence: PatternConfidence = "medium"
    active: bool = True
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "James"
    source_lesson_id: str | None = None
    safety_note: str = "Pattern informs recommendations only and does not authorize sending, buying, submitting, deleting, credential, or production actions."


def normalize_path(path: str | None) -> Path | None:
    if not path:
        return None
    return Path(path).expanduser().resolve()


from dataclasses import dataclass as _ariadne_dataclass
from typing import Optional as _AriadneOptional


@_ariadne_dataclass
class ScreenObservationArtifact:
    screenshot_path: _AriadneOptional[str]
    timestamp_utc: str
    machine_name: str
    width: _AriadneOptional[int]
    height: _AriadneOptional[int]
    active_window_title: _AriadneOptional[str]
    process_name: _AriadneOptional[str]
    app_name: _AriadneOptional[str]
    blocked_or_limited: bool
    tron_safety_review: str
    recommended_observations: list[str]
    executable_actions: list[dict[str, str]]
    active_window_left: _AriadneOptional[int] = None
    active_window_top: _AriadneOptional[int] = None
    active_window_right: _AriadneOptional[int] = None
    active_window_bottom: _AriadneOptional[int] = None

    def to_dict(self) -> dict:
        return {
            "screenshot_path": self.screenshot_path,
            "timestamp_utc": self.timestamp_utc,
            "machine_name": self.machine_name,
            "width": self.width,
            "height": self.height,
            "active_window_title": self.active_window_title,
            "process_name": self.process_name,
            "app_name": self.app_name,
            "active_window_left": self.active_window_left,
            "active_window_top": self.active_window_top,
            "active_window_right": self.active_window_right,
            "active_window_bottom": self.active_window_bottom,
            "blocked_or_limited": self.blocked_or_limited,
            "tron_safety_review": self.tron_safety_review,
            "recommended_observations": self.recommended_observations,
            "executable_actions": self.executable_actions,
        }
