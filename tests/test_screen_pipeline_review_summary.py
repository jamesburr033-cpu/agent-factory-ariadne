import json
import sys

from agent_factory.main import (
    _latest_screen_pipeline_index_entry,
    _run_screen_pipeline_review,
    _screen_pipeline_review_summary,
    main,
)


def test_screen_pipeline_review_summary_for_readable_run():
    entry = {
        "artifact_path": "memory/screen_pipeline_runs/pipeline_20260427T023859Z.json",
        "timestamp_utc": "2026-04-27T02:38:59.002672+00:00",
        "app_name": "notepad++",
        "best_observed_text": "If you can see this, tell me a joke.",
        "text_quality_rating": "usable",
        "blocked_or_limited": False,
        "executable_actions_count": 0,
    }

    summary = _screen_pipeline_review_summary(entry)

    assert "notepad++" in summary
    assert "If you can see this, tell me a joke." in summary
    assert "usable" in summary
    assert "Executable actions proposed: 0" in summary


def test_screen_pipeline_review_summary_for_blocked_run():
    entry = {
        "artifact_path": "memory/screen_pipeline_runs/pipeline_20260427T022420Z.json",
        "timestamp_utc": "2026-04-27T02:24:20.840433+00:00",
        "app_name": "windows powershell",
        "best_observed_text": None,
        "text_quality_rating": None,
        "blocked_or_limited": True,
        "executable_actions_count": 0,
    }

    summary = _screen_pipeline_review_summary(entry)

    assert "windows powershell" in summary
    assert "blocked or limited" in summary
    assert "Executable actions proposed: 0" in summary


def test_latest_screen_pipeline_index_entry_uses_last_valid_line(tmp_path):
    index_path = tmp_path / "index.jsonl"
    index_path.write_text(
        "\n".join(
            [
                json.dumps({"app_name": "first"}),
                "not json",
                json.dumps({"app_name": "latest", "executable_actions_count": 0}),
            ]
        ),
        encoding="utf-8",
    )

    entry = _latest_screen_pipeline_index_entry(str(index_path))

    assert entry == {"app_name": "latest", "executable_actions_count": 0}


def test_run_screen_pipeline_review_returns_safe_payload(tmp_path):
    index_path = tmp_path / "index.jsonl"
    index_path.write_text(
        json.dumps(
            {
                "artifact_path": "memory/screen_pipeline_runs/pipeline_fake.json",
                "timestamp_utc": "2026-04-27T02:38:59.002672+00:00",
                "app_name": "notepad++",
                "best_observed_text": "If you can see this, tell me a joke.",
                "text_quality_rating": "usable",
                "blocked_or_limited": False,
                "executable_actions_count": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = _run_screen_pipeline_review(str(index_path))

    assert result["mode"] == "screen_pipeline_review"
    assert result["latest_run"]["app_name"] == "notepad++"
    assert "If you can see this, tell me a joke." in result["review_summary"]
    assert result["executable_actions"] == []


def test_screen_pipeline_review_cli_outputs_summary(monkeypatch, capsys):
    monkeypatch.setattr(
        "agent_factory.main._run_screen_pipeline_review",
        lambda: {
            "mode": "screen_pipeline_review",
            "review_summary": "Latest screen pipeline run observed notepad++.",
            "latest_run": {"app_name": "notepad++"},
            "executable_actions": [],
        },
    )
    monkeypatch.setattr(sys, "argv", ["agent_factory.main", "--mode", "screen_pipeline_review"])

    main()

    data = json.loads(capsys.readouterr().out)

    assert data["mode"] == "screen_pipeline_review"
    assert data["latest_run"]["app_name"] == "notepad++"
    assert data["executable_actions"] == []
