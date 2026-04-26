from agent_factory.observers.screen_text_extractor import OcrTextExtractor


def test_extract_best_observed_text_selects_useful_phrase():
    text = """
    [By "new 1 - Notepad++ - a |
    BBS. G8| 4H acl\\ el eS\\ER
    7] [ff you can see this, tell we @ Joke.
    Q Search 2uauenau &
    """

    best = OcrTextExtractor().extract_best_observed_text(text)

    assert best == "If you can see this, tell me a Joke."


def test_extract_best_observed_text_returns_none_for_noise():
    text = """
    !!!
    12345
    @@@ ||| ///
    """

    best = OcrTextExtractor().extract_best_observed_text(text)

    assert best is None


def test_phrase_candidate_scores_clean_sentence_higher_than_ui_noise():
    extractor = OcrTextExtractor()

    clean = extractor._score_phrase_candidate("If you can see this, tell me a joke.")
    noisy = extractor._score_phrase_candidate("BBS. G8| 4H acl\\ el eS\\ER")

    assert clean > noisy


def test_ocr_result_shape_includes_best_observed_text_for_missing_file(tmp_path):
    missing = tmp_path / "missing.png"

    data = OcrTextExtractor().extract(str(missing)).to_dict()

    assert "best_observed_text" in data
    assert data["best_observed_text"] is None
    assert data["executable_actions"] == []
