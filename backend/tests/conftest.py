"""Shared test helpers. pytest loads this file automatically."""

from pathlib import Path

import pymupdf
import pytest
from ebooklib import epub

from app.lemmas import load_model


@pytest.fixture(scope="session")
def nlp():
    return load_model()


@pytest.fixture
def make_pdf():
    """Build a PDF in memory with one page per HTML string."""

    def _make(page_html: list[str]) -> bytes:
        with pymupdf.open() as doc:
            for html in page_html:
                page = doc.new_page()
                page.insert_htmlbox(pymupdf.Rect(50, 50, 550, 750), html)
            return doc.tobytes()

    return _make


@pytest.fixture
def make_epub(tmp_path: Path):
    """Build an EPUB on disk with one chapter per HTML string."""

    def _make(chapter_html: list[str]) -> bytes:
        book = epub.EpubBook()
        book.set_identifier("test-book")
        book.set_title("Test")
        book.set_language("pl")
        chapters = []
        for index, html in enumerate(chapter_html):
            chapter = epub.EpubHtml(title=f"Chapter {index}", file_name=f"c{index}.xhtml", lang="pl")
            chapter.content = html
            book.add_item(chapter)
            chapters.append(chapter)
        book.spine = chapters
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        path = tmp_path / "test.epub"
        epub.write_epub(str(path), book)
        return path.read_bytes()

    return _make
