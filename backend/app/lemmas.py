"""Stage 3: run spaCy over clean text and build the ranked list of lemmas."""

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import spacy
from pydantic import BaseModel
from spacy.language import Language

MODEL_NAME = "pl_core_news_lg"

# spaCy refuses single texts over 1,000,000 characters by default, because its
# memory use grows with text length. Measured on a 780,000-character novel, these
# pieces processed one at a time (see analyze_text) use 79 MB on top of the model,
# against 2,582 MB for 100,000-character pieces at spaCy's default batch size.
CHUNK_SIZE = 20_000

# Spelled-out numbers (NUM, like "dwa") stay because they are useful vocabulary.
# Digits never reach this check: the is_alpha test removes them first.
EXCLUDED_POS = {"PROPN", "PUNCT", "SYM", "X", "SPACE"}

# Sentences of this length make the best flashcard examples.
MIN_EXAMPLE_WORDS = 5
MAX_EXAMPLE_WORDS = 25


class LemmaEntry(BaseModel):
    lemma: str
    count: int
    rank: int
    pos: str
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


def analyze_text(text: str, nlp) -> AnalysisResult:
    tallies: dict[str, _Tally] = {}
    total_tokens = 0

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
                lemma = token.lemma_.lower()
                if not lemma:
                    continue

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

    # Sorting by lemma as well makes ties come out in the same order every run.
    ordered = sorted(tallies.items(), key=lambda item: (-item[1].count, item[0]))
    entries = [
        LemmaEntry(
            lemma=lemma,
            count=tally.count,
            rank=rank,
            pos=tally.pos.most_common(1)[0][0],
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
