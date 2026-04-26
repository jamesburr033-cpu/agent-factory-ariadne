from agent_factory.observers.screen_text_extractor import OcrTextExtractor, OcrTextResult


def test_ocr_result_shape_for_missing_file(tmp_path):
    missing = tmp_path / "missing.png"

    result = OcrTextExtractor().extract(str(missing))

    assert isinstance(result, OcrTextResult)
    assert result.screenshot_exists is False
    assert result.observed_text is None
    assert result.executable_actions == []


def test_ocr_result_to_dict_shape_for_missing_file(tmp_path):
    missing = tmp_path / "missing.png"

    data = OcrTextExtractor().extract(str(missing)).to_dict()

    assert data["screenshot_path"]
    assert data["screenshot_exists"] is False
    assert data["observed_text"] is None
    assert data["executable_actions"] == []


def test_ocr_extractor_never_generates_actions(tmp_path):
    missing = tmp_path / "missing.png"

    result = OcrTextExtractor().extract(str(missing))

    forbidden = {"click", "type", "send", "submit", "buy", "delete"}

    assert result.executable_actions == []
    assert all(action.get("type") not in forbidden for action in result.executable_actions)
