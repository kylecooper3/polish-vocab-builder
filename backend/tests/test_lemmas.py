from collections import Counter

import pytest
from spacy.tokens import MorphAnalysis
from spacy.vocab import Vocab

from app.lemmas import (
    _Tally,
    analyze_text,
    choose_lemma,
    resolve_lemmas,
    split_into_chunks,
    split_pronoun,
)
from app.translations import LemmaOptions


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


def test_a_wrong_noun_lemma_is_corrected_in_a_real_sentence(nlp):
    result = analyze_text("Bawił się małym krążkiem.", nlp)
    assert _entry(result, "krążk") is None
    entry = _entry(result, "krążek")
    assert entry.count == 1
    assert "disc" in entry.translation


def test_a_made_up_word_stays_in_the_list_with_no_translation(nlp):
    result = analyze_text("Wtedy kupił nową zbruglawą sepulkę.", nlp)
    assert any(entry.translation == "" and "sepulkę" in entry.forms for entry in result.lemmas)


def test_rocznie_keeps_its_own_meaning(nlp):
    entry = _entry(analyze_text("Zarabiał tysiąc rubli rocznie w tej firmie.", nlp), "rocznie")
    assert "annually" in entry.translation


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


def _bolded(entry):
    return [entry.example[start:end] for start, end in entry.example_spans]


def test_example_marks_only_words_counted_under_that_row(nlp):
    # spaCy counts the first "To" under "ten" and the second under "to".
    result = analyze_text("To dziecko to mój syn.", nlp)
    assert _entry(result, "ten").example_spans == [(0, 2)]
    assert _entry(result, "to").example_spans == [(11, 13)]


def test_example_marks_every_use_of_the_word_in_its_sentence(nlp):
    entry = _entry(analyze_text("Jak ten czas leci, jak ten czas leci.", nlp), "ten")
    assert _bolded(entry) == ["ten", "ten"]


def test_example_marks_the_right_place_after_extra_spaces_are_removed(nlp):
    entry = _entry(analyze_text("Mój   stary\npies bardzo lubi długie spacery.", nlp), "pies")
    assert entry.example.startswith("Mój stary pies")
    assert _bolded(entry) == ["pies"]


def test_example_marks_only_the_sentence_it_kept(nlp):
    text = "Pies! Mój stary pies bardzo lubi długie spacery po lesie."
    entry = _entry(analyze_text(text, nlp), "pies")
    assert entry.example.startswith("Mój stary")
    assert entry.example_spans == [(10, 14)]


def test_a_repeated_sentence_does_not_add_more_marks(nlp):
    entry = _entry(analyze_text("Mój pies śpi.\n\nMój pies śpi.", nlp), "pies")
    assert entry.example_spans == [(4, 8)]


def _options(real_words=(), **forms):
    return LemmaOptions(real_words=set(real_words), options=forms)


def _chosen(form, lemma, pos, options, word_forms=None, rows=()):
    return choose_lemma(form, lemma, pos, options, word_forms or {}, set(rows))


def test_agreement_keeps_spacys_lemma():
    options = _options({"mieć"}, mam="verb=mieć,mamić")
    choice = _chosen("mam", "mieć", "VERB", options)
    assert (choice.lemma, choice.group) == ("mieć", "in_dictionary")


def test_a_made_up_lemma_takes_the_only_match():
    options = _options({"krążek"}, krążkiem="noun=krążek")
    choice = _chosen("krążkiem", "krążk", "NOUN", options)
    assert (choice.lemma, choice.group, choice.method) == ("krążek", "merged", "only_match")


def test_an_entry_that_is_only_a_form_does_not_count_as_a_real_word():
    options = _options({"rozumieć", "rozum"}, rozumie="noun=rozum;verb=rozumieć")
    assert _chosen("rozumie", "rozumie", "VERB", options).lemma == "rozumieć"


def test_part_of_speech_chooses_between_words():
    options = _options({"rozumieć", "rozum"}, rozumie="noun=rozum;verb=rozumieć")
    assert _chosen("rozumie", "rozumie", "NOUN", options).lemma == "rozum"


def test_a_wrong_tag_can_still_reach_the_only_word():
    options = _options({"donieść"}, doniósł="verb=donieść")
    assert _chosen("doniósł", "doniósł", "NOUN", options).lemma == "donieść"


def test_a_real_word_that_does_not_fit_the_form_is_replaced():
    options = _options({"jeść", "jechać"}, jedziemy="verb=jechać")
    choice = _chosen("jedziemy", "jeść", "VERB", options)
    assert (choice.lemma, choice.group) == ("jechać", "merged")


def test_a_real_word_is_not_replaced_by_the_form_itself():
    # "ze" is its own entry, but it's only another spelling of "z" ("with").
    options = _options({"z", "ze"}, ze="prep=ze")
    choice = _chosen("ze", "z", "ADP", options)
    assert (choice.lemma, choice.group) == ("z", "in_dictionary")


