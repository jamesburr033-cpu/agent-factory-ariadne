from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from .config_loader import MEMORY_DIR


class JsonlAuditLog:
    def __init__(self, filename: str = "agent_runs.jsonl") -> None:
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.path = MEMORY_DIR / filename

    def append(self, item: BaseModel | dict[str, Any]) -> None:
        if isinstance(item, BaseModel):
            payload = item.model_dump(mode="json")
        else:
            payload = item
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
