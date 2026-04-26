import json
import sys

from agent_factory.main import main


class FakeOcrResult:
    observed_text = "cleaned fallback text"

    def __init__(self, best_observed_text):
        self.best_observed_text = best_observed_text

    def to_dict(self):
        return {
            "screenshot_path": "screen.png",
            "screenshot_exists": True,
            "observed_text": self.observed_text,
            "best_observed_text": self.best_observed_text,
            "text_quality": {"score": 0.79, "rating": "usable", "warnings": []},
            "executable_actions": [],
        }


class FakeOcrExtractorWithBest:
    def extract(self, screenshot_path, crop_box=None):
        return FakeOcrResult("If you can see this, tell me a Joke.")


class FakeOcrExtractorWithoutBest:
    def extract(self, screenshot_path, crop_box=None):
        return FakeOcrResult(None)


def test_screen_understand_promotes_best_observed_text(tmp_path, monkeypatch, capsys):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"fake png bytes")

    monkeypatch.setattr("agent_factory.main.OcrTextExtractor", FakeOcrExtractorWithBest)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_factory.main",
            "--mode",
            "screen_understand",
            "--screenshot",
            str(screenshot),
            "--extract-text",
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["observed_text"] == "If you can see this, tell me a Joke."
    assert data["best_observed_text"] == "If you can see this, tell me a Joke."
    assert data["text_quality"]["rating"] == "usable"
    assert data["executable_actions"] == []


def test_screen_understand_falls_back_to_cleaned_observed_text(tmp_path, monkeypatch, capsys):
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"fake png bytes")

    monkeypatch.setattr("agent_factory.main.OcrTextExtractor", FakeOcrExtractorWithoutBest)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_factory.main",
            "--mode",
            "screen_understand",
            "--screenshot",
            str(screenshot),
            "--extract-text",
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["observed_text"] == "cleaned fallback text"
    assert data["best_observed_text"] == "cleaned fallback text"
    assert data["text_extraction"]["executable_actions"] == []
