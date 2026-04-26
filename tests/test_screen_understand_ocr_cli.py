import json
import sys

from agent_factory.main import main


def test_screen_understand_cli_extract_text_adds_text_extraction_block(tmp_path, monkeypatch, capsys):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

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

    assert data["screenshot_exists"] is True
    assert "text_extraction" in data
    assert data["text_extraction"]["screenshot_exists"] is True
    assert data["text_extraction"]["executable_actions"] == []
    assert data["executable_actions"] == []


def test_screen_understand_cli_extract_text_handles_missing_file_safely(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "missing.png"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_factory.main",
            "--mode",
            "screen_understand",
            "--screenshot",
            str(missing),
            "--extract-text",
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["screenshot_exists"] is False
    assert data["text_extraction"]["screenshot_exists"] is False
    assert data["text_extraction"]["observed_text"] is None
    assert data["text_extraction"]["executable_actions"] == []
