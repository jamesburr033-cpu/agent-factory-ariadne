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
    parser.add_argument("--mode", choices=["advisor", "assisted_fill", "demo", "screen_observe", "screen_understand", "screen_pipeline"], default="advisor")
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


def _run_screen_pipeline(observe_delay: float = 0) -> dict:
    if observe_delay > 0:
        time.sleep(observe_delay)

    observation_artifact = run_mode("screen_observe")
    observation_data = observation_artifact.to_dict()

    screenshot_path = observation_data.get("screenshot_path")

    if screenshot_path:
        understanding_artifact = ScreenUnderstandingAnalyzer().analyze(
            screenshot_path,
            metadata=_load_screen_metadata(screenshot_path),
        )
        understanding_data = understanding_artifact.to_dict()
    else:
        understanding_data = None

    return {
        "pipeline": "screen_pipeline",
        "observation": observation_data,
        "understanding": understanding_data,
        "executable_actions": [],
    }


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "screen_pipeline":
        result = _run_screen_pipeline(observe_delay=args.observe_delay)
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
