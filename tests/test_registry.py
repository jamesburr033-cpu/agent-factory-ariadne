from agent_factory.registry import AgentRegistry


def test_registry_loads_ariadne_agents():
    registry = AgentRegistry()
    names = registry.list_names()
    assert "tron" in names
    assert "screen_advisor_agent" in names
    assert "self_improvement_agent" in names
