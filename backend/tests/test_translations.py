import json

import pytest

from app.translations import (
    OVERRIDES_FILE,
    apply_overrides,
    load_translations,
    LemmaOptions,
    load_lemma_options,
    translate,
)
from scripts.build_translations import (
    KEPT_POS,
    build_table,
    build_lemma_options,
    fold_leftovers,
    shorten_chains,
    build_word_forms,
    clean_meaning,
)


def _sense(gloss, raw=None, tags=None, **extra):
    sense = {"glosses": [gloss], "tags": tags or [], **extra}
    if raw:
        sense["raw_glosses"] = [raw]
    return sense


def _record(word, pos, *senses):
    return {"word": word, "pos": pos, "senses": list(senses)}


def test_clean_meaning_drops_explanations_in_brackets():
    assert clean_meaning("dog (Canis lupus familiaris)") == "dog"


def test_clean_meaning_shortens_very_long_text():
    assert len(clean_meaning("word " * 40)) <= 81


def test_plain_meanings_beat_regional_ones():
    table = build_table([
        _record("pies", "noun", _sense("dog (Canis)"), _sense("male fox", raw="(hunting) male fox")),
        _record("pies", "noun", _sense("chaff stick", raw="(Western Kraków) chaff stick")),
    ])
    assert "chaff stick" not in table["pies"]["noun"]
    assert table["pies"]["noun"].startswith("dog")


def test_subject_labels_are_ordinary_meanings():
    table = build_table([
        _record(
            "mecenas", "noun",
            _sense("patron, sponsor", raw="(art) patron, sponsor"),
            _sense("lawyer, advocate", raw="(law) lawyer, advocate"),
        ),
    ])
    assert table["mecenas"]["noun"] == "patron, sponsor; lawyer, advocate"


def test_specialist_meaning_is_kept_when_there_is_nothing_else():
    table = build_table([_record("kosa", "noun", _sense("old scythe", tags=["archaic"]))])
    assert table["kosa"]["noun"] == "old scythe"


def test_each_records_first_meaning_comes_first():
    table = build_table([
        _record("zamek", "noun", _sense("lock"), _sense("zip")),
        _record("zamek", "noun", _sense("castle")),
    ])
    assert table["zamek"]["noun"] == "lock; castle"


def test_keeps_at_most_two_senses():
    table = build_table([_record("x", "noun", *(_sense(word) for word in "abcdef"))])
    assert table["x"]["noun"] == "a; b"


def test_keeps_at_most_two_synonyms_per_sense():
    table = build_table([_record("x", "noun", _sense("a, b, c"), _sense("d, e, f"))])
    assert table["x"]["noun"] == "a, b; d, e"


def test_a_sense_that_only_repeats_earlier_terms_does_not_use_up_a_slot():
    table = build_table([
        _record("x", "noun", _sense("head (body part)"), _sense("head (leader)"), _sense("mind")),
    ])
    assert table["x"]["noun"] == "head; mind"


def test_grammar_labels_do_not_count_as_specialist():
    table = build_table([
        _record(
            "mówić", "verb",
            _sense("to speak", raw="(imperfective, transitive) to speak"),
            _sense("to pray", raw="(Biecz) to pray"),
        ),
    ])
    assert table["mówić"]["verb"] == "to speak"


def test_labeled_main_meaning_is_kept():
    table = build_table([
        _record(
            "oko", "noun",
            _sense("eye", raw="(anatomy) eye"),
            _sense("shiny surface of water"),
        ),
    ])
    assert table["oko"]["noun"].startswith("eye")


def test_main_meaning_tagged_as_slang_is_not_kept_over_a_plain_one():
    table = build_table([_record("x", "noun", _sense("cop", tags=["slang"]), _sense("dog"))])
    assert table["x"]["noun"] == "dog"


def test_note_containing_a_comma_is_removed_whole():
    gloss = "indicates separation, distance, loss of contact; from, away"
    table = build_table([_record("od", "prep", _sense(gloss))])
    assert table["od"]["prep"] == "from, away"


def test_repeated_terms_appear_once():
    table = build_table([
        _record("człowiek", "noun", _sense("man, human"), _sense("person"), _sense("man")),
    ])
    assert table["człowiek"]["noun"] == "man, human; person"


