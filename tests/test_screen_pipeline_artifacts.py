import json

from agent_factory.main import (
    _run_screen_pipeline,
    _save_screen_pipeline_artifact,
)


def test_save_screen_pipeline_artifact_writes_json(tmp_path):
    result = {
        "pipeline": "screen_pipeline",
        "observation": {
            "timestamp_utc": "2026-04-27T02:02:47.574526+00:00",
            "executable_actions": [],
        },
        "understanding": {
            "best_observed_text": "If you can see this, tell me a joke.",
            "text_quality": {"rating": "usable"},
            "executable_actions": [],
        },
        "executable_actions": [],
    }

    artifact_path = _save_screen_pipeline_artifact(result, output_dir=str(tmp_path))

    assert artifact_path.endswith("pipeline_20260427T020247Z.json")

    data = json.loads((tmp_path / "pipeline_20260427T020247Z.json").read_text(encoding="utf-8"))

    assert data["pipeline"] == "screen_pipeline"
    assert data["pipeline_artifact_path"] == artifact_path
    assert data["understanding"]["best_observed_text"] == "If you can see this, tell me a joke."
    assert data["understanding"]["executable_actions"] == []
    assert data["executable_actions"] == []


def test_screen_pipeline_extract_text_saves_artifact(monkeypatch):
    saved = {}

    class FakeObservationArtifact:
        def to_dict(self):
            return {
                "screenshot_path": "memory/screen_observations/fake.png",
                "timestamp_utc": "2026-04-27T02:02:47.574526+00:00",
                "active_window_left": 10,
                "active_window_top": 20,
                "active_window_right": 1010,
                "active_window_bottom": 720,
                "executable_actions": [],
            }

    class FakeUnderstandingArtifact:
        def to_dict(self):
            return {
                "screenshot_path": "memory/screen_observations/fake.png",
                "observed_text": None,
                "metadata": {},
                "executable_actions": [],
            }

    class FakeOcrResult:
        def to_dict(self):
            return {
                "observed_text": "cleaned text",
                "best_observed_text": "best text",
                "text_quality": {"rating": "usable"},
                "executable_actions": [],
            }

    class FakeOcrExtractor:
        def extract(self, screenshot_path, crop_box=None):
            return FakeOcrResult()

    def fake_save(result):
        saved["result"] = result
        result["pipeline_artifact_path"] = "memory/screen_pipeline_runs/pipeline_fake.json"
        return result["pipeline_artifact_path"]

    monkeypatch.setattr("agent_factory.main.run_mode", lambda mode: FakeObservationArtifact())
    monkeypatch.setattr(
        "agent_factory.main.ScreenUnderstandingAnalyzer",
        lambda: type(
            "FakeAnalyzer",
            (),
            {"analyze": lambda self, screenshot_path, metadata=None: FakeUnderstandingArtifact()},
        )(),
    )
    monkeypatch.setattr(
        "agent_factory.main._load_screen_metadata",
        lambda screenshot_path: {
            "active_window_left": 10,
            "active_window_top": 20,
            "active_window_right": 1010,
            "active_window_bottom": 720,
        },
    )
    monkeypatch.setattr("agent_factory.main.OcrTextExtractor", FakeOcrExtractor)
    monkeypatch.setattr("agent_factory.main._save_screen_pipeline_artifact", fake_save)

    result = _run_screen_pipeline(observe_delay=0, extract_text=True)

    assert result["pipeline_artifact_path"] == "memory/screen_pipeline_runs/pipeline_fake.json"
    assert saved["result"]["understanding"]["best_observed_text"] == "best text"
    assert saved["result"]["understanding"]["text_quality"]["rating"] == "usable"
    assert saved["result"]["executable_actions"] == []
