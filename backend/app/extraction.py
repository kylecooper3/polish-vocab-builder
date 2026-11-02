"""Stage 1: turn an uploaded PDF or EPUB into a list of raw text pages."""

import tempfile
from pathlib import Path

import ebooklib
import pymupdf
from bs4 import BeautifulSoup
from ebooklib import epub

# HTML tags that start a new line when displayed. Without marking them,
# "<p>koniec</p><p>Nowy</p>" would extract as the single word "koniecNowy".
BLOCK_TAGS = [
    "p", "div", "br", "li", "tr", "blockquote", "section", "article",
    "h1", "h2", "h3", "h4", "h5", "h6",
]

# Parts of an EPUB that aren't the book's own text. Counting them skews the word
# list: in testing, the phrase "przypis edytorski" (editor's note) in the footnotes
# made "przypis" outrank the story's main character.
NON_BOOK_SELECTOR = ", ".join(
    [
        "head", "script", "style",
        # Contents pages and footnote markers ("<sup>1</sup>"), in any EPUB.
        "nav", "sup",
        # Footnotes, as marked by the EPUB standard.
        r'[epub\:type~="noteref"]',
        r'[epub\:type~="footnote"]', r'[epub\:type~="footnotes"]',
        r'[epub\:type~="endnote"]', r'[epub\:type~="endnotes"]',
        r'[epub\:type~="rearnote"]', r'[epub\:type~="rearnotes"]',
        # Wolne Lektury's footnotes, title page, notices and fundraising pages.
        "#book-text #footnotes", "#book-text .title-page", "#book-text .info",
        "#book-text .minor-info", "#book-text .fundraising",
    ]
)


class UnsupportedFormatError(Exception):
    """The file is not a PDF or an EPUB."""


class UnreadableFileError(Exception):
    """The file claims to be a PDF or EPUB but cannot be opened."""


def extract_pages(data: bytes, filename: str) -> list[str]:
    """Pick an extractor based on the file extension."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(data)
    if suffix == ".epub":
        return extract_epub(data)
    raise UnsupportedFormatError(f"Unsupported file type: {suffix or 'none'}")


def extract_pdf(data: bytes) -> list[str]:
    # Parsers raise many exception types on malformed uploads, so catch broadly
    # and report them all as one clear error.
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            if doc.needs_pass:
                raise UnreadableFileError("This PDF is password-protected.")
            return [page.get_text() for page in doc]
    except UnreadableFileError:
        raise
    except Exception as exc:
        raise UnreadableFileError("This file could not be read as a PDF.") from exc


def extract_epub(data: bytes) -> list[str]:
    try:
        # ebooklib needs a real file path. The temporary folder and the book
        # inside it are deleted as soon as this block ends.
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "upload.epub"
            path.write_bytes(data)
            book = epub.read_epub(str(path), options={"ignore_ncx": True})

        # The spine is the EPUB's reading order.
        items = (book.get_item_with_id(item_id) for item_id, _ in book.spine)
        return [
            _html_to_text(item.get_content())
            for item in items
            if item is not None and item.get_type() == ebooklib.ITEM_DOCUMENT
        ]
    except Exception as exc:
        raise UnreadableFileError("This file could not be read as an EPUB.") from exc


def _html_to_text(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select(NON_BOOK_SELECTOR):
        tag.decompose()
    for tag in soup.find_all(BLOCK_TAGS):
        tag.insert_after("\n\n")
    return soup.get_text()
