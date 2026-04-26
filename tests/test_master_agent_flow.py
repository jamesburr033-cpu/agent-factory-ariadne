from agent_factory.master_agent import AriadneMasterAgent
from agent_factory.schemas import UserTask


def test_ariadne_runs_servicenow_assisted_flow():
    ariadne = AriadneMasterAgent()
    result = ariadne.run(UserTask(text="Help me fill a ServiceNow ticket", mode="assisted_fill"))
    assert result.machine_name == "Ariadne"
    assert result.routing.selected_agent == "screen_advisor_agent"
    assert result.critic_review.critic_name == "Tron"
    assert any(a.action_type == "submit_form" for a in result.recommended_actions)
    assert result.requires_human_approval is True


def test_ariadne_blocks_field_fill_in_advisor_mode():
    ariadne = AriadneMasterAgent()
    result = ariadne.run(UserTask(text="Help me fill a ServiceNow ticket", mode="advisor"))
    assert result.blocked is True
    assert any(not d.allowed for d in result.approval_decisions)


def test_ariadne_gpu_demo_plan_does_not_execute_without_flag():
    ariadne = AriadneMasterAgent()
    result = ariadne.run(UserTask(text="Evaluate RTX 3090 listing price is 650 dollars 24 GB VRAM used", mode="assisted_fill"))
    assert result.routing.selected_agent == "browser_agent"
    assert result.screen_observation.app_name == "GPU Deal Evaluator"
    assert result.artifacts == {}
    assert any(d.status == "requires_approval_before_execution" for d in result.approval_decisions)
