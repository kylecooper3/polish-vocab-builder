from app.lemmas import analyze_text, split_into_chunks


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
