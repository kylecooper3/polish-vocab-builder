from collections import Counter

import pytest
from spacy.tokens import MorphAnalysis
from spacy.vocab import Vocab

from app.lemmas import (
    _Tally,
    analyze_text,
    correct_unknown_lemmas,
    find_correct_lemma,
    fix_verb_lemma,
    split_into_chunks,
    split_pronoun,
)


def _entry(result, lemma):
    return next((entry for entry in result.lemmas if entry.lemma == lemma), None)


def test_inflected_forms_count_as_one_lemma(nlp):
    entry = _entry(analyze_text("Mam psa. Masz kota. On ma dom.", nlp), "mieć")
    assert entry.count == 3
    assert set(entry.forms) == {"mam", "masz", "ma"}
    assert entry.pos == "VERB"


def test_past_tense_forms_join_their_real_lemma(nlp):
    result = analyze_text("Myślałem o tym. On myśli o psie. Chciałbym iść. Miałeś dom.", nlp)
    lemmas = {entry.lemma for entry in result.lemmas}
    assert not any(" " in lemma for lemma in lemmas)
    assert {"myśleć", "chcieć", "mieć"} <= lemmas
    assert _entry(result, "myśleć").count == 2
    assert set(_entry(result, "myśleć").forms) == {"myślałem", "myśli"}


def test_wrong_verb_stems_are_replaced_with_the_real_lemma(nlp):
    result = analyze_text("Wtedy poszedłem do domu. Wtedy rzekłem mu to. Wtedy poszedłbym tam.", nlp)
    lemmas = {entry.lemma for entry in result.lemmas}
    assert {"pójść", "rzec"} <= lemmas
    assert not {"poszedć", "rzekć", "poszedłbym"} & lemmas


def test_fix_verb_lemma_replaces_a_stem_not_in_the_dictionary():
    assert fix_verb_lemma("poszedłem", "poszedć", "VERB", {"poszedłem": "pójść"}, {}) == "pójść"


def test_fix_verb_lemma_replaces_a_lemma_that_is_just_the_word():
    forms = {"mógłbym": "móc"}
    assert fix_verb_lemma("mógłbym", "mógłbym", "VERB", forms, {"mógłbym": {}}) == "móc"


def test_fix_verb_lemma_keeps_a_good_lemma():
    forms = {"mam": "mamić"}
    assert fix_verb_lemma("mam", "mieć", "VERB", forms, {"mieć": {}}) == "mieć"


def test_fix_verb_lemma_skips_words_that_only_look_like_verbs():
    assert fix_verb_lemma("zdrów", "zdrów", "VERB", {"zdrów": "zdrowić"}, {}) == "zdrów"


def test_fix_verb_lemma_only_changes_verbs():
    assert fix_verb_lemma("psem", "psem", "NOUN", {"psem": "psać"}, {}) == "psem"


def test_fix_verb_lemma_keeps_spacys_answer_when_the_form_is_unknown():
    assert fix_verb_lemma("xyz", "xyzać", "VERB", {}, {}) == "xyzać"


def test_wybory_is_counted_as_wybor(nlp):
    result = analyze_text("Wybory odbędą się w niedzielę. To był trudny wybór. Nie mam wyboru.", nlp)
    assert _entry(result, "wybory") is None
    entry = _entry(result, "wybór")
    assert entry.count == 3
    assert set(entry.forms) == {"wybory", "wybór", "wyboru"}
    assert "choice" in entry.translation


def test_entries_include_a_translation(nlp):
    result = analyze_text("Mój pies lubi dom.", nlp)
    assert "dog" in _entry(result, "pies").translation
    assert "house" in _entry(result, "dom").translation


def test_filters_punctuation_digits_and_proper_nouns(nlp):
    result = analyze_text("Anna kupiła w Warszawie 12 książek, a potem wróciła.", nlp)
    lemmas = {entry.lemma for entry in result.lemmas}
    assert "książka" in lemmas
    assert not {"anna", "warszawa", "12", ",", "."} & lemmas


