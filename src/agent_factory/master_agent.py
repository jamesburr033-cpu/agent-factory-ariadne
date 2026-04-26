from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .agents.browser_agent import BrowserAgent
from .agents.browser_research_agent import BrowserResearchAgent
from .agents.screen_advisor_agent import ScreenAdvisorAgent
from .agents.self_improvement_agent import SelfImprovementAgent
from .agents.tron import TronCriticAgent
from .action_queue import ActionQueue
from .approvals import ApprovalGate
from .audit_log import JsonlAuditLog
from .pattern_memory import PatternMemory
from .registry import AgentRegistry
from .router import TaskRouter
from .schemas import AgentRunLog, CriticReview, ScreenObservation, UserTask


class AriadneMasterAgent:
    """Ariadne, the Master Agent orchestrator."""

    def __init__(self) -> None:
        self.registry = AgentRegistry()
        self.router = TaskRouter()
        self.approvals = ApprovalGate()
        self.audit_log = JsonlAuditLog()
        self.pattern_memory = PatternMemory()
        self.screen_advisor = ScreenAdvisorAgent()
        self.browser_agent = BrowserAgent(pattern_memory=self.pattern_memory)
        self.self_improvement_agent = SelfImprovementAgent()
        self.tron = TronCriticAgent()
        self.browser_research_agent = BrowserResearchAgent(tron=self.tron, pattern_memory=self.pattern_memory)
        self.action_queue = ActionQueue(tron=self.tron)

    def run(self, task: UserTask) -> AgentRunLog:
        run_id = str(uuid4())
        routing = self.router.route(task)
        observation: ScreenObservation | None = None
        actions = []
        improvement_proposals = []
        artifacts = {}

        research_url = self._extract_research_url(task)

        if routing.selected_agent == "screen_advisor_agent":
            observation, actions = self.screen_advisor.analyze(task)
        elif routing.selected_agent == "browser_agent":
            if research_url:
                research_run = self.browser_research_agent.research_url(
                    research_url,
                    run_id=run_id,
                    visible_text=task.metadata.get("visible_text"),
                    screenshot_path=task.metadata.get("screenshot_path"),
                )
                artifacts["browser_research"] = research_run.model_dump(mode="json")
                if research_run.allowed and research_run.listing:
                    observation = ScreenObservation(
                        screen_type="Read-only browser research",
                        app_name="Browser Research Sandbox",
                        visible_fields=[
                            field
                            for field, value in research_run.listing.model_dump(mode="json").items()
                            if value
                        ],
                        notes=[
                            "Read-only approved-domain research.",
                            "No login, contact, purchase, form submission, or work-system access.",
                        ],
                        confidence="medium",
                    )
                    actions = research_run.proposed_actions
                    critic_review_override = research_run.tron_review
                else:
                    observation = ScreenObservation(
                        screen_type="Blocked browser research",
                        app_name="Browser Research Sandbox",
                        notes=[research_run.blocked_reason or "Browser research blocked."],
                        confidence="high",
                    )
                    actions = []
            else:
                observation, actions = self.browser_agent.plan(task, run_id=run_id)
        elif routing.selected_agent == "self_improvement_agent":
            improvement_proposals = self.self_improvement_agent.propose(task)
            observation = ScreenObservation(
                screen_type="Self-improvement review",
                app_name="Ariadne",
                notes=["Proposal-only. No code/config changes applied."],
                confidence="medium",
            )
        elif routing.selected_agent == "windows_app_agent":
            observation = ScreenObservation(
                screen_type="Windows app automation requested",
                app_name="Ariadne",
                notes=["Windows automation is disabled in v0.2. Advisor mode only."],
                confidence="medium",
            )
        else:
            observation = ScreenObservation(
                screen_type="General strategy request",
                app_name="Ariadne",
                notes=["No tool execution required."],
                confidence="low",
            )

        decisions = self.approvals.evaluate_many(actions, mode=task.mode)
        critic_review = locals().get("critic_review_override") or self.tron.review(routing, actions, decisions)

        execute_demo_form = bool(task.metadata.get("execute_demo_form", False))
        has_blocked_actions = any(not decision.allowed for decision in decisions)
        if execute_demo_form:
            if task.mode not in {"assisted_fill", "demo"}:
                artifacts["browser_demo"] = {
                    "executed": False,
                    "reason": "Demo form execution requires assisted_fill or demo mode.",
                }
            elif has_blocked_actions:
                artifacts["browser_demo"] = {
                    "executed": False,
                    "reason": "One or more approval decisions were blocked.",
                }
            elif routing.selected_agent != "browser_agent":
                artifacts["browser_demo"] = {
                    "executed": False,
                    "reason": "Demo form execution only runs for browser_agent tasks.",
                }
            else:
                # This executor only fills the local GPU Deal Evaluator form and never clicks submit.
                try:
                    artifacts["browser_demo"] = self.browser_agent.execute_gpu_demo_form(actions, project_root=Path.cwd())
                except Exception as exc:
                    artifacts["browser_demo"] = {
                        "executed": False,
                        "reason": str(exc),
                    }

        if improvement_proposals and not actions:
            critic_review = CriticReview(
                critic_name="Tron",
                summary="Self-improvement proposals generated. No changes applied.",
                risks=["Self-improvement changes require branch, tests, Tron review, and human approval."],
                required_approvals=["modify_code", "change_approval_rules"],
                blocked=False,
                confidence="high",
            )

        run_log = AgentRunLog(
            run_id=run_id,
            task=task,
            routing=routing,
            screen_observation=observation,
            recommended_actions=actions,
            approval_decisions=decisions,
            critic_review=critic_review,
            improvement_proposals=improvement_proposals,
            artifacts=artifacts,
        )
        self.audit_log.append(run_log)
        if actions:
            self.action_queue.enqueue_run_actions(run_log)
        return run_log

    def _extract_research_url(self, task: UserTask) -> str | None:
        if task.metadata.get("research_url"):
            return str(task.metadata["research_url"])
        for token in task.text.split():
            if token.startswith(("http://", "https://")):
                return token.rstrip(".,)")
        return None
