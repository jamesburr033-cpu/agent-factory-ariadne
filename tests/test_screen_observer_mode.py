from agent_factory.agents.screen_advisor_agent import ScreenAdvisorAgent
from agent_factory.observers.screen_observer import ScreenObservation
from agent_factory.orchestrator import run_mode


class FakeObserver:
    def __init__(self, allowlisted: bool = True):
        self.allowlisted = allowlisted
        self.called = False

    def observe(self, allowlist_path: str = "configs/app_allowlist.yaml") -> ScreenObservation:
        self.called = True
        return ScreenObservation(
            screenshot_path="memory/screen_observations/screen_20260101T000000Z.png" if self.allowlisted else None,
            timestamp_utc="2026-01-01T00:00:00+00:00",
            machine_name="TEST-PC",
            width=1920 if self.allowlisted else None,
            height=1080 if self.allowlisted else None,
            active_window_title="Calculator",
            process_name="CalculatorApp.exe",
            app_name="calculator",
            allowlisted=self.allowlisted,
            blocked_reason=None if self.allowlisted else "Active application is not in allowlist; screenshot capture limited.",
        )


def test_screen_observe_mode_routes_to_screen_advisor_agent():
    observer = FakeObserver(allowlisted=True)
    artifact = run_mode("screen_observe", observer=observer, advisor=ScreenAdvisorAgent())

    assert observer.called is True
    assert artifact.recommended_observations


def test_screenshot_artifact_schema_is_created():
    artifact = run_mode("screen_observe", observer=FakeObserver(allowlisted=True), advisor=ScreenAdvisorAgent())

    assert artifact.screenshot_path is not None
    assert artifact.timestamp_utc
    assert artifact.machine_name


def test_no_executable_actions_are_generated():
    artifact = run_mode("screen_observe", observer=FakeObserver(allowlisted=True), advisor=ScreenAdvisorAgent())

    assert artifact.executable_actions == []


def test_unallowlisted_app_is_handled_safely():
    artifact = run_mode("screen_observe", observer=FakeObserver(allowlisted=False), advisor=ScreenAdvisorAgent())

    assert artifact.blocked_or_limited is True
    assert artifact.screenshot_path is None


def test_tron_review_confirms_read_only_behavior():
    artifact = run_mode("screen_observe", observer=FakeObserver(allowlisted=True), advisor=ScreenAdvisorAgent())

    assert "Read-only confirmed" in artifact.tron_safety_review
    assert "No click/type/send/buy/submit/delete actions are permitted" in artifact.tron_safety_review


def test_forbidden_actions_are_never_present():
    artifact = run_mode("screen_observe", observer=FakeObserver(allowlisted=True), advisor=ScreenAdvisorAgent())

    forbidden = {"click", "type", "send", "submit", "buy", "delete"}
    assert artifact.executable_actions == []
    assert all(action.get("type") not in forbidden for action in artifact.executable_actions)
