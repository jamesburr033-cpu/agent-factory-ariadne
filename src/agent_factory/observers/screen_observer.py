from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
from typing import Optional


@dataclass
class ScreenObservation:
    screenshot_path: Optional[str]
    timestamp_utc: str
    machine_name: str
    width: Optional[int]
    height: Optional[int]
    active_window_title: Optional[str]
    process_name: Optional[str]
    app_name: Optional[str]
    allowlisted: bool
    blocked_reason: Optional[str]
    active_window_left: Optional[int] = None
    active_window_top: Optional[int] = None
    active_window_right: Optional[int] = None
    active_window_bottom: Optional[int] = None


class ScreenObserver:
    def __init__(self, observation_dir: str = "memory/screen_observations") -> None:
        self.observation_dir = Path(observation_dir)
        self.observation_dir.mkdir(parents=True, exist_ok=True)

    def observe(self, allowlist_path: str = "configs/app_allowlist.yaml") -> ScreenObservation:
        now = datetime.now(timezone.utc)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        timestamp_utc = now.isoformat()

        active_window_title, process_name, app_name, active_rect = self._active_window_metadata()
        allowlist = self._load_allowlist(allowlist_path)
        allowlisted = self._is_allowlisted(app_name, process_name, allowlist)

        screenshot_path: Optional[str] = None
        width: Optional[int] = None
        height: Optional[int] = None
        blocked_reason: Optional[str] = None

        if allowlisted:
            screenshot_path, width, height = self._capture_screenshot(stamp)
        else:
            blocked_reason = "Active application is not in allowlist; screenshot capture limited."

        observation = ScreenObservation(
            screenshot_path=screenshot_path,
            timestamp_utc=timestamp_utc,
            machine_name=platform.node() or os.environ.get("COMPUTERNAME", "unknown"),
            width=width,
            height=height,
            active_window_title=active_window_title,
            process_name=process_name,
            app_name=app_name,
            allowlisted=allowlisted,
            blocked_reason=blocked_reason,
            active_window_left=active_rect.get("left") if active_rect else None,
            active_window_top=active_rect.get("top") if active_rect else None,
            active_window_right=active_rect.get("right") if active_rect else None,
            active_window_bottom=active_rect.get("bottom") if active_rect else None,
        )

        self._write_artifact(stamp, observation)
        return observation

    def _capture_screenshot(self, stamp: str) -> tuple[Optional[str], Optional[int], Optional[int]]:
        path = self.observation_dir / f"screen_{stamp}.png"

        try:
            from PIL import ImageGrab  # type: ignore

            image = ImageGrab.grab()
            image.save(path)
            return str(path), image.width, image.height
        except Exception:
            return None, None, None

    def _active_window_metadata(
        self,
    ) -> tuple[Optional[str], Optional[str], Optional[str], Optional[dict[str, int]]]:
        if os.name != "nt":
            return None, None, None, None

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()

            if not hwnd:
                return None, None, None, None

            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value or None

            rect = wintypes.RECT()
            active_rect = None
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                active_rect = {
                    "left": int(rect.left),
                    "top": int(rect.top),
                    "right": int(rect.right),
                    "bottom": int(rect.bottom),
                }

            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            process_name = None
            app_name = None

            try:
                import psutil  # type: ignore

                process_name = psutil.Process(pid.value).name()
                app_name = process_name.split(".")[0].lower() if process_name else None
            except Exception:
                process_name = None
                app_name = None

            if not app_name and title:
                app_name = self._infer_app_name_from_title(title)

            return title, process_name, app_name, active_rect
        except Exception:
            return None, None, None, None

    def _infer_app_name_from_title(self, title: str) -> Optional[str]:
        normalized = title.lower()

        known_apps = {
            "notepad++": ["notepad++"],
            "notepad": ["notepad"],
            "calculator": ["calculator"],
            "mspaint": ["mspaint", "paint"],
        }

        for app_name, markers in known_apps.items():
            if any(marker in normalized for marker in markers):
                return app_name

        parts = [part.strip() for part in title.split("-") if part.strip()]
        if len(parts) > 1:
            return parts[-1].lower()

        return title.strip().lower() or None

    def _load_allowlist(self, allowlist_path: str) -> set[str]:
        path = Path(allowlist_path)

        if not path.exists():
            return set()

        values: set[str] = set()

        for raw in path.read_text().splitlines():
            line = raw.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("-"):
                values.add(line.lstrip("-").strip().lower())

        return values

    def _is_allowlisted(
        self,
        app_name: Optional[str],
        process_name: Optional[str],
        allowlist: set[str],
    ) -> bool:
        if not allowlist:
            return False

        candidates = {value.lower() for value in [app_name, process_name] if value}

        for candidate in list(candidates):
            if candidate.endswith(".exe"):
                candidates.add(candidate[:-4])

        return any(candidate in allowlist for candidate in candidates)

    def _write_artifact(self, stamp: str, observation: ScreenObservation) -> None:
        artifact_path = self.observation_dir / f"screen_{stamp}.json"
        artifact_path.write_text(json.dumps(asdict(observation), indent=2))
