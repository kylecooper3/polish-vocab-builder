"""Look up an English translation for a Polish lemma."""

import gzip
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_FOLDER = Path(__file__).parent.parent / "data"
DATA_FILE = DATA_FOLDER / "translations.json"

# Hand-written fixes for common words, where a learner would notice a poor translation.
OVERRIDES_FILE = DATA_FOLDER / "translation_overrides.json"

LEMMA_OPTIONS_FILE = DATA_FOLDER / "lemma_options.json.gz"

# spaCy and Wiktionary name parts of speech differently, and don't always agree. Where
# they disagree, such as "więc" (SCONJ in spaCy, a particle in Wiktionary), the fallback
# in translate() still finds the word.
SPACY_TO_WIKTIONARY = {
    "ADJ": ["adj"],
    "ADP": ["prep"],
    "ADV": ["adv"],
    "AUX": ["verb"],
    "CCONJ": ["conj"],
    "DET": ["det", "pron", "adj"],
    "INTJ": ["intj"],
    "NOUN": ["noun"],
    "NUM": ["num"],
    "PART": ["particle"],
    "PRON": ["pron"],
    "SCONJ": ["conj"],
    "VERB": ["verb"],
}


@dataclass
class LemmaOptions:
    """Which dictionary words a spelling could belong to, from Wiktionary."""

    real_words: set[str]
    options: dict[str, str]  # {"rozumie": "noun=rozum;verb=rozumieć"}
    fallback: dict[str, list[str]]  # {"największej": ["największy"]}, when options has nothing
    verbal_nouns: dict[str, str]  # {"robienia": "robić"}, for nouns with no meaning of their own

    def for_form(self, form: str, spacy_pos: str) -> tuple[set[str], set[str]]:
        """Return the words matching spaCy's part of speech, and every word."""
        wanted = SPACY_TO_WIKTIONARY.get(spacy_pos, [])
        matching, every = set(), set()
        encoded = self.options.get(form)
        if encoded:
            for group in encoded.split(";"):
                pos, _, words = group.partition("=")
                words = words.split(",")
                every.update(words)
                if pos in wanted:
                    matching.update(words)
        return matching, every


@lru_cache(maxsize=1)
def load_translations() -> dict[str, dict[str, str]]:
    table = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return apply_overrides(table, overrides)


@lru_cache(maxsize=1)
def load_lemma_options() -> LemmaOptions:
    data = json.loads(gzip.decompress(LEMMA_OPTIONS_FILE.read_bytes()))
    # A word with a hand-written translation is a real word, even if Wiktionary lacks it.
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return LemmaOptions(
        real_words={*data["real_words"], *overrides},
        options=data["options"],
        fallback=data["fallback"],
        verbal_nouns=data["verbal_nouns"],
    )


def apply_overrides(table: dict, overrides: dict) -> dict:
    """Replace only the parts of speech an override names, keeping a word's others."""
    for word, entry in overrides.items():
        table.setdefault(word, {}).update(entry)
    return table


def translate(lemma: str, pos: str, table: dict[str, dict[str, str]]) -> str:
    """Return the English meaning, or an empty string rather than a guess."""
    entry = table.get(lemma)
    if not entry:
        return ""
    for dictionary_pos in SPACY_TO_WIKTIONARY.get(pos, []):
        if dictionary_pos in entry:
            return entry[dictionary_pos]
    # The word exists but under a different part of speech. Its meaning is still useful.
    return next(iter(entry.values()))
