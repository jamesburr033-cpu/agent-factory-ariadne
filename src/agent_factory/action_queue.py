from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from .agents.tron import NEVER_EXECUTE_ACTION_TYPES, TronCriticAgent
from .approvals import ApprovalGate
from .config_loader import MEMORY_DIR
from .schemas import ActionApprovalState, ActionQueueRecord, AgentRunLog, ApprovalDecision, RecommendedAction


ACTION_QUEUE_PATH = MEMORY_DIR / "action_queue.jsonl"
ACTION_QUEUE_EVENTS_PATH = MEMORY_DIR / "action_queue_events.jsonl"
EXECUTABLE_ACTION_TYPES = {"fill_field", "suggest_values"}
EXECUTABLE_RISK_LEVELS = {"low", "medium"}


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(f"Object is not JSON serializable: {type(value)!r}")


def append_jsonl(path: Path, item: dict[str, Any] | BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = item.model_dump(mode="json") if isinstance(item, BaseModel) else item
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL rows must be objects in {path} at line {line_number}")
            rows.append(payload)
    return rows


class ActionQueue:
    def __init__(
        self,
        queue_path: Path = ACTION_QUEUE_PATH,
        event_path: Path = ACTION_QUEUE_EVENTS_PATH,
        approval_gate: ApprovalGate | None = None,
        tron: TronCriticAgent | None = None,
    ) -> None:
        self.queue_path = queue_path
        self.event_path = event_path
        self.approval_gate = approval_gate or ApprovalGate()
        self.tron = tron or TronCriticAgent()

    def enqueue_run_actions(self, run: AgentRunLog) -> list[ActionQueueRecord]:
        records: list[ActionQueueRecord] = []
        for action in run.recommended_actions:
            record = ActionQueueRecord(
                action_id=str(uuid4()),
                run_id=run.run_id,
                action=action,
            )
            self._append_record(record)
            self._log_event(
                "queue_created",
                record,
                {"approval_status": record.approval_status, "execution_status": record.execution_status},
            )
            records.append(record)
        return records

    def list_records(self) -> list[ActionQueueRecord]:
        latest: dict[str, ActionQueueRecord] = {}
        for row in read_jsonl(self.queue_path):
            record = ActionQueueRecord.model_validate(row)
            latest[record.action_id] = record
        return list(latest.values())

    def list_records_for_run(self, run_id: str) -> list[ActionQueueRecord]:
        return [record for record in self.list_records() if record.run_id == run_id]

    def get_record(self, action_id: str) -> ActionQueueRecord:
        for record in self.list_records():
            if record.action_id == action_id:
                return record
        raise ValueError(f"Unknown queued action: {action_id}")

    def set_approval_status(
        self,
        action_id: str,
        approval_status: ActionApprovalState,
        reviewer: str = "James",
        notes: str = "",
    ) -> ActionQueueRecord:
        if approval_status not in {"approved", "rejected", "needs_revision", "pending"}:
            raise ValueError(f"Unsupported approval status: {approval_status}")
        record = self.get_record(action_id).model_copy(
            update={
                "timestamp_utc": datetime.now(timezone.utc),
                "approval_status": approval_status,
                "reviewer": reviewer,
                "review_notes": notes,
            }
        )
        self._append_record(record)
        self._log_event("approval_decision", record, {"approval_status": approval_status, "notes": notes})
        return record

    def execute_action(self, action_id: str, attempted_by: str = "James") -> ActionQueueRecord:
        record = self.get_record(action_id)
        self._log_event(
            "execution_attempt",
            record,
            {
                **self._execution_context(record),
                "attempted_by": attempted_by,
                "result": "attempted",
                "blocked_reason": None,
                "tron_final_check_result": None,
            },
        )

        allowed, reason, tron_decision = self._can_execute(record)
        if not allowed:
            result = {
                "executed": False,
                "result": "blocked",
                "blocked_reason": reason,
                "reason": reason,
                "attempted_by": attempted_by,
                "tron_final_check_result": self._tron_result(tron_decision),
            }
            updated = record.model_copy(
                update={
                    "timestamp_utc": datetime.now(timezone.utc),
                    "execution_status": "blocked",
                    "execution_result": result,
                }
            )
            self._append_record(updated)
            self._log_event("execution_result", updated, result)
            return updated

        result = {
            "executed": True,
            "result": "executed",
            "blocked_reason": None,
            "attempted_by": attempted_by,
            "tron_final_check_result": self._tron_result(tron_decision),
            "mode": "local_demo_queue",
            "action_type": record.action.action_type,
            "app_name": record.action.app_name,
            "field_name": record.action.field_name,
            "value": record.action.value,
            "safety_note": "v0.4 queue execution records approved local demo fill/suggest actions only; it does not submit, send, save, delete, purchase, access credentials, deploy, or touch production.",
        }
        updated = record.model_copy(
            update={
                "timestamp_utc": datetime.now(timezone.utc),
                "execution_status": "executed",
                "execution_result": result,
            }
        )
        self._append_record(updated)
        self._log_event("execution_result", updated, result)
        return updated

    def can_execute(self, record: ActionQueueRecord) -> tuple[bool, str]:
        allowed, reason, _ = self._can_execute(record, run_tron=False)
        return allowed, reason

    def _can_execute(
        self,
        record: ActionQueueRecord,
        run_tron: bool = True,
    ) -> tuple[bool, str, ApprovalDecision | None]:
        action = record.action
        if record.approval_status != "approved":
            return False, "Action must be explicitly approved before execution.", None
        if record.execution_status != "not_executed":
            return False, f"Action execution status is {record.execution_status}.", None
        if action.action_type in NEVER_EXECUTE_ACTION_TYPES:
            return False, f"{action.action_type} must never execute in v0.6.1.", None
        if action.action_type not in EXECUTABLE_ACTION_TYPES:
            return False, f"{action.action_type} is not executable by the v0.6.1 local demo queue.", None
        if action.risk_level not in EXECUTABLE_RISK_LEVELS:
            return False, "Only low or medium risk actions can execute from the queue.", None
        if not self.approval_gate._app_is_allowlisted(action.app_name, "demo"):
            return False, "App is not allowlisted for local demo execution.", None

        if not run_tron:
            return True, "Allowed.", None
        tron_decision = self.tron.final_action_check(action)
        if not tron_decision.allowed:
            return False, tron_decision.blocked_reason or "Tron final check blocked execution.", tron_decision
        return True, "Allowed.", tron_decision

    def _execution_context(self, record: ActionQueueRecord) -> dict[str, Any]:
        return {
            "approval_status": record.approval_status,
            "execution_status": record.execution_status,
            "action_type": record.action.action_type,
            "risk_level": record.action.risk_level,
            "app_name": record.action.app_name,
        }

    def _append_record(self, record: ActionQueueRecord) -> None:
        append_jsonl(self.queue_path, record)

    def _log_event(self, event_type: str, record: ActionQueueRecord, details: dict[str, Any]) -> None:
        append_jsonl(
            self.event_path,
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "run_id": record.run_id,
                "action_id": record.action_id,
                "attempted_by": details.get("attempted_by"),
                "result": details.get("result"),
                "blocked_reason": details.get("blocked_reason"),
                "tron_final_check_result": details.get("tron_final_check_result"),
                "details": details,
            },
        )

    def _tron_result(self, decision: ApprovalDecision | None) -> dict[str, Any] | None:
        if decision is None:
            return None
        return {
            "allowed": decision.allowed,
            "approval_required": decision.approval_required,
            "status": decision.status,
            "blocked_reason": decision.blocked_reason,
            "conditions_failed": decision.conditions_failed,
        }
