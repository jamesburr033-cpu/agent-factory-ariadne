from __future__ import annotations

import json
from pathlib import Path

from ..config_loader import MEMORY_DIR
from ..schemas import ImprovementProposal, UserTask


class SelfImprovementAgent:
    """Proposal-only self-improvement agent."""

    def propose(self, task: UserTask) -> list[ImprovementProposal]:
        failed_path = MEMORY_DIR / "failed_actions.jsonl"
        if not failed_path.exists():
            return [
                ImprovementProposal(
                    title="Create failure logging seed file",
                    problem_observed="No failed_actions.jsonl file exists yet, so Ariadne cannot identify repeated failures.",
                    proposed_change="Create a failure logging path and add a test that failed actions are recorded for later review.",
                    files_or_configs_to_change=["memory/failed_actions.jsonl", "tests/test_self_improvement_gate.py"],
                )
            ]

        failures = []
        with failed_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    failures.append(json.loads(line))

        if not failures:
            return []

        return [
            ImprovementProposal(
                title="Review repeated failed actions",
                problem_observed=f"Found {len(failures)} failed action log entries.",
                proposed_change="Group failures by action_type and add pre-checks/tests for the most common failure class.",
                files_or_configs_to_change=["src/agent_factory/approvals.py", "tests/test_approval_rules.py"],
            )
        ]