def test_grammar_notes_are_dropped_when_a_translation_exists():
    table = build_table([
        _record("w", "prep", _sense("denotes inessive position; in, at, on")),
        _record("nie", "particle", _sense("negation particle; no, not")),
    ])
    assert table["w"]["prep"] == "in, at"
    assert table["nie"]["particle"] == "no, not"


def test_a_word_with_only_an_explanation_keeps_it():
    table = build_table([_record("to", "pron", _sense("used to point to the object"))])
    assert table["to"]["pron"] == "used to point to the object"


def test_long_descriptions_are_dropped_when_shorter_terms_exist():
    table = build_table([
        _record("panna", "noun", _sense("someone with a Virgo star sign"), _sense("Miss")),
    ])
    assert table["panna"]["noun"] == "Miss"


def test_female_form_takes_the_quoted_meaning():
    gloss = "female equivalent of pan (“Mrs; miss”) (title before a last name)"
    table = build_table([_record("pani", "noun", _sense(gloss, form_of=[{"word": "pan"}]))])
    assert table["pani"]["noun"] == "Mrs, miss"


def test_inflected_form_follows_its_link():
    table = build_table([
        _record("schody", "noun", _sense("plural of schód", form_of=[{"word": "schód"}])),
        _record("schód", "noun", _sense("step")),
    ])
    assert table["schody"]["noun"] == "step"


def test_alternative_form_follows_its_link():
    table = build_table([
        _record("siebie", "pron", _sense("alternative form of się", alt_of=[{"word": "się"}])),
        _record("się", "pron", _sense("oneself")),
    ])
    assert table["siebie"]["pron"] == "oneself"


def test_synonym_follows_its_link():
    table = build_table([
        _record("kobita", "noun", _sense("synonym of kobieta")),
        _record("kobieta", "noun", _sense("woman")),
    ])
    assert table["kobita"]["noun"] == "woman"


def test_names_and_letters_are_left_out():
    table = build_table([
        _record("warszawa", "name", _sense("Warsaw")),
        _record("q", "character", _sense("a letter")),
    ])
    assert "warszawa" not in table
    assert "q" not in table


def test_translate_prefers_the_matching_part_of_speech():
    table = {"pan": {"noun": "gentleman", "pron": "you"}}
    assert translate("pan", "NOUN", table) == "gentleman"
    assert translate("pan", "PRON", table) == "you"


def test_translate_falls_back_to_another_part_of_speech():
    assert translate("więc", "SCONJ", {"więc": {"particle": "so"}}) == "so"


def test_translate_returns_empty_for_unknown_words():
    assert translate("xyz", "NOUN", {}) == ""


def test_override_replaces_only_the_part_of_speech_it_names():
    table = {"pan": {"noun": "lord", "pron": "you"}}
    apply_overrides(table, {"pan": {"noun": "Mr, sir"}})
    assert table["pan"] == {"noun": "Mr, sir", "pron": "you"}


def test_override_can_add_a_missing_word():
    assert apply_overrides({}, {"i": {"conj": "and"}}) == {"i": {"conj": "and"}}


def test_every_override_uses_a_real_part_of_speech_and_says_something():
    # A typo here would do nothing, without any error, so the fix would silently not apply.
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    assert overrides
    for word, entry in overrides.items():
        assert word == word.lower()
        for pos, translation in entry.items():
            assert pos in KEPT_POS, word
            assert translation.strip(), word


def test_overrides_win_over_the_automatic_translation():
    table = load_translations()
    assert translate("pies", "NOUN", table) == "dog"
    assert translate("drzewo", "NOUN", table).startswith("tree")
    assert translate("zwykle", "ADV", table) == "usually"
    assert translate("to", "PRON", table) == "this, that, it"


def test_clean_meaning_drops_notes_in_square_brackets():
    assert clean_meaning("it is known [with o (+ locative)]") == "it is known"


def test_leftover_wiki_markup_is_dropped():
    gloss = "to arise, to develop; {{syn of|pl|stać|t=to happen"
    table = build_table([_record("powstać", "verb", _sense(gloss))])
    assert table["powstać"]["verb"] == "to arise, to develop"


