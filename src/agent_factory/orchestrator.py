from __future__ import annotations

from agent_factory.agents.screen_advisor_agent import ScreenAdvisorAgent
from agent_factory.observers.screen_observer import ScreenObserver


def run_mode(
    mode: str,
    observer: ScreenObserver | None = None,
    advisor: ScreenAdvisorAgent | None = None,
):
    if mode != "screen_observe":
        raise ValueError(f"Unsupported mode: {mode}")

    observer = observer or ScreenObserver()
    advisor = advisor or ScreenAdvisorAgent()

    observation = observer.observe(allowlist_path="configs/screen_observer_allowlist.yaml")
    return advisor.review_screen_observation(observation)