def test_a_real_word_is_kept_when_several_others_fit():
    options = _options({"on", "jeść", "być"}, je="verb=być,jeść")
    assert _chosen("je", "on", "VERB", options).lemma == "on"


def test_a_tie_is_settled_by_a_word_already_in_the_book():
    options = _options({"robot", "robota"}, robocie="noun=robot,robota")
    choice = _chosen("robocie", "robocie", "NOUN", options, rows={"robot"})
    assert (choice.lemma, choice.method) == ("robot", "tie_break")


def test_a_tie_with_no_clear_answer_stays_unresolved():
    options = _options({"robot", "robota"}, robocie="noun=robot,robota")
    for rows in (set(), {"robot", "robota"}):
        choice = _chosen("robocie", "robocie", "NOUN", options, rows=rows)
        assert (choice.lemma, choice.group) == ("robocie", "unresolved")


def test_the_form_table_is_the_fallback():
    choice = _chosen("największej", "największej", "ADJ", _options(), {"największej": ["największy"]})
    assert (choice.lemma, choice.group) == ("największy", "merged")


def test_a_word_found_nowhere_stays_as_it_is():
    choice = _chosen("sepulki", "sepulka", "NOUN", _options())
    assert (choice.lemma, choice.group) == ("sepulka", "no_match")


@pytest.mark.parametrize("form", ["bylem", "zdrów", "dziw", "laty", "lewo", "kuzynka"])
def test_known_false_matches_are_left_alone(form):
    options = _options(set(), **{form: "noun=inne"})
    assert _chosen(form, "x", "NOUN", options).lemma == "x"


def _reading(count, example="", good=False, sentence=-1, spans=None, stop=0):
    return _Tally(
        count=count, stop_count=stop, example=example, example_is_good=good,
        example_sentence=sentence, example_spans=spans or [],
    )


def _readings(*items):
    readings = {}
    for lemma, form, pos, settled, tally in items:
        tally.forms[form] = tally.count
        tally.pos[pos] = tally.count
        readings[(lemma, form, pos, settled)] = tally
    return readings


def test_forms_of_one_spacy_row_can_go_to_different_words():
    options = _options({"pies", "kot"}, aa="noun=pies", bb="noun=kot")
    rows, merges, _ = resolve_lemmas(
        _readings(("xx", "aa", "NOUN", False, _reading(1)), ("xx", "bb", "NOUN", False, _reading(2))),
        options, {},
    )
    assert (rows["pies"].count, rows["kot"].count) == (1, 2)
    assert {(merge.from_lemma, merge.to_lemma) for merge in merges} == {("xx", "pies"), ("xx", "kot")}


def test_a_settled_pronoun_is_not_checked_again():
    options = _options({"ona", "jej"}, jej="pron=jej,ona")
    rows, merges, _ = resolve_lemmas(_readings(("ona", "jej", "PRON", True, _reading(3))), options, {})
    assert rows["ona"].count == 3
    assert merges == []


def test_merging_combines_counts_forms_and_stopwords():
    options = _options({"mebel"}, meble="noun=mebel", mebli="noun=mebel")
    rows, _, _ = resolve_lemmas(
        _readings(
            ("mebel", "mebli", "NOUN", False, _reading(2)),
            ("mebl", "meble", "NOUN", False, _reading(1, stop=1)),
        ),
        options, {},
    )
    assert set(rows) == {"mebel"}
    assert rows["mebel"].count == 3
    assert rows["mebel"].stop_count == 1
    assert rows["mebel"].forms == Counter({"mebli": 2, "meble": 1})
    assert rows["mebel"].pos["NOUN"] == 3


def test_a_row_keeps_the_earliest_good_example():
    options = _options({"mebel"}, meble="noun=mebel", mebli="noun=mebel")
    rows, _, _ = resolve_lemmas(
        _readings(
            ("mebel", "mebli", "NOUN", False, _reading(1, "Late.", True, 9, [(0, 5)])),
            ("mebl", "meble", "NOUN", False, _reading(1, "Early.", True, 2, [(0, 6)])),
        ),
        options, {},
    )
    assert rows["mebel"].example == "Early."
    assert rows["mebel"].example_spans == [(0, 6)]


def test_a_good_example_beats_a_short_one():
    options = _options({"mebel"}, meble="noun=mebel", mebli="noun=mebel")
    rows, _, _ = resolve_lemmas(
        _readings(
            ("mebel", "mebli", "NOUN", False, _reading(1, "Mebli!", False, 1, [(0, 5)])),
            ("mebl", "meble", "NOUN", False, _reading(1, "Stare meble tu stoją razem.", True, 8, [(6, 11)])),
        ),
        options, {},
    )
    assert rows["mebel"].example.startswith("Stare")
    assert rows["mebel"].example_is_good is True


