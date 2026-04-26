from agent_factory.master_agent import AriadneMasterAgent
from agent_factory.schemas import UserTask


def test_self_improvement_is_proposal_only():
    ariadne = AriadneMasterAgent()
    result = ariadne.run(UserTask(text="Review failed actions and self improve", mode="advisor"))
    assert result.routing.selected_agent == "self_improvement_agent"
    assert result.improvement_proposals
    assert all(p.requires_human_approval for p in result.improvement_proposals)
    assert all(p.may_apply_directly is False for p in result.improvement_proposals)
    assert "modify_code" in result.critic_review.required_approvals
