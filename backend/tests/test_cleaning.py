import unicodedata

from app.cleaning import clean_pages, looks_garbled


def test_rejoins_word_hyphenated_across_lines():
    assert clean_pages(["To jest książ-\nka o psie."]) == "To jest książka o psie."


def test_rejoins_word_hyphenated_across_pages():
    assert clean_pages(["To jest książ-", "ka o psie."]) == "To jest książka o psie."


def test_keeps_hyphen_in_a_compound_split_across_lines():
    # "biało" and "czerwona" are both words, but "białoczerwona" isn't.
    assert clean_pages(["Flaga jest biało-\nczerwona."]) == "Flaga jest biało-czerwona."


def test_keeps_hyphen_before_capitalized_word():
    assert clean_pages(["Maria Skłodowska-\nCurie"]) == "Maria Skłodowska-Curie"


def test_removes_page_number_lines():
    for line in ["12", "- 12 -", "12 / 300", "Strona 12", "XIV"]:
        assert clean_pages([f"Początek\n{line}\nkoniec"]) == "Początek koniec"


def test_keeps_numbers_inside_sentences():
    assert clean_pages(["Miał 12 psów."]) == "Miał 12 psów."


def test_keeps_lone_lowercase_word_that_looks_roman():
    assert clean_pages(["Pies\ni\nkot"]) == "Pies i kot"


def test_removes_header_repeated_on_many_pages():
    pages = [
        f"Lalka\nTreść strony numer {word}.\nRozdział {number}"
        for number, word in enumerate(["jeden", "dwa", "trzy", "cztery"], start=1)
    ]
    cleaned = clean_pages(pages)
    assert "Lalka" not in cleaned
    assert "Rozdział" not in cleaned
    assert "Treść strony numer cztery." in cleaned


def test_keeps_line_repeated_on_too_few_pages():
    assert "Lalka" in clean_pages(["Lalka\nJeden.", "Lalka\nDwa.", "Trzy.", "Cztery."])


def test_keeps_repeated_line_in_the_middle_of_a_page():
    page = "Pierwsza.\nDruga.\nTak.\nCzwarta.\nPiąta."
    assert "Tak." in clean_pages([page, page, page])


def test_single_newline_becomes_space_and_blank_line_stays():
    assert clean_pages(["Jeden\ndwa.\n\nTrzy   cztery."]) == "Jeden dwa.\n\nTrzy cztery."


def test_combining_marks_become_single_letters():
    decomposed = unicodedata.normalize("NFD", "książka")
    assert decomposed != "książka"
    assert clean_pages([decomposed]) == "książka"


def test_removes_soft_hyphens():
    assert clean_pages(["ksią­żka"]) == "książka"


def test_removes_footnote_marker_stuck_to_a_word():
    assert clean_pages(["Spotkał jegomościa1 w parku, a potem książkę12."]) == (
        "Spotkał jegomościa w parku, a potem książkę."
    )


def test_keeps_standalone_numbers_next_to_words():
    assert clean_pages(["Rok 1984 i 12 psów."]) == "Rok 1984 i 12 psów."


def test_rejoins_word_split_by_soft_hyphen_at_line_end():
    assert clean_pages(["To jest książ­\nka o psie."]) == "To jest książka o psie."


def test_rejoins_word_split_by_soft_hyphen_across_pages():
    assert clean_pages(["To jest książ­", "ka o psie."]) == "To jest książka o psie."


def test_normal_polish_text_is_not_garbled():
    assert not looks_garbled("Zażółć gęślą jaźń — to jest zwykły polski tekst, 1878 rok!")


def test_wrong_letter_mapping_is_garbled():
    assert looks_garbled("Sprawiedliwym గest to, że గa గuż wiem, గak గest.")


def test_private_use_characters_are_garbled():
    assert looks_garbled(" tekst")


def test_a_short_foreign_quotation_is_not_garbled():
    text = "To jest długi polski akapit o książkach. " * 30 + "Rzekł: Война."
    assert not looks_garbled(text)


def test_text_with_no_letters_is_not_called_garbled():
    assert not looks_garbled("")
    assert not looks_garbled("123 456")


def test_empty_input_gives_empty_text():
    assert clean_pages([]) == ""
    assert clean_pages(["", "   "]) == ""