def test_real_data_has_the_words_that_needed_special_handling():
    table = load_translations()
    assert translate("i", "CCONJ", table) == "and"
    assert "dog" in translate("pies", "NOUN", table)
    assert "castle" in translate("zamek", "NOUN", table)
    assert "lock" in translate("zamek", "NOUN", table)
    assert translate("pani", "NOUN", table)
    assert translate("schody", "NOUN", table)
    assert translate("siebie", "PRON", table)
    assert "to say" in translate("mówić", "VERB", table)
    assert "pray" not in translate("mówić", "VERB", table)
    assert translate("w", "ADP", table).startswith("in")
    assert translate("oko", "NOUN", table).startswith("eye")
    assert translate("od", "ADP", table).startswith("from")
    assert "lawyer" in translate("mecenas", "NOUN", table)
    assert translate("zamek", "NOUN", table) == "lock; castle"
    # No raw wiki markup should reach the app, for any of the 145,000 words.
    assert "{{" not in json.dumps(table, ensure_ascii=False)


def _forms_record(word, pos, *forms):
    return {
        "word": word,
        "pos": pos,
        "forms": [{"form": form, "tags": tags} for form, tags in forms],
    }


def test_word_forms_map_inflections_to_their_dictionary_word():
    records = [_forms_record("krążek", "noun", ("krążkiem", ["instrumental", "singular"]))]
    assert build_word_forms(records, {"krążek"})["krążkiem"] == ["krążek"]


def test_word_forms_include_the_dictionary_word_itself():
    records = [_forms_record("oświadczyny", "noun")]
    assert build_word_forms(records, {"oświadczyny"}) == {"oświadczyny": ["oświadczyny"]}


def test_word_forms_keep_every_word_a_form_could_belong_to():
    records = [
        _forms_record("mebel", "noun", ("meble", ["nominative", "plural"])),
        _forms_record("meble", "noun"),
    ]
    assert build_word_forms(records, {"mebel", "meble"})["meble"] == ["mebel", "meble"]


def test_word_forms_skip_related_words_that_are_not_inflections():
    records = [
        _forms_record(
            "pies",
            "noun",
            ("piesek", ["diminutive"]),
            ("psi", ["adjective"]),
            ("psisko", ["augmentative"]),
            ("psem", ["instrumental", "singular"]),
        )
    ]
    assert set(build_word_forms(records, {"pies"})) == {"pies", "psem"}


def test_word_forms_keep_comparatives_with_their_adjective():
    records = [_forms_record("wolny", "adj", ("wolniejszy", ["comparative"]))]
    assert build_word_forms(records, {"wolny"})["wolniejszy"] == ["wolny"]


def test_word_forms_skip_table_notes_and_phrases():
    records = [
        _forms_record(
            "wolny",
            "adj",
            ("pl-adecl", ["inflection-template", "singular"]),
            ("bardziej wolny", ["comparative"]),
        )
    ]
    assert set(build_word_forms(records, {"wolny"})) == {"wolny"}


def test_word_forms_use_verb_conjugations():
    records = [_forms_record("donieść", "verb", ("doniósł", ["past", "masculine"]), ("donosić", ["imperfective"]))]
    assert set(build_word_forms(records, {"donieść"})) == {"donieść", "doniósł"}


def test_word_forms_skip_words_without_a_translation():
    records = [_forms_record("xyz", "noun", ("xyza", ["genitive", "singular"]))]
    assert build_word_forms(records, {"pies"}) == {}


def test_leftovers_only_cover_single_words_the_options_lack():
    word_forms = {"chciwszych": ["chciwszy"], "krążkiem": ["krążek"], "czarny rynek": ["czarny rynek"]}
    options = {"krążkiem": "noun=krążek", "chciwszy": "adj=chciwy"}
    assert fold_leftovers(word_forms, set(), options) == {"chciwszych": "any=chciwy"}


def test_a_leftover_goes_straight_to_the_final_word():
    folded = fold_leftovers({"lepsze": ["lepszy"]}, {"dobry"}, {"lepszy": "adj=dobry"})
    assert folded == {"lepsze": "any=dobry"}


