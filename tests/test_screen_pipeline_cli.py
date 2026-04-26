import json
import sys

from agent_factory.main import main


def test_screen_pipeline_cli_outputs_combined_artifact(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["agent_factory.main", "--mode", "screen_pipeline"],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["pipeline"] == "screen_pipeline"
    assert "observation" in data
    assert "understanding" in data
    assert data["executable_actions"] == []
    assert data["observation"]["executable_actions"] == []


def test_screen_pipeline_generates_no_executable_actions(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["agent_factory.main", "--mode", "screen_pipeline"],
    )

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["executable_actions"] == []

    if data["understanding"] is not None:
        assert data["understanding"]["executable_actions"] == []
