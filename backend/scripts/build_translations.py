"""Build data/translations.json from Wiktionary's Polish data.

Download the source file (about 860 MB) from
https://kaikki.org/dictionary/Polish/kaikki.org-dictionary-Polish.jsonl
(kaikki.org marks this download as deprecated, so it may eventually move), then,
from the backend folder, run:

    python -m scripts.build_translations path/to/kaikki.org-dictionary-Polish.jsonl
"""

import gzip
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "translations.json"
VERB_FORMS_FILE = OUTPUT_FILE.parent / "verb_forms.json.gz"

# Entries in a verb's table that aren't forms of that verb.
ASPECT_TAGS = {"imperfective", "perfective"}
NON_FORM_TAGS = {"table-tags", "inflection-template", "class", "canonical", "romanization"}

# Names, letters, prefixes and so on aren't vocabulary a learner looks up here.
KEPT_POS = {"noun", "verb", "adj", "adv", "prep", "conj", "pron", "det", "num", "particle", "intj"}

# Meanings a learner shouldn't see first, such as a regional word for a farm tool.
SPECIALIST_TAGS = {
    "archaic", "dated", "dialectal", "derogatory", "obsolete", "offensive", "rare", "slang", "vulgar",
}

# Enough to show that "zamek" means both "lock" and "castle", while keeping flashcards short.
MAX_SENSES = 2
MAX_SYNONYMS = 2
MAX_MEANING_LENGTH = 80

# A term this long is usually describing a word rather than translating it.
MAX_WORDS_IN_TERM = 4

# Grammar notes, such as "denotes inessive position" for "w" ("in").
EXPLANATION = re.compile(
    r"^(denotes|indicates|used|introduces|emphasizes|expressing|often|first[- ]person|"
    r"second[- ]person|third[- ]person)\b|\b(pronoun|particle)$|…|\{\{"
)
INLINE_NOTE = re.compile(r"\s(?=denotes\s|indicates\s)")

# 'female equivalent of pan (“Mrs; miss”) (title)' carries its meaning in the quotes.
QUOTED_MEANING = re.compile(r"\(“(.+?)”\)")
RELATED_WORD = re.compile(r"^synonym of (\S+)")


def clean_meaning(gloss: str) -> str:
    """Shorten 'dog (Canis lupus familiaris)' to 'dog', and 'to know [with o]' to 'to know'."""
    meaning = gloss.split(" (")[0].split(" [")[0].strip().rstrip(":;,")
    if len(meaning) > MAX_MEANING_LENGTH:
        meaning = meaning[:MAX_MEANING_LENGTH].rsplit(" ", 1)[0] + "…"
    return meaning


def classify_sense(sense: dict) -> tuple[str, str]:
    """Return what kind of sense this is, and its meaning or the word it points to."""
    glosses = sense.get("glosses")
    if not glosses:
        return "skip", ""
    gloss = glosses[-1]

    links = sense.get("form_of") or sense.get("alt_of")
    if links:
        # A related word that has its own meaning: "pani" is the female form of "pan".
        quoted = QUOTED_MEANING.search(gloss)
        if quoted:
            return "plain", clean_meaning(quoted.group(1))
        # An inflected or alternative form: "schody" is a plural form of "schód".
        return "link", links[0]["word"].lower()

    synonym = RELATED_WORD.match(gloss)
    if synonym:
        return "link", synonym.group(1).lower()

    is_specialist = has_specialist_label(sense) or SPECIALIST_TAGS & set(sense.get("tags", []))
    return ("specialist" if is_specialist else "plain"), clean_meaning(gloss)


def has_specialist_label(sense: dict) -> bool:
    """Is there a capitalized bracketed label, which marks a place, as in "(Biecz)"?

    Lowercase labels such as "(transitive)", "(law)" or "(anatomy)" describe grammar or
    a subject, and those are ordinary meanings: "mecenas" really does mean "lawyer".
    """
    label = re.match(r"\((.+?)\)", sense.get("raw_glosses", [""])[0])
    if not label:
        return False
    return any(part.strip()[:1].isupper() for part in re.split(r",| or ", label.group(1)))