def test_a_leftover_stops_when_the_next_step_is_a_tie():
    folded = fold_leftovers({"patrzących": ["patrzący"]}, set(), {"patrzący": "verb=patrzeć,patrzyć"})
    assert folded == {"patrzących": "any=patrzący"}


def test_a_leftover_pointing_to_a_real_word_stops_there():
    folded = fold_leftovers({"znanym": ["znany"]}, {"znany"}, {"znany": "adj=znany;verb=znać"})
    assert folded == {"znanym": "any=znany"}


def test_a_leftover_with_nothing_further_keeps_its_word():
    assert fold_leftovers({"rzadkiego": ["rzadki"]}, set(), {}) == {"rzadkiego": "any=rzadki"}


def test_a_leftover_pointing_only_to_a_phrase_is_dropped():
    assert fold_leftovers({"naj": ["mądry jak gacie"]}, set(), {}) == {}


def _sense_of(gloss, target=None, tags=()):
    sense = {"glosses": [gloss], "tags": list(tags)}
    if target:
        sense["form_of"] = [{"word": target}]
    return sense


def _entry_record(word, pos, senses, *forms):
    return {
        "word": word, "pos": pos, "senses": senses,
        "forms": [{"form": form, "tags": tags} for form, tags in forms],
    }


def test_lemma_options_group_forms_by_part_of_speech():
    data = build_lemma_options([
        _entry_record("rozum", "noun", [_sense_of("mind")], ("rozumie", ["locative", "singular"])),
        _entry_record("rozumieć", "verb", [_sense_of("to understand")], ("rozumie", ["third-person", "singular"])),
    ])
    assert data["options"]["rozumie"] == "noun=rozum;verb=rozumieć"
    assert data["real_words"] == ["rozum", "rozumieć"]


def test_an_entry_that_is_only_a_form_is_not_a_real_word():
    data = build_lemma_options([
        _entry_record("szedł", "verb", [_sense_of("past of iść", "iść", ["past", "singular"])]),
    ])
    assert data["real_words"] == []
    assert data["options"]["szedł"] == "verb=iść"


def test_an_entry_with_a_real_meaning_too_counts_as_a_real_word():
    data = build_lemma_options([
        _entry_record("stały", "adj", [_sense_of("constant")]),
        _entry_record("stały", "verb", [_sense_of("past of stać", "stać", ["past", "plural"])]),
    ])
    assert "stały" in data["real_words"]
    assert data["options"]["stały"] == "adj=stały;verb=stać"


@pytest.mark.parametrize(
    "sense",
    [
        _sense_of("alternative spelling of z", "z", ["alternative", "singular"]),
        _sense_of("verbal noun of robić", "robić", ["noun-from-verb"]),
    ],
)
def test_links_that_are_not_inflections_are_ignored(sense):
    data = build_lemma_options([_entry_record("slowo", "noun", [sense])])
    assert "slowo" not in data["options"]


def test_equivalent_links_are_ignored_even_with_grammar_tags():
    sense = _sense_of("female equivalent of pan", "pan", ["singular"])
    assert build_lemma_options([_entry_record("pani", "noun", [sense])])["options"] == {"pani": "noun=pani"}


def test_related_words_in_a_table_are_not_options():
    data = build_lemma_options([
        _entry_record("pies", "noun", [_sense_of("dog")], ("piesek", ["diminutive"]), ("psem", ["instrumental", "singular"])),
    ])
    assert set(data["options"]) == {"pies", "psem"}


def test_multi_word_links_and_names_are_left_out():
    data = build_lemma_options([
        _entry_record("chłopi", "noun", [_sense_of("plural of x", "chłop pańszczyźniany", ["plural"])]),
        _entry_record("Warszawa", "name", [_sense_of("Warsaw")]),
    ])
    assert data == {"real_words": [], "options": {}, "verbal_nouns": {}}


def test_for_form_separates_the_tag_from_every_option():
    options = LemmaOptions(real_words=set(), options={"rozumie": "noun=rozum;verb=rozumieć"}, verbal_nouns={})
    assert options.for_form("rozumie", "VERB") == ({"rozumieć"}, {"rozum", "rozumieć"})
    assert options.for_form("rozumie", "ADP") == (set(), {"rozum", "rozumieć"})
    assert options.for_form("xyz", "NOUN") == (set(), set())


