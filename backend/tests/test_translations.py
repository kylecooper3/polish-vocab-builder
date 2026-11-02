from app.translations import load_translations, translate
from scripts.build_translations import build_table, clean_meaning


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
    assert table["pies"]["noun"] == "dog"


def test_specialist_meaning_is_kept_when_there_is_nothing_else():
    table = build_table([_record("kosa", "noun", _sense("old scythe", tags=["archaic"]))])
    assert table["kosa"]["noun"] == "old scythe"


def test_each_records_first_meaning_comes_first():
    table = build_table([
        _record("zamek", "noun", _sense("lock"), _sense("zip")),
        _record("zamek", "noun", _sense("castle")),
    ])
    assert table["zamek"]["noun"] == "lock, castle, zip"


def test_keeps_at_most_four_terms():
    table = build_table([_record("x", "noun", *(_sense(word) for word in "abcdef"))])
    assert table["x"]["noun"] == "a, b, c, d"


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
    assert table["człowiek"]["noun"] == "man, human, person"


def test_grammar_notes_are_dropped_when_a_translation_exists():
    table = build_table([
        _record("w", "prep", _sense("denotes inessive position; in, at, on")),
        _record("nie", "particle", _sense("negation particle; no, not")),
    ])
    assert table["w"]["prep"] == "in, at, on"
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