def test_forms_in_the_same_sentence_are_all_marked():
    options = _options({"mebel"}, meble="noun=mebel", mebli="noun=mebel")
    sentence = "Stare meble i mebli."
    rows, _, _ = resolve_lemmas(
        _readings(
            ("mebel", "mebli", "NOUN", False, _reading(1, sentence, False, 3, [(14, 19)])),
            ("mebl", "meble", "NOUN", False, _reading(1, sentence, False, 3, [(6, 11)])),
        ),
        options, {},
    )
    assert rows["mebel"].example_spans == [(6, 11), (14, 19)]


def test_stats_put_every_spacy_row_in_one_group_and_count_every_use():
    options = _options({"mebel", "krążek", "palec", "palce"},
                       mebli="noun=mebel", meble="noun=mebel", krążkiem="noun=krążek", palcach="noun=palce,palec")
    _, _, stats = resolve_lemmas(
        _readings(
            ("mebel", "mebli", "NOUN", False, _reading(2)),
            ("krążk", "krążkiem", "NOUN", False, _reading(3)),
            ("palc", "palcach", "NOUN", False, _reading(5)),
            ("sepulka", "sepulki", "NOUN", False, _reading(4)),
        ),
        options, {},
    )
    assert (stats.in_dictionary.rows, stats.in_dictionary.occurrences) == (1, 2)
    assert (stats.merged.rows, stats.merged.occurrences) == (1, 3)
    assert (stats.unresolved.rows, stats.unresolved.occurrences) == (1, 5)
    assert (stats.no_match.rows, stats.no_match.occurrences) == (1, 4)


def test_a_row_split_between_groups_counts_once_under_its_biggest_group():
    options = _options({"pies"}, aa="noun=pies")
    _, _, stats = resolve_lemmas(
        _readings(("xx", "aa", "NOUN", False, _reading(5)), ("xx", "bb", "NOUN", False, _reading(1))),
        options, {},
    )
    assert (stats.merged.rows, stats.merged.occurrences) == (1, 5)
    assert (stats.no_match.rows, stats.no_match.occurrences) == (0, 1)


def test_merges_are_described_with_the_biggest_first():
    options = _options({"mebel", "krążek", "meble"}, krążkiem="noun=krążek", meble="noun=mebel,meble")
    _, merges, _ = resolve_lemmas(
        _readings(
            ("mebel", "mebli", "NOUN", True, _reading(2)),
            ("meble_", "meble", "NOUN", False, _reading(1, "Stare meble.", spans=[(6, 11)])),
            ("krążk", "krążkiem", "NOUN", False, _reading(3)),
        ),
        options, {},
    )
    assert [merge.from_lemma for merge in merges] == ["krążk", "meble_"]
    tied = merges[1]
    assert (tied.to_lemma, tied.count, tied.pos, tied.method, tied.new_row) == ("mebel", 1, "NOUN", "tie_break", False)
    assert tied.forms == ["meble"]
    assert tied.example_spans == [(6, 11)]
    assert (merges[0].to_lemma, merges[0].method, merges[0].new_row) == ("krążek", "only_match", True)


def test_match_stats_cover_the_whole_book(nlp):
    result = analyze_text("Bawił się małym krążkiem. Mam psa. Kupił nową zbruglawą sepulkę.", nlp)
    stats = result.match_stats
    groups = [stats.in_dictionary, stats.merged, stats.unresolved, stats.no_match]
    assert sum(group.occurrences for group in groups) == result.total_tokens
    assert stats.merged.occurrences == sum(merge.count for merge in result.merges)


@pytest.mark.parametrize(
    ("sentence", "form", "lemma"),
    [
        ("Czy my jedziemy, czy stoimy?", "jedziemy", "jechać"),
        ("Chcę iść na spacer, gdybym mógłbym tam pójść.", "mógłbym", "móc"),
        ("Moja pani mieszka tutaj od roku.", "pani", "pani"),
        ("Przyszedł ze szkoły do domu.", "ze", "z"),
        ("Zrobiłbym to przed laty, ale nie dziś.", "laty", "rok"),
        ("W pokoju stały stare meble.", "stały", "stać"),
    ],
)
def test_real_sentences_get_the_right_word(nlp, sentence, form, lemma):
    entry = _entry(analyze_text(sentence, nlp), lemma)
    assert entry is not None and form in entry.forms


def test_a_lemma_confirmed_by_the_form_table_is_not_counted_as_merged():
    choice = _chosen("kąciku", "kącik", "NOUN", _options(), {"kąciku": ["kącik"]})
    assert (choice.lemma, choice.group) == ("kącik", "in_dictionary")
