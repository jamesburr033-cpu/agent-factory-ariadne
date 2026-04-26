from agent_factory.router import TaskRouter
from agent_factory.schemas import UserTask


def test_routes_servicenow_to_form_fill():
    decision = TaskRouter().route(UserTask(text="Help me fill a ServiceNow ticket"))
    assert decision.task_type == "form_fill"
    assert decision.selected_agent == "screen_advisor_agent"


def test_routes_gpu_to_browser_agent():
    decision = TaskRouter().route(UserTask(text="Find RTX 3090 GPU listings"))
    assert decision.task_type == "browser_research"
    assert decision.selected_agent == "browser_agent"


def test_ebay_read_only_url_routes_to_browser_research_before_form_fill():
    decision = TaskRouter().route(
        UserTask(text="Read-only research this eBay GPU listing https://www.ebay.com/itm/123 and do not submit forms")
    )
    assert decision.task_type == "browser_research"
    assert decision.selected_agent == "browser_agent"


def test_example_url_read_only_routes_to_browser_research_for_allowlist_blocking():
    decision = TaskRouter().route(
        UserTask(text="Read-only browser research this listing https://example.org/rtx-3090")
    )
    assert decision.task_type == "browser_research"
    assert decision.selected_agent == "browser_agent"


def test_do_not_submit_forms_does_not_force_form_fill():
    decision = TaskRouter().route(
        UserTask(text="Read-only research https://www.ebay.com/itm/123. Do not submit forms.")
    )
    assert decision.task_type == "browser_research"
    assert decision.selected_agent == "browser_agent"


def test_true_form_fill_still_routes_to_form_fill():
    decision = TaskRouter().route(UserTask(text="Help me fill the ServiceNow short description field"))
    assert decision.task_type == "form_fill"
    assert decision.selected_agent == "screen_advisor_agent"
