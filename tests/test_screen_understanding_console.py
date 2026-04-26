from agent_factory.observers.screen_understanding import ScreenUnderstandingAnalyzer
from agent_factory.review_console import render_screen_understanding


def test_review_console_renders_screen_understanding(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    artifact = ScreenUnderstandingAnalyzer().analyze(
        str(screenshot),
        metadata={"active_window_title": "*new 1 - Notepad++", "app_name": "notepad++"},
    )

    rendered = render_screen_understanding(artifact)

    assert "Screen Understanding Artifact" in rendered
    assert "Screenshot:" in rendered
    assert "Summary:" in rendered
    assert "Confidence: medium" in rendered
    assert "Observed text: <not available>" in rendered
    assert "Executable actions: []" in rendered


def test_review_console_renders_screen_understanding_limitations(tmp_path):
    screenshot = tmp_path / "screen_test.png"
    screenshot.write_bytes(b"fake png bytes")

    artifact = ScreenUnderstandingAnalyzer().analyze(str(screenshot))
    rendered = render_screen_understanding(artifact)

    assert "Limitations:" in rendered
    assert "No OCR or vision model" in rendered
    assert "Understanding is based on artifact metadata only" in rendered
