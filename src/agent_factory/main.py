from __future__ import annotations

import argparse
import json
import time

from .master_agent import AriadneMasterAgent
from .orchestrator import run_mode
from .schemas import UserTask
from .observers.screen_understanding import ScreenUnderstandingAnalyzer
from .observers.screen_text_extractor import OcrTextExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Ariadne Master Agent v0.2")
    parser.add_argument("task", nargs="?", default="Help me evaluate an RTX 3090 GPU listing")
    parser.add_argument("--mode", choices=["advisor", "assisted_fill", "demo", "screen_observe", "screen_understand", "screen_pipeline", "screen_pipeline_review"], default="advisor")
    parser.add_argument("--screenshot", default=None)
    parser.add_argument(
        "--latest-screen",
        action="store_true",
        help="Use the most recent screenshot artifact from memory/screen_observations.",
    )
    parser.add_argument(
        "--extract-text",
        action="store_true",
        help="Attempt read-only OCR text extraction from the selected screenshot artifact.",
    )
    parser.add_argument(
        "--execute-demo-form",
        action="store_true",
        help="Fill the local GPU Deal Evaluator demo form with Playwright. Never submits.",
    )
    parser.add_argument(
        "--observe-delay",
        type=float,
        default=0,
        help="Seconds to wait before screen_observe captures the active window.",
    )
    return parser
