import json

from app.translations import (
    OVERRIDES_FILE,
    apply_overrides,
    load_translations,
    load_verb_forms,
    load_word_forms,
    translate,
)
from scripts.build_translations import (
    KEPT_POS,
    build_table,
    build_verb_forms,
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


def _verb(word, *forms):
    return {"word": word, "pos": "verb", "forms": [{"form": f, "tags": t} for f, t in forms]}


def test_verb_forms_map_to_their_dictionary_word():
    table = build_verb_forms([_verb("pójść", ("poszedłem", ["past", "singular"]))])
    assert table == {"poszedłem": "pójść"}


def test_verb_forms_skip_a_verbs_partner_and_template_notes():
    table = build_verb_forms([
        _verb("pójść", ("iść", ["imperfective"]), ("l", ["inflection-template"]), ("pójdę", ["future"])),
    ])
    assert table == {"pójdę": "pójść"}


def test_verb_forms_leave_out_a_form_shared_by_two_verbs():
    table = build_verb_forms([_verb("stać", ("stanę", ["future"])), _verb("stanąć", ("stanę", ["future"]))])
    assert table == {}


def test_verb_forms_ignore_other_parts_of_speech_and_phrases():
    records = [
        {"word": "pies", "pos": "noun", "forms": [{"form": "psa", "tags": ["genitive"]}]},
        _verb("pójść", ("pójdzie się", ["impersonal"])),
    ]
    assert build_verb_forms(records) == {}


def test_real_verb_form_data_has_the_irregular_forms():
    forms = load_verb_forms()
    assert forms["poszedłem"] == "pójść"
    assert forms["rzekłem"] == "rzec"
    assert forms["jadłem"] == "jeść"
    assert forms["mogłem"] == "móc"


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


def test_word_form_table_finds_a_real_noun():
    assert load_word_forms()["krążkiem"] == ["krążek"]
