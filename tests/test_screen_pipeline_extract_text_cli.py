import json
import sys

from agent_factory.main import main


class FakeObservationArtifact:
    def to_dict(self):
        return {
            "screenshot_path": "memory/screen_observations/fake.png",
            "timestamp_utc": "2026-04-26T00:00:00+00:00",
            "machine_name": "Ariadne",
            "width": 1920,
            "height": 1080,
            "active_window_title": "*new 1 - Notepad++",
            "process_name": None,
            "app_name": "notepad++",
            "active_window_left": 10,
            "active_window_top": 20,
            "active_window_right": 1010,
            "active_window_bottom": 720,
            "blocked_or_limited": False,
            "tron_safety_review": "TRON Safety Review: Read-only confirmed.",
            "recommended_observations": ["Read-only screen observation captured."],
            "executable_actions": [],
        }


class FakeUnderstandingArtifact:
    def to_dict(self):
        return {
            "screenshot_path": "memory/screen_observations/fake.png",
            "screenshot_exists": True,
            "file_size_bytes": 123,
            "screen_summary": "Screenshot artifact exists.",
            "observed_text": None,
            "confidence": "medium",
            "limitations": [],
            "metadata": {},
            "executable_actions": [],
        }


class FakeOcrResult:
    observed_text = "cleaned fallback text"

    def to_dict(self):
        return {
            "screenshot_path": "memory/screen_observations/fake.png",
            "screenshot_exists": True,
            "observed_text": "cleaned fallback text",
            "best_observed_text": "If you can see this, tell me a Joke.",
            "text_quality": {"score": 0.79, "rating": "usable", "warnings": []},
            "executable_actions": [],
        }


class FakeOcrExtractor:
    def extract(self, screenshot_path, crop_box=None):
        assert screenshot_path == "memory/screen_observations/fake.png"
        assert crop_box == {"left": 10, "top": 20, "right": 1010, "bottom": 720}
        return FakeOcrResult()


def test_screen_pipeline_extract_text_promotes_best_text(monkeypatch, capsys):
    monkeypatch.setattr("agent_factory.main.run_mode", lambda mode: FakeObservationArtifact())
    monkeypatch.setattr(
        "agent_factory.main.ScreenUnderstandingAnalyzer",
        lambda: type(
            "FakeAnalyzer",
            (),
            {"analyze": lambda self, screenshot_path, metadata=None: FakeUnderstandingArtifact()},
        )(),
    )
    monkeypatch.setattr("agent_factory.main._load_screen_metadata", lambda screenshot_path: {
        "active_window_left": 10,
        "active_window_top": 20,
        "active_window_right": 1010,
        "active_window_bottom": 720,
    })
    monkeypatch.setattr("agent_factory.main.OcrTextExtractor", FakeOcrExtractor)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_factory.main",
            "--mode",
            "screen_pipeline",
            "--observe-delay",
            "0",
            "--extract-text",
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["pipeline"] == "screen_pipeline"
    assert data["executable_actions"] == []
    assert data["observation"]["executable_actions"] == []
    assert data["understanding"]["executable_actions"] == []
    assert data["understanding"]["observed_text"] == "If you can see this, tell me a Joke."
    assert data["understanding"]["best_observed_text"] == "If you can see this, tell me a Joke."
    assert data["understanding"]["text_quality"]["rating"] == "usable"
    assert data["understanding"]["text_extraction"]["executable_actions"] == []


def test_screen_pipeline_without_extract_text_preserves_existing_behavior(monkeypatch, capsys):
    monkeypatch.setattr("agent_factory.main.run_mode", lambda mode: FakeObservationArtifact())
    monkeypatch.setattr(
        "agent_factory.main.ScreenUnderstandingAnalyzer",
        lambda: type(
            "FakeAnalyzer",
            (),
            {"analyze": lambda self, screenshot_path, metadata=None: FakeUnderstandingArtifact()},
        )(),
    )
    monkeypatch.setattr("agent_factory.main._load_screen_metadata", lambda screenshot_path: {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_factory.main",
            "--mode",
            "screen_pipeline",
            "--observe-delay",
            "0",
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["pipeline"] == "screen_pipeline"
    assert data["understanding"]["observed_text"] is None
    assert "best_observed_text" not in data["understanding"]
    assert "text_quality" not in data["understanding"]
    assert "text_extraction" not in data["understanding"]
    assert data["executable_actions"] == []
