"""Stage 3: run spaCy over clean text and build the ranked list of lemmas."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal, NamedTuple

import spacy
from pydantic import BaseModel, Field
from spacy.language import Language

from app.translations import (
    LemmaOptions,
    load_lemma_options,
    load_translations,
    load_word_forms,
    translate,
)

MODEL_NAME = "pl_core_news_lg"

# spaCy refuses single texts over 1,000,000 characters by default, because its
# memory use grows with text length. Measured on a 780,000-character novel, these
# pieces processed one at a time (see analyze_text) use 79 MB on top of the model,
# against 2,582 MB for 100,000-character pieces at spaCy's default batch size.
CHUNK_SIZE = 20_000

# Spelled-out numbers (NUM, like "dwa") stay because they are useful vocabulary.
# Digits never reach this check: the is_alpha test removes them first.
EXCLUDED_POS = {"PROPN", "PUNCT", "SYM", "X", "SPACE"}

# Lemmas counted as another word. spaCy treats "wybory" as its own word, but it's also
# the plural of "wybór" ("choice"). Merging means its "elections" meaning isn't listed.
LEMMA_MERGES = {"wybory": "wybór", "zdrów": "zdrowy"}

# Spellings where the dictionary's answer is known to be wrong, so spaCy's lemma stays.
# "bylem" comes from "byle" ("if only"), not "byl" ("flower stalk"). "zdrów" means "healthy",
# not "zdrowić" ("to heal"). "laty" belongs to "rok" ("year"), as in "przed laty" ("years
# ago"). "lewo" is "left", as in "w lewo", and "kuzynka" is a female cousin, not "kuzynek".
NOT_WORD_FORMS = {"bylem", "zdrów", "dziw", "laty", "lewo", "kuzynka"}

# A form whose part of speech settles it, where Wiktionary lists several words. spaCy can
# tag "je" ("eats") as a verb but still give it the lemma "on" ("he"), and Wiktionary also
# lists it under "być" ("to be"), which isn't its modern meaning.
LEMMA_BY_FORM_AND_POS = {("je", "VERB"): "jeść"}

# The forms of "ono" ("it") that aren't also spelled the same as a form of "on" ("he").
NEUTER_ONLY_FORMS = {"ono", "je"}

# Sentences of this length make the best flashcard examples.
MIN_EXAMPLE_WORDS = 5
MAX_EXAMPLE_WORDS = 25


class LemmaEntry(BaseModel):
    lemma: str
    count: int
    rank: int
    pos: str
    translation: str
    forms: list[str]
    example: str
    example_spans: list[tuple[int, int]]  # where this word is in the example (start, end)
    is_stopword: bool


class LemmaMerge(BaseModel):
    """One row spaCy produced that the app folded into a dictionary word."""

    from_lemma: str
    to_lemma: str
    count: int
    pos: str
    forms: list[str]
    example: str
    example_spans: list[tuple[int, int]]
    method: Literal["only_match", "tie_break"]
    new_row: bool  # True if spaCy gave the book no correct row for this word


class MatchGroup(BaseModel):
    rows: int = 0
    occurrences: int = 0


class MatchStats(BaseModel):
    """How spaCy's rows matched the dictionary.

    Every use of a word is counted in the group its own form landed in. One spaCy row can
    have forms in different groups, so each row is counted once, under its biggest group.
    """

    in_dictionary: MatchGroup = Field(default_factory=MatchGroup)
    merged: MatchGroup = Field(default_factory=MatchGroup)
    unresolved: MatchGroup = Field(default_factory=MatchGroup)  # possible matches, none chosen
    no_match: MatchGroup = Field(default_factory=MatchGroup)


class AnalysisResult(BaseModel):
    total_tokens: int
    unique_lemmas: int
    lemmas: list[LemmaEntry]
    match_stats: MatchStats
    merges: list[LemmaMerge]


@dataclass
class _Tally:
    """Everything collected about one lemma while reading the book."""

    count: int = 0
    stop_count: int = 0
    forms: Counter = field(default_factory=Counter)
    pos: Counter = field(default_factory=Counter)
    example: str = ""
    example_is_good: bool = False
    example_spans: list = field(default_factory=list)
    example_sentence: int = -1  # which sentence of the book the example came from


class Choice(NamedTuple):
    lemma: str
    group: str  # a field of MatchStats
    method: str = "only_match"


@lru_cache(maxsize=1)
def load_model():
    """Load the model once and reuse it, since loading takes several seconds."""
    # Named-entity recognition is the slowest step and we don't use its output.
    nlp = spacy.load(MODEL_NAME, exclude=["ner"])
    nlp.add_pipe("paragraph_boundaries", before="parser")
    return nlp


@Language.component("paragraph_boundaries")
def paragraph_boundaries(doc):
    """Start a new sentence after each blank line, so a chapter heading doesn't
    get glued onto the first sentence of the chapter."""
    for token in doc[:-1]:
        if token.is_space and "\n\n" in token.text:
            doc[token.i + 1].is_sent_start = True
    return doc


def split_into_chunks(text: str, max_chars: int = CHUNK_SIZE) -> list[str]:
    """Split text into pieces, breaking at paragraphs or spaces where possible."""
    chunks = []
    start = 0
    while len(text) - start > max_chars:
        end = start + max_chars
        cut = text.rfind("\n\n", start + 1, end)
        if cut == -1:
            cut = text.rfind(" ", start + 1, end)
        if cut == -1:
            cut = end
        chunks.append(text[start:cut])
        start = cut
    if start < len(text):
        chunks.append(text[start:])
    return chunks


def _word_starts(sentence, sentence_text: str) -> dict[int, int]:
    """Find where each word sits in the sentence once its extra spaces are removed."""
    starts = {}
    position = 0
    for token in sentence:
        if token.is_space:
            continue
        start = sentence_text.find(token.text, position)
        if start != -1:
            starts[token.i] = start
            position = start + len(token.text)
    return starts


def split_pronoun(lemma: str, pos: str, morph, form: str) -> str:
    """Give "he", "she", "it" and both words for "they" a row each.

    spaCy files all of them under "on", which is a fair grammatical view but shows a
    learner "ona" under "he". Its gender and number tags say which word was meant. "oni"
    is only for groups of people including men: "je" for things is tagged masculine
    plural too, so the human tag is needed as well.

    "it" only uses the spellings that differ from "he". Forms like "jego" and "nim" are
    the same for both, and in a sample from one novel, 22 of 30 rows tagged neuter were
    really masculine, so showing them as "it" would mostly be wrong.
    """
    if lemma != "on" or pos != "PRON":
        return lemma
    gender = morph.get("Gender")
    number = morph.get("Number")
    if "Plur" in number:
        return "oni" if "Masc" in gender and "Hum" in morph.get("Animacy") else "one"
    if "Sing" in number and "Fem" in gender:
        return "ona"
    if "Sing" in number and "Neut" in gender and form in NEUTER_ONLY_FORMS:
        return "ono"
    return "on"


def choose_lemma(
    form: str, lemma: str, pos: str, options: LemmaOptions, word_forms: dict, rows_in_book: set[str]
) -> Choice:
    """Compare spaCy's lemma and part of speech with Wiktionary, and decide which to trust.

    spaCy reads context but can invent words. Wiktionary only has real words but can't read
    context. So agreement keeps the lemma, and a made-up lemma takes Wiktionary's answer.
    A real word is only replaced when the form can't belong to it and one other word fits.
    Anything unclear stays as it is, because a blank row is better than a wrong one.
    """
    if (form, pos) in LEMMA_BY_FORM_AND_POS:
        return Choice(LEMMA_BY_FORM_AND_POS[(form, pos)], "merged")

    in_dictionary = lemma in options.real_words
    if form in NOT_WORD_FORMS:
        return Choice(lemma, "in_dictionary" if in_dictionary else "no_match")

    matching, every = options.for_form(form, pos)
    if lemma in matching:
        return Choice(lemma, "in_dictionary")

    if in_dictionary:
        if len(matching) == 1 and form not in matching:
            return Choice(next(iter(matching)), "merged")
        return Choice(lemma, "in_dictionary")

    # The form table also covers entries that are only forms themselves, like "najwyższy".
    candidates = matching or every or set(word_forms.get(form, []))
    if not candidates:
        return Choice(lemma, "no_match")
    tied = len(candidates) > 1
    if tied:
        # "robocie" could be "robot" or "robota", so prefer one this book already uses.
        candidates = candidates & rows_in_book
    if candidates == {lemma}:
        return Choice(lemma, "in_dictionary")  # confirmed, so nothing moved
    if len(candidates) == 1:
        return Choice(next(iter(candidates)), "merged", "tie_break" if tied else "only_match")
    return Choice(lemma, "unresolved")


def resolve_lemmas(
    readings: dict[tuple, _Tally], options: LemmaOptions, word_forms: dict
) -> tuple[dict[str, _Tally], list[LemmaMerge], MatchStats]:
    """Turn what was read into the final rows, deciding each form separately.

    It runs once the whole book is read, because the tie-break needs to know which words
    the book contains. Each reading is one combination of spaCy's lemma, the form and its
    part of speech. Returns a record of every merge and how everything matched, written as
    each decision is made, so people can check what the app actually did.
    """
    rows_in_book = {key[0] for key in readings if key[0] in options.real_words}
    rows: dict[str, _Tally] = {}
    moved: dict[tuple[str, str], _Tally] = {}
    methods: dict[tuple[str, str], str] = {}
    uses_by_group = defaultdict(Counter)

    for (lemma, form, pos, settled), tally in readings.items():
        choice = (
            Choice(lemma, "in_dictionary")
            if settled
            else choose_lemma(form, lemma, pos, options, word_forms, rows_in_book)
        )
        target = LEMMA_MERGES.get(choice.lemma, choice.lemma)
        uses_by_group[lemma][choice.group] += tally.count
        _merge_tally(rows.setdefault(target, _Tally()), tally)
        if target != lemma:
            _merge_tally(moved.setdefault((lemma, target), _Tally()), tally)
            if methods.get((lemma, target)) != "tie_break":
                methods[(lemma, target)] = choice.method

    stats = MatchStats()
    for uses in uses_by_group.values():
        for group, count in uses.items():
            getattr(stats, group).occurrences += count
        biggest = max(sorted(uses), key=uses.__getitem__)
        getattr(stats, biggest).rows += 1

    merges = [
        LemmaMerge(
            from_lemma=lemma,
            to_lemma=target,
            count=tally.count,
            pos=tally.pos.most_common(1)[0][0],
            forms=[form for form, _ in tally.forms.most_common()],
            example=tally.example,
            example_spans=tally.example_spans,
            method=methods[(lemma, target)],
            new_row=target not in rows_in_book,
        )
        for (lemma, target), tally in moved.items()
    ]
    merges.sort(key=lambda merge: (-merge.count, merge.from_lemma, merge.to_lemma))
    return rows, merges, stats


def _merge_tally(target: _Tally, source: _Tally) -> None:
    target.count += source.count
    target.stop_count += source.stop_count
    target.forms.update(source.forms)
    target.pos.update(source.pos)
    if target.example and target.example_sentence == source.example_sentence:
        # Both chose the same sentence, so all of these words are now this word.
        target.example_spans = sorted({*target.example_spans, *source.example_spans})
    elif (
        not target.example
        or (source.example_is_good and not target.example_is_good)
        or (
            source.example_is_good == target.example_is_good
            and source.example_sentence < target.example_sentence
        )
    ):
        target.example = source.example
        target.example_is_good = source.example_is_good
        target.example_spans = source.example_spans
        target.example_sentence = source.example_sentence


def analyze_text(text: str, nlp) -> AnalysisResult:
    readings: dict[tuple, _Tally] = {}
    total_tokens = 0
    translations = load_translations()

    # By default nlp.pipe groups up to 1,000 texts into a batch, which would process
    # every chunk at once and undo the memory saving of splitting the text.
    sentence_number = 0
    for doc in nlp.pipe(split_into_chunks(text), batch_size=1):
        for sentence in doc.sents:
            sentence_number += 1
            sentence_text = " ".join(sentence.text.split())
            word_starts = _word_starts(sentence, sentence_text)
            word_count = sum(1 for token in sentence if not token.is_punct and not token.is_space)
            good_length = MIN_EXAMPLE_WORDS <= word_count <= MAX_EXAMPLE_WORDS

            for token in sentence:
                if not token.is_alpha or token.pos_ in EXCLUDED_POS:
                    continue
                # spaCy turns "myślałem" into "myśleć być", because Polish past-tense
                # endings work like a stuck-on "to be". Without this, "myśleć" would be
                # counted as two separate words. The first word is the real lemma.
                lemma_parts = token.lemma_.lower().split()
                if not lemma_parts:
                    continue
                lemma = split_pronoun(lemma_parts[0], token.pos_, token.morph, token.lower_)
                # The split used this word's tags, so the dictionary can't improve on it.
                settled = lemma != lemma_parts[0]
                lemma = LEMMA_MERGES.get(lemma, lemma)

                tally = readings.setdefault((lemma, token.lower_, token.pos_, settled), _Tally())
                tally.count += 1
                tally.stop_count += token.is_stop
                tally.forms[token.lower_] += 1
                tally.pos[token.pos_] += 1
                total_tokens += 1

                # Keep the first sentence seen, upgrading once to the first one
                # that has a good length.
                if not tally.example or (good_length and not tally.example_is_good):
                    tally.example = sentence_text
                    tally.example_is_good = good_length
                    tally.example_spans = []
                    tally.example_sentence = sentence_number

                # Recorded word by word, because spelling alone can't tell which row a
                # word belongs to: "to" can be counted under "ten" or under "to".
                if tally.example_sentence == sentence_number and token.i in word_starts:
                    start = word_starts[token.i]
                    tally.example_spans.append((start, start + len(token.text)))

    tallies, merges, match_stats = resolve_lemmas(readings, load_lemma_options(), load_word_forms())

    # Sorting by lemma as well makes ties come out in the same order every run.
    ordered = sorted(tallies.items(), key=lambda item: (-item[1].count, item[0]))
    entries = [
        LemmaEntry(
            lemma=lemma,
            count=tally.count,
            rank=rank,
            pos=tally.pos.most_common(1)[0][0],
            translation=translate(lemma, tally.pos.most_common(1)[0][0], translations),
            forms=[form for form, _ in tally.forms.most_common()],
            example=tally.example,
            example_spans=tally.example_spans,
            is_stopword=_is_stopword(lemma, tally, nlp),
        )
        for rank, (lemma, tally) in enumerate(ordered, start=1)
    ]
    return AnalysisResult(
        total_tokens=total_tokens,
        unique_lemmas=len(entries),
        lemmas=entries,
        match_stats=match_stats,
        merges=merges,
    )


def _is_stopword(lemma: str, tally: _Tally, nlp) -> bool:
    # spaCy's stopword list holds word forms, so it flags "mam" but not "masz".
    # One lemma needs one answer: the lemma is listed, or most of its uses were.
    return lemma in nlp.Defaults.stop_words or tally.stop_count * 2 > tally.count
