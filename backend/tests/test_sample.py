"""Run a real public-domain book through the whole pipeline."""

from pathlib import Path

from app.cleaning import clean_pages
from app.extraction import extract_pages
from app.lemmas import AnalysisResult, analyze_text
from scripts.build_demo_data import OUTPUT_FILE, analyze_sample

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


def test_demo_data_matches_the_current_pipeline():
    # If this fails, the live demo is out of date: run python -m scripts.build_demo_data
    saved = AnalysisResult.model_validate_json(OUTPUT_FILE.read_text(encoding="utf-8"))
    assert saved == analyze_sample()


def test_sample_book_excludes_publisher_material(nlp):
    text = clean_pages(extract_pages(SAMPLE.read_bytes(), SAMPLE.name))
    result = analyze_text(text, nlp)
    lemmas = {entry.lemma: entry for entry in result.lemmas}

    # These come from the footnotes, license notice and fundraising pages.
    assert not {"przypis", "redakcyjny", "fundacja", "licencja"} & set(lemmas)

    # Its first use is "jegomościa1", which a footnote marker used to hide.
    assert "jegomość" in lemmas
    assert not any(char.isdigit() for char in lemmas["jegomość"].example)


def test_match_stats_add_up_to_the_whole_book(nlp):
    text = clean_pages(extract_pages(SAMPLE.read_bytes(), SAMPLE.name))
    result = analyze_text(text, nlp)
    stats = result.match_stats
    groups = [stats.in_dictionary, stats.merged, stats.unresolved, stats.no_match]

    assert sum(group.occurrences for group in groups) == result.total_tokens
    assert stats.merged.rows == len(result.merges)
    assert stats.merged.occurrences == sum(merge.count for merge in result.merges)


def test_example_marks_always_point_at_a_form_of_that_word(nlp):
    text = clean_pages(extract_pages(SAMPLE.read_bytes(), SAMPLE.name))
    result = analyze_text(text, nlp)
    for entry in [*result.lemmas, *result.merges]:
        assert entry.example_spans, entry
        for start, end in entry.example_spans:
            assert entry.example[start:end].lower() in entry.forms, entry