def _find_latest_screen(observation_dir: str = "memory/screen_observations") -> str:
    from pathlib import Path

    root = Path(observation_dir)

    if not root.exists():
        raise SystemExit("No screen observation directory found. Run screen_observe first.")

    screenshots = sorted(
        root.glob("*.png"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    if not screenshots:
        raise SystemExit("No screen observation screenshots found. Run screen_observe first.")

    return str(screenshots[0])


def _load_screen_metadata(screenshot_path: str) -> dict:
    from pathlib import Path

    path = Path(screenshot_path)
    metadata_path = path.with_suffix(".json")

    if not metadata_path.exists():
        return {}

    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
def _active_window_crop_box(metadata: dict) -> dict | None:
    required = [
        "active_window_left",
        "active_window_top",
        "active_window_right",
        "active_window_bottom",
    ]

    if not all(metadata.get(key) is not None for key in required):
        return None

    return {
        "left": int(metadata["active_window_left"]),
        "top": int(metadata["active_window_top"]),
        "right": int(metadata["active_window_right"]),
        "bottom": int(metadata["active_window_bottom"]),
    }


def _screen_pipeline_run_timestamp(result: dict) -> str:
    from datetime import datetime, timezone

    timestamp_utc = (result.get("observation") or {}).get("timestamp_utc")

    try:
        if timestamp_utc:
            parsed = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
        else:
            parsed = datetime.now(timezone.utc)

        return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    except Exception:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _screen_pipeline_index_record(result: dict, artifact_path: str) -> dict:
    observation = result.get("observation") or {}
    understanding = result.get("understanding") or {}
    text_quality = understanding.get("text_quality") or {}
    executable_actions = result.get("executable_actions") or []

    return {
        "artifact_path": artifact_path,
        "timestamp_utc": observation.get("timestamp_utc"),
        "app_name": observation.get("app_name"),
        "best_observed_text": understanding.get("best_observed_text"),
        "text_quality_rating": text_quality.get("rating"),
        "blocked_or_limited": observation.get("blocked_or_limited"),
        "executable_actions_count": len(executable_actions),
    }


def _append_screen_pipeline_index(
    result: dict,
    artifact_path: str,
    output_dir: str = "memory/screen_pipeline_runs",
) -> str:
    from pathlib import Path

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    index_path = root / "index.jsonl"
    record = _screen_pipeline_index_record(result, artifact_path)

    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return str(index_path)


def _save_screen_pipeline_artifact(
    result: dict,
    output_dir: str = "memory/screen_pipeline_runs",
) -> str:
    from pathlib import Path

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    timestamp = _screen_pipeline_run_timestamp(result)
    artifact_path = root / f"pipeline_{timestamp}.json"

    result["pipeline_artifact_path"] = str(artifact_path)

    artifact_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _append_screen_pipeline_index(result, str(artifact_path), output_dir=output_dir)

    return str(artifact_path)


def _load_screen_pipeline_index_entries(
    index_path: str = "memory/screen_pipeline_runs/index.jsonl",
) -> list[dict]:
    from pathlib import Path

    path = Path(index_path)

    if not path.exists():
        return []

    entries: list[dict] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries


def _latest_screen_pipeline_index_entry(
    index_path: str = "memory/screen_pipeline_runs/index.jsonl",
) -> dict | None:
    entries = _load_screen_pipeline_index_entries(index_path)

    if not entries:
        return None

    return sorted(
        entries,
        key=lambda entry: entry.get("timestamp_utc") or "",
    )[-1]


def _screen_pipeline_review_summary(entry: dict | None) -> str:
    if not entry:
        return "No screen pipeline runs found. No executable actions were proposed."

    app_name = entry.get("app_name") or "unknown app"
    blocked = entry.get("blocked_or_limited")
    best_text = entry.get("best_observed_text")
    quality = entry.get("text_quality_rating") or "unavailable"
    action_count = entry.get("executable_actions_count", 0)

    if blocked:
        return (
            f"Latest screen pipeline run observed {app_name}, but the app was blocked or limited. "
            f"No readable screen text was available. Executable actions proposed: {action_count}."
        )

    if best_text:
        return (
            f"Latest screen pipeline run observed {app_name} and read: \"{best_text}\" "
            f"Text quality rating: {quality}. Executable actions proposed: {action_count}."
        )

    return (
        f"Latest screen pipeline run observed {app_name}, but no best observed text was available. "
        f"Text quality rating: {quality}. Executable actions proposed: {action_count}."
    )


def _run_screen_pipeline_review(
    index_path: str = "memory/screen_pipeline_runs/index.jsonl",
) -> dict:
    entry = _latest_screen_pipeline_index_entry(index_path)

    return {
        "mode": "screen_pipeline_review",
        "review_summary": _screen_pipeline_review_summary(entry),
        "latest_run": entry,
        "executable_actions": [],
    }


def _run_screen_pipeline(observe_delay: float = 0, extract_text: bool = False) -> dict:
    if observe_delay > 0:
        time.sleep(observe_delay)

    observation_artifact = run_mode("screen_observe")
    observation_data = observation_artifact.to_dict()

    screenshot_path = observation_data.get("screenshot_path")

    if screenshot_path:
        metadata = _load_screen_metadata(screenshot_path)

        understanding_artifact = ScreenUnderstandingAnalyzer().analyze(
            screenshot_path,
            metadata=metadata,
        )
        understanding_data = understanding_artifact.to_dict()

        if extract_text:
            text_result = OcrTextExtractor().extract(
                screenshot_path,
                crop_box=_active_window_crop_box(metadata),
            )
            text_data = text_result.to_dict()
            best_observed_text = text_data.get("best_observed_text") or text_data.get("observed_text")

            understanding_data["observed_text"] = best_observed_text
            understanding_data["best_observed_text"] = best_observed_text
            understanding_data["text_quality"] = text_data.get("text_quality", {})
            understanding_data["text_extraction"] = text_data
    else:
        understanding_data = None

    result = {
        "pipeline": "screen_pipeline",
        "observation": observation_data,
        "understanding": understanding_data,
        "executable_actions": [],
    }

    if extract_text:
        _save_screen_pipeline_artifact(result)

    return result


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "screen_pipeline_review":
        result = _run_screen_pipeline_review()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.mode == "screen_pipeline":
        result = _run_screen_pipeline(observe_delay=args.observe_delay, extract_text=args.extract_text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.mode == "screen_understand":
        if args.latest_screen:
            args.screenshot = _find_latest_screen()

        if not args.screenshot:
            raise SystemExit("--screenshot or --latest-screen is required for screen_understand mode.")

        metadata = _load_screen_metadata(args.screenshot)

        artifact = ScreenUnderstandingAnalyzer().analyze(
            args.screenshot,
            metadata=metadata,
        )

        data = artifact.to_dict()

        if args.extract_text:
            text_result = OcrTextExtractor().extract(
                args.screenshot,
                crop_box=_active_window_crop_box(metadata),
            )
            text_data = text_result.to_dict()
            best_observed_text = text_data.get("best_observed_text") or text_data.get("observed_text")

            data["observed_text"] = best_observed_text
            data["best_observed_text"] = best_observed_text
            data["text_quality"] = text_data.get("text_quality", {})
            data["text_extraction"] = text_data

        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    if args.mode == "screen_observe":
        if args.observe_delay > 0:
            time.sleep(args.observe_delay)
        artifact = run_mode("screen_observe")
        print(json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False))
        return

    ariadne = AriadneMasterAgent()
    result = ariadne.run(
        UserTask(
            text=args.task,
            mode=args.mode,
            screenshot_path=args.screenshot,
            metadata={"execute_demo_form": args.execute_demo_form},
        )
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