def test_keeps_spelled_out_numbers(nlp):
    assert _entry(analyze_text("Anna ma dwa domy.", nlp), "dwa") is not None


def test_ranks_most_frequent_first_with_no_gaps(nlp):
    result = analyze_text("Kot śpi. Kot je. Kot biega. Pies śpi.", nlp)
    assert result.lemmas[0].lemma == "kot"
    assert [entry.rank for entry in result.lemmas] == list(range(1, len(result.lemmas) + 1))
    counts = [entry.count for entry in result.lemmas]
    assert counts == sorted(counts, reverse=True)


def test_totals_match_the_entries(nlp):
    result = analyze_text("Mam psa. Masz kota. Mój pies je.", nlp)
    assert result.total_tokens == sum(entry.count for entry in result.lemmas)
    assert result.unique_lemmas == len(result.lemmas)


def test_lemma_gets_one_stopword_answer_across_its_forms(nlp):
    # spaCy flags "mam" and "ma" but not "masz", word by word.
    entry = _entry(analyze_text("Mam psa. Masz kota. On ma dom.", nlp), "mieć")
    assert entry.is_stopword is True


def test_content_word_is_not_a_stopword(nlp):
    assert _entry(analyze_text("Moja książka leży na stole.", nlp), "książka").is_stopword is False


def test_example_prefers_a_sentence_of_good_length(nlp):
    text = "Pies! Mój stary pies bardzo lubi długie spacery po lesie."
    assert _entry(analyze_text(text, nlp), "pies").example == (
        "Mój stary pies bardzo lubi długie spacery po lesie."
    )


def test_example_falls_back_to_a_short_sentence(nlp):
    assert _entry(analyze_text("Mam psa.", nlp), "pies").example == "Mam psa."


def test_heading_is_not_glued_to_the_first_sentence(nlp):
    text = "Katarynka\n\nMój stary pies bardzo lubi długie spacery po lesie."
    assert _entry(analyze_text(text, nlp), "pies").example == (
        "Mój stary pies bardzo lubi długie spacery po lesie."
    )


def test_empty_text_gives_empty_result(nlp):
    result = analyze_text("", nlp)
    assert result.total_tokens == 0
    assert result.lemmas == []


