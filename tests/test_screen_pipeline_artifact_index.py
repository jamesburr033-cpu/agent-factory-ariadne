import json

from agent_factory.main import (
    _append_screen_pipeline_index,
    _save_screen_pipeline_artifact,
    _screen_pipeline_index_record,
)


def test_screen_pipeline_index_record_summarizes_run():
    result = {
        "pipeline": "screen_pipeline",
        "observation": {
            "timestamp_utc": "2026-04-27T02:25:54.721734+00:00",
            "app_name": "notepad++",
            "blocked_or_limited": False,
            "executable_actions": [],
        },
        "understanding": {
            "best_observed_text": "If you can see this, tell me a joke.",
            "text_quality": {"rating": "usable"},
            "executable_actions": [],
        },
        "executable_actions": [],
    }

    record = _screen_pipeline_index_record(
        result,
        "memory/screen_pipeline_runs/pipeline_20260427T022554Z.json",
    )

    assert record == {
        "artifact_path": "memory/screen_pipeline_runs/pipeline_20260427T022554Z.json",
        "timestamp_utc": "2026-04-27T02:25:54.721734+00:00",
        "app_name": "notepad++",
        "best_observed_text": "If you can see this, tell me a joke.",
        "text_quality_rating": "usable",
        "blocked_or_limited": False,
        "executable_actions_count": 0,
    }


def test_save_screen_pipeline_artifact_appends_index_jsonl(tmp_path):
    result = {
        "pipeline": "screen_pipeline",
        "observation": {
            "timestamp_utc": "2026-04-27T02:25:54.721734+00:00",
            "app_name": "notepad++",
            "blocked_or_limited": False,
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

    index_path = tmp_path / "index.jsonl"
    lines = index_path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 1

    record = json.loads(lines[0])

    assert record["artifact_path"] == artifact_path
    assert record["timestamp_utc"] == "2026-04-27T02:25:54.721734+00:00"
    assert record["app_name"] == "notepad++"
    assert record["best_observed_text"] == "If you can see this, tell me a joke."
    assert record["text_quality_rating"] == "usable"
    assert record["blocked_or_limited"] is False
    assert record["executable_actions_count"] == 0


def test_append_screen_pipeline_index_handles_blocked_run_without_understanding(tmp_path):
    result = {
        "pipeline": "screen_pipeline",
        "observation": {
            "timestamp_utc": "2026-04-27T02:24:20.840433+00:00",
            "app_name": "windows powershell",
            "blocked_or_limited": True,
            "executable_actions": [],
        },
        "understanding": None,
        "executable_actions": [],
    }

    _append_screen_pipeline_index(
        result,
        "memory/screen_pipeline_runs/pipeline_20260427T022420Z.json",
        output_dir=str(tmp_path),
    )

    record = json.loads((tmp_path / "index.jsonl").read_text(encoding="utf-8").splitlines()[0])

    assert record["app_name"] == "windows powershell"
    assert record["blocked_or_limited"] is True
    assert record["best_observed_text"] is None
    assert record["text_quality_rating"] is None
    assert record["executable_actions_count"] == 0
