from agent_factory.observers.screen_text_extractor import OcrTextExtractor


def test_ocr_clean_text_removes_empty_and_symbol_noise():
    raw = """
    !!!

    Can you see this Ari?

    @@@ ### ///
    """

    cleaned = OcrTextExtractor().clean_text(raw)

    assert cleaned == "Can you see this Ari?"


def test_ocr_clean_text_normalizes_spacing_and_quotes():
    raw = '  “Can   you   see   this   Ari?”  '

    cleaned = OcrTextExtractor().clean_text(raw)

    assert cleaned == '"Can you see this Ari?"'


def test_ocr_clean_text_returns_none_when_no_usable_content():
    raw = """
    !!!
    @@
    12345
    """

    cleaned = OcrTextExtractor().clean_text(raw)

    assert cleaned is None


def test_ocr_result_has_raw_and_cleaned_fields_for_missing_file(tmp_path):
    missing = tmp_path / "missing.png"

    data = OcrTextExtractor().extract(str(missing)).to_dict()

    assert "raw_observed_text" in data
    assert "cleaned_observed_text" in data
    assert data["executable_actions"] == []