def test_chunks_respect_the_limit_and_lose_nothing():
    text = "\n\n".join(["akapit " * 20] * 50)
    chunks = split_into_chunks(text, max_chars=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert "".join(chunks) == text


def test_chunks_prefer_paragraph_breaks():
    chunks = split_into_chunks("aaaa bbbb\n\ncccc", max_chars=12)
    assert chunks == ["aaaa bbbb", "\n\ncccc"]


def test_chunks_handle_text_with_no_spaces():
    assert split_into_chunks("a" * 10, max_chars=4) == ["aaaa", "aaaa", "aa"]


def test_short_text_is_one_chunk():
    assert split_into_chunks("krótki tekst") == ["krótki tekst"]
    assert split_into_chunks("") == []


def _tally(forms, pos="NOUN", example="", good_example=False, stop_count=0):
    return _Tally(
        count=sum(forms.values()),
        stop_count=stop_count,
        forms=Counter(forms),
        pos=Counter({pos: sum(forms.values())}),
        example=example,
        example_is_good=good_example,
    )


def test_find_correct_lemma_uses_the_only_match():
    assert find_correct_lemma(_tally({"krążkiem": 1}), {"krążkiem": ["krążek"]}, set()) == "krążek"


def test_find_correct_lemma_breaks_a_tie_with_a_word_already_in_the_book():
    table = {"meble": ["mebel", "meble"]}
    assert find_correct_lemma(_tally({"meble": 1}), table, {"mebel"}) == "mebel"


def test_find_correct_lemma_does_not_guess_when_no_tie_break_applies():
    table = {"meble": ["mebel", "meble"]}
    assert find_correct_lemma(_tally({"meble": 1}), table, set()) is None
    assert find_correct_lemma(_tally({"meble": 1}), table, {"mebel", "meble"}) is None


def test_find_correct_lemma_leaves_unknown_words_alone():
    assert find_correct_lemma(_tally({"sepulki": 2}), {}, set()) is None


def test_find_correct_lemma_needs_every_form_to_agree():
    table = {"aa": ["pies"], "bb": ["kot"]}
    assert find_correct_lemma(_tally({"aa": 1, "bb": 1}), table, set()) is None
    assert find_correct_lemma(_tally({"aa": 1, "bb": 1}), {"aa": ["pies"]}, set()) is None


def test_correct_unknown_lemmas_merges_into_an_existing_row():
    tallies = {
        "mebel": _tally({"meble": 1, "mebli": 1}, example="Stare meble.", good_example=True),
        "mebl": _tally({"meble": 1}, example="Inne meble tutaj stoją razem.", good_example=True, stop_count=1),
    }
    correct_unknown_lemmas(tallies, {"meble": ["mebel", "meble"]}, {"mebel": {}, "meble": {}})
    assert set(tallies) == {"mebel"}
    assert tallies["mebel"].count == 3
    assert tallies["mebel"].stop_count == 1
    assert tallies["mebel"].forms == Counter({"meble": 2, "mebli": 1})
    assert tallies["mebel"].pos["NOUN"] == 3
    assert tallies["mebel"].example == "Stare meble."


def test_correct_unknown_lemmas_creates_a_row_when_needed():
    tallies = {"krążk": _tally({"krążkiem": 2}, example="Bawił się krążkiem.")}
    correct_unknown_lemmas(tallies, {"krążkiem": ["krążek"]}, {"krążek": {}})
    assert set(tallies) == {"krążek"}
    assert tallies["krążek"].count == 2
    assert tallies["krążek"].example == "Bawił się krążkiem."


def test_correct_unknown_lemmas_upgrades_to_a_better_example():
    tallies = {
        "mebel": _tally({"mebli": 1}, example="Mebli!"),
        "mebl": _tally({"meble": 1}, example="Inne meble tutaj stoją razem.", good_example=True),
    }
    correct_unknown_lemmas(tallies, {"meble": ["mebel"]}, {"mebel": {}})
    assert tallies["mebel"].example == "Inne meble tutaj stoją razem."
    assert tallies["mebel"].example_is_good is True


def test_correct_unknown_lemmas_ignores_words_that_have_a_translation():
    tallies = {"stać": _tally({"stały": 1})}
    correct_unknown_lemmas(tallies, {"stały": ["stały"]}, {"stać": {}, "stały": {}})
    assert set(tallies) == {"stać"}


def test_correct_unknown_lemmas_keeps_words_it_cannot_place():
    tallies = {"sepulka": _tally({"sepulki": 2})}
    correct_unknown_lemmas(tallies, {}, {})
    assert tallies["sepulka"].count == 2


def test_correct_unknown_lemmas_applies_merges_to_the_target():
    tallies = {"wybor": _tally({"wyborach": 1})}
    correct_unknown_lemmas(tallies, {"wyborach": ["wybory"]}, {"wybory": {}, "wybór": {}})
    assert set(tallies) == {"wybór"}


def test_a_wrong_noun_lemma_is_corrected_in_a_real_sentence(nlp):
    result = analyze_text("Bawił się małym krążkiem.", nlp)
    assert _entry(result, "krążk") is None
    entry = _entry(result, "krążek")
    assert entry.count == 1
    assert "disc" in entry.translation


def test_a_made_up_word_stays_in_the_list_with_no_translation(nlp):
    result = analyze_text("Wtedy kupił nową zbruglawą sepulkę.", nlp)
    assert any(entry.translation == "" and "sepulkę" in entry.forms for entry in result.lemmas)


def test_find_correct_lemma_skips_forms_of_unrelated_words():
    assert find_correct_lemma(_tally({"bylem": 2}), {"bylem": ["byl"]}, set()) is None


def test_rocznie_keeps_its_own_meaning(nlp):
    entry = _entry(analyze_text("Zarabiał tysiąc rubli rocznie w tej firmie.", nlp), "rocznie")
    assert "annually" in entry.translation


def _report_tallies():
    return {
        "mebel": _tally({"mebli": 2}),  # in the dictionary
        "mebl": _tally({"meble": 1}, example="Stare meble."),  # tied, then settled by "mebel"
        "krążk": _tally({"krążkiem": 3}),  # one match, and no "krążek" row yet
        "sepulka": _tally({"sepulki": 4}),  # not in the table at all
        "palc": _tally({"palcach": 5}),  # tied, and neither candidate is in the book
        "bylem": _tally({"bylem": 6}),  # an exception, so it counts as no match
    }


FORMS_FOR_REPORT = {
    "meble": ["mebel", "meble"],
    "krążkiem": ["krążek"],
    "palcach": ["palec", "palce"],
    "bylem": ["byl"],
}
DICTIONARY_FOR_REPORT = {"mebel": {}, "meble": {}, "krążek": {}, "palec": {}, "palce": {}, "byl": {}}


def test_correction_report_puts_every_row_in_one_group():
    _, stats = correct_unknown_lemmas(_report_tallies(), FORMS_FOR_REPORT, DICTIONARY_FOR_REPORT)
    assert (stats.in_dictionary.rows, stats.in_dictionary.occurrences) == (1, 2)
    assert (stats.merged.rows, stats.merged.occurrences) == (2, 4)
    assert (stats.unresolved.rows, stats.unresolved.occurrences) == (1, 5)
    assert (stats.no_match.rows, stats.no_match.occurrences) == (2, 10)


def test_correction_report_describes_each_merge():
    merges, _ = correct_unknown_lemmas(_report_tallies(), FORMS_FOR_REPORT, DICTIONARY_FOR_REPORT)
    by_source = {merge.from_lemma: merge for merge in merges}
    assert set(by_source) == {"mebl", "krążk"}

    tied = by_source["mebl"]
    assert (tied.to_lemma, tied.count, tied.pos) == ("mebel", 1, "NOUN")
    assert tied.forms == ["meble"]
    assert tied.example == "Stare meble."
    assert tied.method == "tie_break"
    assert tied.new_row is False

    only = by_source["krążk"]
    assert (only.to_lemma, only.method, only.new_row) == ("krążek", "only_match", True)


def test_correction_report_lists_the_biggest_merges_first():
    merges, _ = correct_unknown_lemmas(_report_tallies(), FORMS_FOR_REPORT, DICTIONARY_FOR_REPORT)
    assert [merge.from_lemma for merge in merges] == ["krążk", "mebl"]


def test_a_merge_keeps_the_row_it_came_from_out_of_the_final_counts():
    tallies = _report_tallies()
    correct_unknown_lemmas(tallies, FORMS_FOR_REPORT, DICTIONARY_FOR_REPORT)
    assert {"mebl", "krążk"}.isdisjoint(tallies)
    assert tallies["mebel"].count == 3


def test_match_stats_cover_the_whole_book(nlp):
    result = analyze_text("Bawił się małym krążkiem. Mam psa. Kupił nową zbruglawą sepulkę.", nlp)
    groups = [
        result.match_stats.in_dictionary,
        result.match_stats.merged,
        result.match_stats.unresolved,
        result.match_stats.no_match,
    ]
    assert sum(group.occurrences for group in groups) == result.total_tokens
    # Merged rows disappear, but each new word they created adds one back.
    new_words = {merge.to_lemma for merge in result.merges if merge.new_row}
    rows_before = sum(group.rows for group in groups)
    assert rows_before - result.match_stats.merged.rows + len(new_words) == result.unique_lemmas


def test_analysis_reports_a_real_merge(nlp):
    result = analyze_text("Bawił się małym krążkiem.", nlp)
    merge = next(merge for merge in result.merges if merge.from_lemma == "krążk")
    assert merge.to_lemma == "krążek"
    assert merge.forms == ["krążkiem"]
    assert merge.method == "only_match"
    assert "krążkiem" in merge.example


def test_empty_text_has_empty_stats(nlp):
    result = analyze_text("", nlp)
    assert result.merges == []
    assert result.match_stats.merged.rows == 0
    assert result.match_stats.no_match.occurrences == 0


def test_stats_do_not_count_a_merge_twice_when_its_target_comes_later():
    # Rows are checked in the order the book introduced them, so "mebl" can come first.
    tallies = {"mebl": _tally({"meble": 1}), "mebel": _tally({"mebli": 2})}
    _, stats = correct_unknown_lemmas(tallies, {"meble": ["mebel"]}, {"mebel": {}})
    assert stats.merged.occurrences == 1
    assert stats.in_dictionary.occurrences == 2
    assert tallies["mebel"].count == 3


@pytest.mark.parametrize(
    ("features", "form", "expected"),
    [
        ("Gender=Masc|Number=Sing", "on", "on"),
        ("Animacy=Hum|Gender=Masc|Number=Sing", "go", "on"),
        ("Gender=Fem|Number=Sing", "ją", "ona"),
        ("Gender=Neut|Number=Sing", "ono", "ono"),
        ("Gender=Neut|Number=Sing", "je", "ono"),
        ("Animacy=Hum|Gender=Masc|Number=Plur", "ich", "oni"),
        ("Animacy=Inan|Gender=Masc|Number=Plur", "je", "one"),
        ("Gender=Fem|Number=Plur", "one", "one"),
        ("Gender=Neut|Number=Plur", "one", "one"),
    ],
)
def test_split_pronoun_uses_gender_and_number(features, form, expected):
    assert split_pronoun("on", "PRON", MorphAnalysis(Vocab(), features), form) == expected


@pytest.mark.parametrize("form", ["jego", "nim", "niego", "jemu", "go", "mu"])
def test_forms_shared_with_he_are_not_shown_as_it(form):
    features = MorphAnalysis(Vocab(), "Gender=Neut|Number=Sing")
    assert split_pronoun("on", "PRON", features, form) == "on"


def test_split_pronoun_keeps_on_when_the_tags_are_missing():
    assert split_pronoun("on", "PRON", MorphAnalysis(Vocab(), ""), "on") == "on"


def test_split_pronoun_only_changes_the_pronoun_on():
    features = MorphAnalysis(Vocab(), "Gender=Fem|Number=Sing")
    assert split_pronoun("kot", "NOUN", features, "kot") == "kot"
    assert split_pronoun("on", "NOUN", features, "on") == "on"


@pytest.mark.parametrize(
    ("sentence", "form", "lemma", "meaning"),
    [
        ("On idzie do domu.", "on", "on", "he"),
        ("Ona idzie do domu.", "ona", "ona", "she"),
        ("Dziecko spało, bo ono było zmęczone.", "ono", "ono", "it"),
        ("Oni idą do domu.", "oni", "oni", "they"),
        ("One idą do domu.", "one", "one", "they"),
        ("Widzę go codziennie.", "go", "on", "he"),
        ("Widzę ją codziennie.", "ją", "ona", "she"),
        ("Znam ich dobrze.", "ich", "oni", "they"),
        ("Książki leżą na stole, weź je.", "je", "one", "they"),
    ],
)
def test_pronouns_get_their_own_rows(nlp, sentence, form, lemma, meaning):
    entry = _entry(analyze_text(sentence, nlp), lemma)
    assert form in entry.forms
    assert entry.translation == meaning
    assert entry.is_stopword is True


def test_pronoun_forms_stay_together_within_their_row(nlp):
    result = analyze_text("Ona śpi. Widzę ją codziennie. Dałem jej książkę.", nlp)
    assert set(_entry(result, "ona").forms) == {"ona", "ją", "jej"}
    assert _entry(result, "on") is None