def test_real_lemma_options_handle_the_words_we_tested():
    options = load_lemma_options()
    assert options.for_form("jedziemy", "VERB")[0] == {"jechać"}
    assert options.for_form("meble", "NOUN")[0] == {"mebel"}
    assert "mógłbym" not in options.real_words
    assert {"mebel", "rozumieć", "pani", "rocznie"} <= options.real_words
    assert "pan" not in options.for_form("pani", "NOUN")[0]


def _verbal_sense(verb):
    return _sense_of(f"verbal noun of {verb}", verb, ["form-of", "noun-from-verb"])


def test_a_noun_that_is_only_a_verbal_noun_points_to_its_verb():
    data = build_lemma_options([
        _entry_record("robić", "verb", [_sense_of("to do")]),
        _entry_record("robienie", "noun", [_verbal_sense("robić")], ("robienia", ["genitive", "singular"])),
    ])
    assert data["verbal_nouns"] == {"robienie": "robić", "robienia": "robić"}


def test_a_verbal_noun_with_its_own_meaning_stays_a_word():
    data = build_lemma_options([
        _entry_record("mieszkanie", "noun", [_sense_of("apartment")], ("mieszkania", ["genitive", "singular"])),
        _entry_record("mieszkanie", "noun", [_verbal_sense("mieszkać")], ("mieszkania", ["genitive", "singular"])),
    ])
    assert data["verbal_nouns"] == {}


def test_a_form_shared_with_a_real_noun_is_left_out():
    data = build_lemma_options([
        _entry_record("kos", "noun", [_sense_of("blackbird")], ("kosy", ["genitive", "singular"])),
        _entry_record("koszenie", "noun", [_verbal_sense("kosić")], ("kosy", ["plural"]), ("koszenia", ["genitive", "singular"])),
    ])
    assert data["verbal_nouns"] == {"koszenie": "kosić", "koszenia": "kosić"}


def test_a_verbal_noun_linked_to_two_verbs_is_left_out():
    sense = _sense_of("verbal noun of a or b", "a", ["form-of", "noun-from-verb"])
    sense["form_of"].append({"word": "b"})
    assert build_lemma_options([_entry_record("x", "noun", [sense])])["verbal_nouns"] == {}


def test_the_same_tag_on_another_kind_of_noun_is_not_a_verbal_noun():
    sense = _sense_of("female equivalent of eks", "eks", ["form-of", "noun-from-verb"])
    assert build_lemma_options([_entry_record("była", "noun", [sense])])["verbal_nouns"] == {}


def test_a_verbal_noun_with_two_verbs_across_records_is_left_out():
    data = build_lemma_options([
        _entry_record("tępienie", "noun", [_verbal_sense("tępić")]),
        _entry_record("tępienie", "noun", [_verbal_sense("tępieć")]),
    ])
    assert data["verbal_nouns"] == {}


def test_a_spelling_that_belongs_to_another_verb_is_left_out():
    data = build_lemma_options([
        _entry_record("stawać", "verb", [_sense_of("to stand")], ("stanie", ["future", "singular"])),
        _entry_record("stanie", "noun", [_verbal_sense("stać")], ("stania", ["genitive", "singular"])),
    ])
    assert data["verbal_nouns"] == {"stania": "stać"}


def test_a_spelling_that_is_also_its_own_verb_stays_in():
    data = build_lemma_options([
        _entry_record("dostać", "verb", [_sense_of("to get")], ("dostanie", ["future", "singular"])),
        _entry_record("dostanie", "noun", [_verbal_sense("dostać")]),
    ])
    assert data["verbal_nouns"] == {"dostanie": "dostać"}


def test_two_verbal_nouns_sharing_a_spelling_are_left_out():
    data = build_lemma_options([
        _entry_record("aa", "noun", [_verbal_sense("x")], ("wspolne", ["plural"]), ("aaa", ["plural"])),
        _entry_record("bb", "noun", [_verbal_sense("y")], ("wspolne", ["plural"])),
    ])
    assert data["verbal_nouns"] == {"aa": "x", "aaa": "x", "bb": "y"}


