from agent_factory.agents.browser_agent import BrowserAgent
from agent_factory.approvals import ApprovalGate
from agent_factory.schemas import UserTask


def _gpu_task():
    return UserTask(
        text=(
            "Help me evaluate an RTX 3090 GPU listing. Price is 650 dollars, "
            "24 GB VRAM, used, local pickup, seller says it works but has not provided benchmarks. "
            "Recommend red flags, offer price, and a draft seller message. Do not send anything."
        ),
        mode="assisted_fill",
    )


def test_browser_agent_creates_gpu_deal_form_actions():
    observation, actions = BrowserAgent().plan(_gpu_task())
    assert observation.app_name == "GPU Deal Evaluator"
    assert any(action.field_name == "Product" and action.value == "RTX 3090" for action in actions)
    assert any(action.field_name == "VRAM" and action.value == "24 GB" for action in actions)
    assert any(action.field_name == "Price" and action.value == "$650" for action in actions)
    assert any(action.field_name == "Draft message" for action in actions)


def test_gpu_deal_fields_are_allowlisted_for_assisted_fill():
    _, actions = BrowserAgent().plan(_gpu_task())
    decisions = ApprovalGate().evaluate_many(actions, mode="assisted_fill")
    fill_decisions = [d for d in decisions if d.action.action_type == "fill_field"]
    assert fill_decisions
    assert all(d.allowed for d in fill_decisions)
    assert all(d.status == "allowed" for d in fill_decisions)


def test_gpu_deal_submit_requires_approval_before_execution():
    _, actions = BrowserAgent().plan(_gpu_task())
    decisions = ApprovalGate().evaluate_many(actions, mode="assisted_fill")
    submit_decisions = [d for d in decisions if d.action.action_type == "submit_form"]
    assert len(submit_decisions) == 1
    assert submit_decisions[0].allowed is True
    assert submit_decisions[0].approval_required is True
    assert submit_decisions[0].status == "requires_approval_before_execution"
