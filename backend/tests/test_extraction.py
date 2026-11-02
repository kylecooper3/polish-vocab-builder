import pytest

from app.extraction import (
    UnreadableFileError,
    UnsupportedFormatError,
    _html_to_text,
    extract_pages,
)


def test_pdf_returns_one_string_per_page(make_pdf):
    data = make_pdf(["<p>Pierwsza strona</p>", "<p>Druga strona</p>"])
    pages = extract_pages(data, "book.pdf")
    assert len(pages) == 2
    assert "Pierwsza" in pages[0]
    assert "Druga" in pages[1]


def test_pdf_keeps_polish_letters(make_pdf):
    data = make_pdf(["<p>Zażółć gęślą jaźń</p>"])
    assert "Zażółć gęślą jaźń" in extract_pages(data, "book.pdf")[0]


def test_epub_returns_text_without_html(make_epub):
    data = make_epub(["<html><body><p>Zażółć <b>gęślą</b> jaźń</p></body></html>"])
    text = "".join(extract_pages(data, "book.epub"))
    assert "Zażółć gęślą jaźń" in text
    assert "<b>" not in text


def test_epub_keeps_paragraphs_apart(make_epub):
    data = make_epub(["<html><body><p>koniec</p><p>Nowy</p></body></html>"])
    assert "koniecNowy" not in "".join(extract_pages(data, "book.epub"))


def test_epub_skips_style_and_script_contents(make_epub):
    html = "<html><body><style>p {color: red}</style><script>alert(1)</script><p>Tekst</p></body></html>"
    text = "".join(extract_pages(make_epub([html]), "book.epub"))
    assert "Tekst" in text
    assert "color" not in text
    assert "alert" not in text


@pytest.mark.parametrize(
    "unwanted",
    [
        "<nav><ol><li>Spis treści</li></ol></nav>",
        "<sup>1</sup>",
        '<a epub:type="noteref">1</a>',
        '<aside epub:type="footnote">Przypis autora</aside>',
        '<section epub:type="footnotes">Przypisy</section>',
        '<section class="x" epub:type="bodymatter endnotes">Przypisy</section>',
        '<div id="book-text"><div id="footnotes">Przypisy</div></div>',
        '<div id="book-text"><p class="info">Licencja</p></div>',
        '<div id="book-text"><div class="fundraising">Wesprzyj</div></div>',
    ],
)
def test_epub_removes_non_book_content(unwanted):
    html = f"<html><body>{unwanted}<p>Tekst</p></body></html>".encode()
    assert " ".join(_html_to_text(html).split()) == "Tekst"


def test_epub_keeps_ordinary_info_class_outside_wolne_lektury_books():
    html = b'<html><body><p class="info">Tekst</p></body></html>'
    assert "Tekst" in _html_to_text(html)


def test_extension_check_ignores_case(make_pdf):
    assert extract_pages(make_pdf(["<p>Tekst</p>"]), "BOOK.PDF")


def test_unsupported_extension_is_rejected():
    with pytest.raises(UnsupportedFormatError):
        extract_pages(b"hello", "notes.txt")


@pytest.mark.parametrize("filename", ["fake.pdf", "fake.epub"])
def test_corrupt_file_is_rejected(filename):
    with pytest.raises(UnreadableFileError):
        extract_pages(b"this is not a real book", filename)
