from agent_factory.observers.screen_text_extractor import OcrTextExtractor


def test_ocr_text_quality_good_for_clean_sentence():
    result = OcrTextExtractor().score_text_quality("If you can see this, tell me a joke.")

    assert result["score"] >= 0.8
    assert result["rating"] == "good"
    assert result["warnings"] == []


def test_ocr_text_quality_flags_symbol_noise():
    result = OcrTextExtractor().score_text_quality(r"[ff ||| @@@ \\\\ [] [] 12345 @@@ UI")

    assert result["score"] < 0.8
    assert result["rating"] in {"usable", "noisy", "poor"}
    assert result["warnings"]


def test_ocr_text_quality_unavailable_when_empty():
    result = OcrTextExtractor().score_text_quality(None)

    assert result["score"] == 0.0
    assert result["rating"] == "unavailable"
    assert result["warnings"]


def test_ocr_confidence_tracks_quality():
    extractor = OcrTextExtractor()

    assert extractor._confidence_from_quality({"rating": "good"}) == "high"
    assert extractor._confidence_from_quality({"rating": "usable"}) == "medium"
    assert extractor._confidence_from_quality({"rating": "noisy"}) == "low"
