from agent_factory.observers.screen_understanding import ScreenUnderstandingAnalyzer


def test_screen_understanding_artifact_created_for_existing_file(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    artifact = ScreenUnderstandingAnalyzer().analyze(str(screenshot))

    assert artifact.screenshot_exists is True
    assert artifact.file_size_bytes == len(b"fake png bytes")
    assert artifact.observed_text is None
    assert artifact.executable_actions == []


def test_screen_understanding_handles_missing_file_safely(tmp_path):
    missing = tmp_path / "missing.png"

    artifact = ScreenUnderstandingAnalyzer().analyze(str(missing))

    assert artifact.screenshot_exists is False
    assert artifact.file_size_bytes is None
    assert "could not be found" in artifact.screen_summary
    assert artifact.executable_actions == []


def test_screen_understanding_uses_active_window_metadata(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    artifact = ScreenUnderstandingAnalyzer().analyze(
        str(screenshot),
        metadata={"active_window_title": "*new 1 - Notepad++", "app_name": "notepad++"},
    )

    assert "*new 1 - Notepad++" in artifact.screen_summary
    assert artifact.metadata["app_name"] == "notepad++"
    assert artifact.confidence == "medium"


def test_screen_understanding_declares_no_ocr_or_vision_yet(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    artifact = ScreenUnderstandingAnalyzer().analyze(str(screenshot))

    assert any("No OCR or vision model" in item for item in artifact.limitations)


def test_screen_understanding_to_dict_shape(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    data = ScreenUnderstandingAnalyzer().analyze(str(screenshot)).to_dict()

    assert data["screenshot_path"]
    assert data["screenshot_exists"] is True
    assert "screen_summary" in data
    assert data["executable_actions"] == []


def test_screen_understanding_never_generates_forbidden_actions(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    artifact = ScreenUnderstandingAnalyzer().analyze(str(screenshot))
    forbidden = {"click", "type", "send", "submit", "buy", "delete"}

    assert artifact.executable_actions == []
    assert all(action.get("type") not in forbidden for action in artifact.executable_actions)