def test_real_verbal_nouns_follow_the_rule():
    options = load_lemma_options()
    assert options.verbal_nouns["robienie"] == "robić"
    assert options.verbal_nouns["pukania"] == "pukać"
    for word in ("mieszkanie", "życie", "zdanie", "spotkanie", "przyjęcie", "jedzenie", "była", "stara", "tępienie"):
        assert word not in options.verbal_nouns


def test_a_female_version_is_its_own_word():
    sense = _sense_of("female equivalent of sanitariusz", "sanitariusz", ["feminine", "form-of"])
    data = build_lemma_options([_entry_record("sanitariuszka", "noun", [sense], ("sanitariuszkom", ["dative", "plural"]))])
    assert data["real_words"] == ["sanitariuszka"]
    assert data["options"]["sanitariuszkom"] == "noun=sanitariuszka"


def test_a_diminutive_is_its_own_word():
    sense = _sense_of("diminutive of kolacja", "kolacja", ["diminutive", "form-of"])
    data = build_lemma_options([_entry_record("kolacyjka", "noun", [sense], ("kolacyjki", ["genitive", "singular"]))])
    assert data["real_words"] == ["kolacyjka"]
    assert data["options"]["kolacyjki"] == "noun=kolacyjka"


def test_a_female_version_does_not_point_to_the_male_word():
    sense = _sense_of("female equivalent of pan", "pan", ["feminine", "form-of"])
    assert build_lemma_options([_entry_record("pani", "noun", [sense])])["options"]["pani"] == "noun=pani"


def test_a_grammatical_form_is_still_not_its_own_word():
    sense = _sense_of("masculine past of iść", "iść", ["form-of", "past"])
    data = build_lemma_options([_entry_record("szedł", "verb", [sense])])
    assert data["real_words"] == []
    assert data["options"]["szedł"] == "verb=iść"


def test_a_misspelling_is_still_not_its_own_word():
    sense = _sense_of("misspelling of mebel", "mebel", ["form-of", "misspelling"])
    assert build_lemma_options([_entry_record("mebl", "noun", [sense])])["real_words"] == []


def test_real_data_counts_everyday_related_words():
    options = load_lemma_options()
    for word in ("dziewczynka", "nauczycielka", "aktorka", "sanitariuszka", "kolacyjka"):
        assert word in options.real_words
    assert options.for_form("sanitariuszkom", "NOUN")[0] == {"sanitariuszka"}


def test_real_data_folds_leftovers_into_one_list():
    options = load_lemma_options()
    assert options.for_form("chciwszych", "ADJ") == (set(), {"chciwy"})
    assert options.for_form("największej", "ADJ") == (set(), {"największy"})
    assert options.for_form("patrzących", "ADJ")[1] == {"patrzący"}
    assert "szedł" not in options.real_words
    assert "największy" not in options.real_words


def test_a_chain_goes_straight_to_the_final_word():
    options = {"lepsze": "adj=lepszy", "lepszy": "adj=dobry", "dobry": "adj=dobry"}
    assert shorten_chains(options, {"dobry"})["lepsze"] == "adj=dobry"


def test_a_chain_stops_at_a_tie():
    options = {"większe": "adj=większy", "większy": "adj=duży,wielki"}
    assert shorten_chains(options, set())["większe"] == "adj=większy"


def test_a_chain_stops_at_a_real_word():
    options = {"znane": "adj=znany", "znany": "adj=znany;verb=znać"}
    assert shorten_chains(options, {"znany"})["znane"] == "adj=znany"


def test_a_chain_keeps_the_part_of_speech_it_came_from():
    options = {"mające": "adj=mający", "mający": "verb=mieć"}
    assert shorten_chains(options, set())["mające"] == "adj=mieć"


def test_a_chain_keeps_the_other_words_a_spelling_could_be():
    options = {"lepsze": "adj=lepszy;noun=lepsza", "lepszy": "adj=dobry"}
    assert shorten_chains(options, {"lepsza"})["lepsze"] == "adj=dobry;noun=lepsza"


def test_real_data_collapses_comparatives():
    options = load_lemma_options()
    assert "dobry" in options.for_form("lepsze", "ADJ")[0]
    assert "lepszy" not in options.for_form("lepsze", "ADJ")[0]
