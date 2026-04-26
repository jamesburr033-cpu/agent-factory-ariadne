from PIL import Image

from agent_factory.observers.screen_text_extractor import OcrTextExtractor


def test_ocr_crop_image_uses_active_window_box(tmp_path):
    image = Image.new("RGB", (100, 100), "white")

    cropped = OcrTextExtractor()._crop_image(
        image,
        {"left": 10, "top": 20, "right": 60, "bottom": 80},
    )

    assert cropped.width == 50
    assert cropped.height == 60


def test_ocr_crop_image_falls_back_when_invalid_box(tmp_path):
    image = Image.new("RGB", (100, 100), "white")

    cropped = OcrTextExtractor()._crop_image(
        image,
        {"left": 90, "top": 90, "right": 10, "bottom": 10},
    )

    assert cropped.width == 100
    assert cropped.height == 100
