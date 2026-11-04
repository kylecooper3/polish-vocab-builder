"""Stage 3: run spaCy over clean text and build the ranked list of lemmas."""

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import spacy
from pydantic import BaseModel
from spacy.language import Language

from app.translations import load_translations, load_verb_forms, load_word_forms, translate

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

VERB_POS = {"VERB", "AUX"}

# Words spaCy can wrongly tag as verbs that also match a form in the verb tables, such
# as "zdrów" ("healthy"), which would otherwise become "zdrowić" ("to heal").
NOT_VERB_FORMS = {"zdrów", "dziw"}

# Words that happen to match a form of an unrelated word, such as "bylem", which looks
# like a form of "byl" ("flower stalk") but comes from "byle" ("if only").
NOT_WORD_FORMS = {"bylem"}

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
    is_stopword: bool


class AnalysisResult(BaseModel):
    total_tokens: int
    unique_lemmas: int
    lemmas: list[LemmaEntry]


@dataclass
class _Tally:
    """Everything collected about one lemma while reading the book."""

    count: int = 0
    stop_count: int = 0
    forms: Counter = field(default_factory=Counter)
    pos: Counter = field(default_factory=Counter)
    example: str = ""
    example_is_good: bool = False


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


def fix_verb_lemma(form: str, lemma: str, pos: str, verb_forms: dict, translations: dict) -> str:
    """Replace a verb lemma that looks wrong with the dictionary word for its form.

    spaCy sometimes guesses a stem that doesn't exist ("poszedłem" gives "poszedć"), or
    just returns the word unchanged ("mógłbym"). Any other verb keeps spaCy's answer.
    """
    if pos not in VERB_POS or form in NOT_VERB_FORMS:
        return lemma
    if lemma in translations and lemma != form:
        return lemma
    return verb_forms.get(form, lemma)


def find_correct_lemma(tally: _Tally, word_forms: dict, rows_in_book: set[str]) -> str | None:
    """Work out which dictionary word a row belongs to from the forms the book used.

    spaCy can invent a stem ("krążkiem" gives "krążk"), but the form itself is reliable.
    Returns None rather than guess, because a blank row is better than a wrong merge.
    """
    targets = set()
    for form in tally.forms:
        candidates = [] if form in NOT_WORD_FORMS else word_forms.get(form, [])
        if len(candidates) > 1:
            # "meble" could be "mebel" or "meble", so prefer one this book already uses.
            candidates = [word for word in candidates if word in rows_in_book]
        if len(candidates) != 1:
            return None
        targets.add(candidates[0])
    return targets.pop() if len(targets) == 1 else None


def correct_unknown_lemmas(tallies: dict[str, _Tally], word_forms: dict, translations: dict) -> None:
    """Merge rows whose lemma isn't in the dictionary into the word they belong to.

    A row with no match stays as it is. That may be a word the dictionary doesn't have,
    such as one an author invented, and it still deserves a place in the list.
    """
    # Decided up front, so the answer doesn't depend on which rows are fixed first.
    rows_in_book = {lemma for lemma in tallies if lemma in translations}
    for lemma in [lemma for lemma in tallies if lemma not in translations]:
        target = find_correct_lemma(tallies[lemma], word_forms, rows_in_book)
        if target:
            target = LEMMA_MERGES.get(target, target)
            _merge_tally(tallies.setdefault(target, _Tally()), tallies.pop(lemma))


def _merge_tally(target: _Tally, source: _Tally) -> None:
    target.count += source.count
    target.stop_count += source.stop_count
    target.forms.update(source.forms)
    target.pos.update(source.pos)
    if not target.example or (source.example_is_good and not target.example_is_good):
        target.example = source.example
        target.example_is_good = source.example_is_good


def analyze_text(text: str, nlp) -> AnalysisResult:
    tallies: dict[str, _Tally] = {}
    total_tokens = 0
    translations = load_translations()
    verb_forms = load_verb_forms()

    # By default nlp.pipe groups up to 1,000 texts into a batch, which would process
    # every chunk at once and undo the memory saving of splitting the text.
    for doc in nlp.pipe(split_into_chunks(text), batch_size=1):
        for sentence in doc.sents:
            sentence_text = " ".join(sentence.text.split())
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
                lemma = fix_verb_lemma(
                    token.lower_, lemma_parts[0], token.pos_, verb_forms, translations
                )
                lemma = LEMMA_MERGES.get(lemma, lemma)

                tally = tallies.setdefault(lemma, _Tally())
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

    correct_unknown_lemmas(tallies, load_word_forms(), translations)

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
            is_stopword=_is_stopword(lemma, tally, nlp),
        )
        for rank, (lemma, tally) in enumerate(ordered, start=1)
    ]
    return AnalysisResult(
        total_tokens=total_tokens,
        unique_lemmas=len(entries),
        lemmas=entries,
    )


def _is_stopword(lemma: str, tally: _Tally, nlp) -> bool:
    # spaCy's stopword list holds word forms, so it flags "mam" but not "masz".
    # One lemma needs one answer: the lemma is listed, or most of its uses were.
    return lemma in nlp.Defaults.stop_words or tally.stop_count * 2 > tally.count
