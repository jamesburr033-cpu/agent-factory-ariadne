import json
import sys

import pytest

from agent_factory.main import main


def test_screen_understand_cli_outputs_artifact(tmp_path, monkeypatch, capsys):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    metadata = tmp_path / "screen_test.json"
    metadata.write_text(
        json.dumps({"active_window_title": "*new 1 - Notepad++", "app_name": "notepad++"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agent_factory.main",
            "--mode",
            "screen_understand",
            "--screenshot",
            str(screenshot),
        ],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["screenshot_exists"] is True
    assert "*new 1 - Notepad++" in data["screen_summary"]
    assert data["metadata"]["app_name"] == "notepad++"
    assert data["executable_actions"] == []


def test_screen_understand_cli_requires_screenshot(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agent_factory.main", "--mode", "screen_understand"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert "--screenshot or --latest-screen is required" in str(excinfo.value)