def split_into_senses(meanings: list[str]) -> list[str]:
    """Pick the first few senses, as short synonyms with no repeats or grammar notes."""
    senses = []
    seen = set()
    for meaning in meanings:
        terms = []
        for part in re.split(r";|" + INLINE_NOTE.pattern, meaning):
            # Checked before splitting on commas, so a note like "indicates separation,
            # distance" goes as a whole rather than leaving "distance" behind.
            if EXPLANATION.search(part.strip()):
                continue
            for term in part.split(","):
                term = term.strip()
                if (
                    term
                    and term not in seen
                    and term not in terms
                    and not EXPLANATION.search(term)
                    and len(term.split()) <= MAX_WORDS_IN_TERM
                ):
                    terms.append(term)

        # A sense that only repeats earlier terms adds nothing, so it doesn't use up a slot.
        if terms:
            terms = terms[:MAX_SYNONYMS]
            seen.update(terms)
            senses.append(", ".join(terms))
        if len(senses) == MAX_SENSES:
            break

    # If a word only has an explanation, like "to" ("used to point to..."), that's still
    # better than nothing, so keep the whole first meaning.
    return senses or meanings[:1]


def choose_meanings(records: list[list[str]]) -> list[str]:
    """Take each record's first meaning before anyone's second.

    "zamek" has one record for "lock, zip" and another for "castle", and a learner
    should see both of its real meanings rather than two kinds of fastener.
    """
    ordered = []
    for position in range(max(map(len, records), default=0)):
        for meanings in records:
            if position < len(meanings):
                ordered.append(meanings[position])
    return split_into_senses(ordered)


def build_table(records) -> dict[str, dict[str, str]]:
    """Turn raw Wiktionary records into {word: {part of speech: translation}}."""
    plain = defaultdict(lambda: defaultdict(list))
    specialist = defaultdict(lambda: defaultdict(list))
    links = defaultdict(lambda: defaultdict(list))

    for record in records:
        word, pos = record.get("word", "").lower(), record.get("pos")
        if not word or pos not in KEPT_POS:
            continue
        found = {"plain": [], "specialist": [], "link": []}
        for sense in record.get("senses", []):
            kind, value = classify_sense(sense)
            if kind != "skip" and value:
                found[kind].append(value)
        plain[word][pos].append(found["plain"])
        specialist[word][pos].append(found["specialist"])
        links[word][pos].extend(found["link"])

    def direct_meanings(word: str, pos: str) -> list[str]:
        # Specialist meanings are only a last resort, when nothing better exists.
        return choose_meanings(plain[word][pos]) or choose_meanings(specialist[word][pos])

    table = defaultdict(dict)
    for word in list(plain):
        for pos in list(plain[word]):
            meanings = direct_meanings(word, pos)
            # Follow one link: "schody" has no meaning of its own, but "schód" does.
            for target in links[word][pos]:
                if meanings or target not in plain:
                    break
                meanings = direct_meanings(target, pos)
            if meanings:
                # Commas separate synonyms and semicolons separate meanings, as in a
                # printed dictionary: "patron, sponsor; lawyer, advocate".
                table[word][pos] = "; ".join(meanings)

    return dict(table)


def build_verb_forms(records) -> dict[str, str]:
    """Map each verb form to its dictionary word: {"poszedłem": "pójść"}.

    A form that could belong to several verbs is left out, because a wrong guess
    would be worse than keeping spaCy's answer.
    """
    candidates = defaultdict(set)
    for record in records:
        word = record.get("word", "").lower()
        if not word or record.get("pos") != "verb":
            continue
        for entry in record.get("forms", []):
            form = (entry.get("form") or "").lower()
            tags = set(entry.get("tags", []))
            # Tables also list a verb's partner ("pójść" lists "iść") and template notes.
            if form and " " not in form and not tags <= ASPECT_TAGS and not tags & NON_FORM_TAGS:
                candidates[form].add(word)
    return {form: next(iter(words)) for form, words in candidates.items() if len(words) == 1}


def main(source: str) -> None:
    with open(source, encoding="utf-8") as handle:
        table = build_table(json.loads(line) for line in handle)
    with open(source, encoding="utf-8") as handle:
        verb_forms = build_verb_forms(json.loads(line) for line in handle)
    # mtime=0 means a rebuild with the same data gives an identical file for Git.
    VERB_FORMS_FILE.write_bytes(
        gzip.compress(json.dumps(verb_forms, ensure_ascii=False, sort_keys=True).encode(), mtime=0)
    )
    print(f"{len(verb_forms):,} verb forms, {VERB_FORMS_FILE.stat().st_size / 1e6:.1f} MB")
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    # Sorted, with one word per line, so a rebuild gives a readable Git diff.
    lines = [
        f"{json.dumps(word, ensure_ascii=False)}: {json.dumps(table[word], ensure_ascii=False)}"
        for word in sorted(table)
    ]
    OUTPUT_FILE.write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")
    print(f"{len(table):,} words, {OUTPUT_FILE.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
