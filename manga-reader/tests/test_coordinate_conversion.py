import fitz

from manga_reader.pdf_renderer import render_page


def test_render_page_uses_image_coordinate_metadata(tmp_path, monkeypatch):
    import manga_reader.pdf_renderer as pdf_renderer

    page_cache_dir = tmp_path / "cache" / "pages"
    monkeypatch.setattr(pdf_renderer, "PAGE_CACHE_DIR", page_cache_dir)

    pdf_path = tmp_path / "one_page.pdf"
    doc = fitz.open()
    doc.new_page(width=100, height=200)
    doc.save(pdf_path)
    doc.close()

    page_data = render_page(str(pdf_path), 0, zoom=2.0)

    assert page_data["pdf_width"] == 100.0
    assert page_data["pdf_height"] == 200.0
    assert page_data["image_width"] == 200
    assert page_data["image_height"] == 400
    assert page_data["zoom"] == 2.0
    assert page_data["image_path"].endswith("page_0000.png")
