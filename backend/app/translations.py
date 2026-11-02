"""Look up an English translation for a Polish lemma."""

import json
from functools import lru_cache
from pathlib import Path

DATA_FOLDER = Path(__file__).parent.parent / "data"
DATA_FILE = DATA_FOLDER / "translations.json"

# Hand-written fixes for common words, where a learner would notice a poor translation.
OVERRIDES_FILE = DATA_FOLDER / "translation_overrides.json"

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


@lru_cache(maxsize=1)
def load_translations() -> dict[str, dict[str, str]]:
    table = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return apply_overrides(table, overrides)


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
