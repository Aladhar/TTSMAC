from manga_reader.cleanup import clean_ocr_text, clean_tts_text


def test_clean_ocr_text_normalizes_spaces_and_ligatures():
    assert clean_ocr_text("  ﬁght   me  ") == "fight me"


def test_clean_tts_text_flattens_display_lines():
    assert clean_tts_text("hello\nthere …") == "hello there ..."
