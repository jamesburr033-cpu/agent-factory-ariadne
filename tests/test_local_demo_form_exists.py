from pathlib import Path


def test_gpu_deal_form_exists_and_submit_is_disabled():
    html_path = Path("examples/gpu_deal_form.html")
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "Ariadne GPU Deal Evaluator" in html
    assert 'id="submit"' in html
    assert "disabled" in html
