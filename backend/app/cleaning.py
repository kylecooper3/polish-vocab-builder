"""Stage 2: turn raw pages into clean paragraphs that spaCy can read well."""

import re
import unicodedata
from collections import Counter

from app.translations import load_lemma_options

# A line that is only a page number: "12", "- 12 -", "12 / 300", "Strona 12", "XIV".
PAGE_NUMBER_LINE = re.compile(
    r"^\W*(?:strona\s+)?\d{1,4}(?:\s*/\s*\d{1,4})?\W*$|^\W*[IVXLC]+\W*$",
    re.IGNORECASE,
)
ROMAN_LINE = re.compile(r"^\W*[ivxlc]+\W*$")

SOFT_HYPHEN_AT_LINE_END = re.compile(r"­(?=[ \t]*$)", re.MULTILINE)

# A word broken across a line: "książ-\nka" becomes "książka".
LINE_BREAK_HYPHEN = re.compile(r"(\w+)[-‐]\n\s*([a-ząćęłńóśźż]\w*)")

# A real compound keeps its hyphen: "Skłodowska-\nCurie" becomes "Skłodowska-Curie".
LINE_BREAK_COMPOUND = re.compile(r"(?<=\w)([-‐])\n\s*(?=[A-ZĄĆĘŁŃÓŚŹŻ])")

# A footnote marker stuck to a word: "jegomościa1". Left in place, the digit makes
# the whole word fail the letters-only check later, and it would never be counted.
FOOTNOTE_MARKER = re.compile(r"(?<=[^\W\d_])\d{1,3}\b")

PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

# How many lines at the top and bottom of a page can be a header or footer.
EDGE_LINES = 2
MAX_HEADER_LENGTH = 80

# Polish books can quote some Greek or Russian, but "j" alone is about 2% of letters.
MAX_NON_LATIN_SHARE = 0.01


def looks_garbled(text: str) -> bool:
    """Is too much of this text not Latin letters to be a usable Polish book?

    A PDF can look perfect on screen while its hidden text layer maps letters to the
    wrong characters. In one real book every "j" came out as the Telugu letter "గ",
    and some spaces vanished too, so it can't be repaired without guessing.
    """
    letters = [char for char in text if char.isalpha() or unicodedata.category(char) == "Co"]
    if not letters:
        return False
    unexpected = sum(1 for char in letters if "LATIN" not in unicodedata.name(char, ""))
    return unexpected / len(letters) > MAX_NON_LATIN_SHARE


def clean_pages(pages: list[str]) -> str:
    """Run every cleaning step and return one string of paragraphs."""
    pages = [_normalize_characters(page) for page in pages]
    pages = [_remove_page_numbers(page) for page in pages]
    pages = _remove_repeated_headers(pages)
    # Joining with a single newline lets a sentence or a hyphenated word carry
    # on across a page break.
    text = "\n".join(pages)
    text = LINE_BREAK_HYPHEN.sub(_rejoin, text)
    text = LINE_BREAK_COMPOUND.sub(r"\1", text)
    text = FOOTNOTE_MARKER.sub("", text)
    return _normalize_whitespace(text)


def _rejoin(match: re.Match) -> str:
    """Join a word split at a line end, unless it's a compound like "biało-czerwona".

    A compound keeps its hyphen when the joined word isn't a known spelling but both
    halves are, because "białoczerwona" isn't a word while "biało" and "czerwona" are.
    """
    left, right = match.groups()
    spellings = load_lemma_options().options
    joined = left + right
    if joined.lower() not in spellings and left.lower() in spellings and right.lower() in spellings:
        return f"{left}-{right}"
    return joined


def _normalize_characters(text: str) -> str:
    # NFKC gives every letter one standard encoding. PDFs may store "ą" as "a"
    # plus a separate tail, or "fi" as a single ligature, which would otherwise
    # look like different words.
    text = unicodedata.normalize("NFKC", text)
    # U+00AD is a "soft" hyphen. At a line end it marks a split word, so it becomes a
    # normal hyphen for the rejoining step. Anywhere else it's invisible, so it goes.
    text = SOFT_HYPHEN_AT_LINE_END.sub("-", text)
    return text.replace("­", "")


def _is_page_number(line: str) -> bool:
    # Lowercase Roman numerals are excluded: a line holding only "i" is far more
    # likely to be the Polish word for "and" than a page number.
    return bool(PAGE_NUMBER_LINE.match(line)) and not ROMAN_LINE.match(line)


def _remove_page_numbers(page: str) -> str:
    return "\n".join(line for line in page.splitlines() if not _is_page_number(line))


def _header_key(line: str) -> str:
    # Ignore digits so "Rozdział 3" and "Rozdział 4" count as the same header.
    return re.sub(r"\d+", "", line).strip().lower()


def _edge_line_indexes(lines: list[str]) -> set[int]:
    filled = [index for index, line in enumerate(lines) if line.strip()]
    return set(filled[:EDGE_LINES] + filled[-EDGE_LINES:])


def _remove_repeated_headers(pages: list[str]) -> list[str]:
    """Drop short lines that repeat at the top or bottom of many pages."""
    split_pages = [page.splitlines() for page in pages]

    seen_on_pages = Counter()
    for lines in split_pages:
        seen_on_pages.update(
            {
                _header_key(lines[index])
                for index in _edge_line_indexes(lines)
                if len(lines[index]) <= MAX_HEADER_LENGTH
            }
        )

    # At least 3 pages, and at least 10% of a long book.
    threshold = max(3, len(pages) // 10)
    headers = {
        key for key, pages_seen in seen_on_pages.items() if key and pages_seen >= threshold
    }

    cleaned = []
    for lines in split_pages:
        edges = _edge_line_indexes(lines)
        cleaned.append(
            "\n".join(
                line
                for index, line in enumerate(lines)
                if not (index in edges and _header_key(line) in headers)
            )
        )
    return cleaned


def _normalize_whitespace(text: str) -> str:
    # A single newline is only where the line happened to wrap, so it becomes a
    # space. A blank line marks a real paragraph, so those stay.
    paragraphs = (" ".join(part.split()) for part in PARAGRAPH_BREAK.split(text))
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)
