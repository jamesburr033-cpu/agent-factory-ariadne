import json
import sys

import pytest

from agent_factory.main import main


def test_screen_understand_cli_uses_latest_screen(tmp_path, monkeypatch, capsys):
    old_screen = tmp_path / "old.png"
    new_screen = tmp_path / "new.png"

    old_screen.write_bytes(b"old")
    new_screen.write_bytes(b"newer")

    metadata = tmp_path / "new.json"
    metadata.write_text(
        json.dumps({"active_window_title": "Latest Notepad++", "app_name": "notepad++"}),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    screen_dir = tmp_path / "memory" / "screen_observations"
    screen_dir.mkdir(parents=True)

    target_old = screen_dir / "old.png"
    target_new = screen_dir / "new.png"
    target_old.write_bytes(old_screen.read_bytes())
    target_new.write_bytes(new_screen.read_bytes())
    (screen_dir / "new.json").write_text(metadata.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["agent_factory.main", "--mode", "screen_understand", "--latest-screen"],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["screenshot_exists"] is True
    assert data["metadata"]["app_name"] == "notepad++"
    assert "Latest Notepad++" in data["screen_summary"]
    assert data["executable_actions"] == []


def test_screen_understand_latest_screen_errors_when_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["agent_factory.main", "--mode", "screen_understand", "--latest-screen"],
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert "No screen observation directory found" in str(excinfo.value)
