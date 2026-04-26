from __future__ import annotations

import argparse
import json
import time

from .master_agent import AriadneMasterAgent
from .orchestrator import run_mode
from .schemas import UserTask
from .observers.screen_understanding import ScreenUnderstandingAnalyzer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Ariadne Master Agent v0.2")
    parser.add_argument("task", nargs="?", default="Help me evaluate an RTX 3090 GPU listing")
    parser.add_argument("--mode", choices=["advisor", "assisted_fill", "demo", "screen_observe", "screen_understand"], default="advisor")
    parser.add_argument("--screenshot", default=None)
    parser.add_argument(
        "--latest-screen",
        action="store_true",
        help="Use the most recent screenshot artifact from memory/screen_observations.",
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


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "screen_understand":
        if args.latest_screen:
            args.screenshot = _find_latest_screen()

        if not args.screenshot:
            raise SystemExit("--screenshot or --latest-screen is required for screen_understand mode.")

        artifact = ScreenUnderstandingAnalyzer().analyze(
            args.screenshot,
            metadata=_load_screen_metadata(args.screenshot),
        )
        print(json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False))
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
