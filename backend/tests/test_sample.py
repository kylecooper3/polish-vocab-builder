"""Run a real public-domain book through the whole pipeline."""

from pathlib import Path

from app.cleaning import clean_pages
from app.extraction import extract_pages
from app.lemmas import analyze_text

SAMPLE = Path(__file__).parents[2] / "sample" / "katarynka.epub"


def test_sample_book_produces_a_sensible_word_list(nlp):
    text = clean_pages(extract_pages(SAMPLE.read_bytes(), SAMPLE.name))
    result = analyze_text(text, nlp)

    assert result.total_tokens > 3000
    assert result.unique_lemmas > 500

    lemmas = {entry.lemma: entry for entry in result.lemmas}
    # "katarynka" is the story's subject and appears in many inflected forms.
    assert lemmas["katarynka"].count > 5
    assert len(lemmas["katarynka"].forms) > 1
    example = lemmas["katarynka"].example.lower()
    assert any(form in example for form in lemmas["katarynka"].forms)


def test_sample_book_excludes_publisher_material(nlp):
    text = clean_pages(extract_pages(SAMPLE.read_bytes(), SAMPLE.name))
    result = analyze_text(text, nlp)
    lemmas = {entry.lemma: entry for entry in result.lemmas}

    # These come from the footnotes, license notice and fundraising pages.
    assert not {"przypis", "redakcyjny", "fundacja", "licencja"} & set(lemmas)

    # Its first use is "jegomościa1", which a footnote marker used to hide.
    assert "jegomość" in lemmas
    assert not any(char.isdigit() for char in lemmas["jegomość"].example)
