from __future__ import annotations

from .config_loader import config_path, load_yaml
from .schemas import AgentDefinition


class AgentRegistry:
    def __init__(self, config_name: str = "agents.yaml") -> None:
        raw = load_yaml(config_path(config_name))
        agents_raw = raw.get("agents", {})
        self._agents: dict[str, AgentDefinition] = {}
        for name, data in agents_raw.items():
            self._agents[name] = AgentDefinition(name=name, **data)

    def get(self, name: str) -> AgentDefinition:
        if name not in self._agents:
            raise KeyError(f"Agent not registered: {name}")
        return self._agents[name]

    def list_names(self) -> list[str]:
        return sorted(self._agents.keys())

    def all(self) -> dict[str, AgentDefinition]:
        return dict(self._agents)
