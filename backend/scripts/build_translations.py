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
LEMMA_OPTIONS_FILE = OUTPUT_FILE.parent / "lemma_options.json.gz"

# Entries in a verb's table that aren't forms of that verb.
ASPECT_TAGS = {"imperfective", "perfective"}
NON_FORM_TAGS = {"table-tags", "inflection-template", "class", "canonical", "romanization"}

# A noun or adjective's entries also list related words, such as "piesek" and "psi" under
# "pies". Those are different words, so only entries with these tags count as its forms.
INFLECTION_TAGS = {
    "singular", "plural", "nominative", "genitive", "dative", "accusative",
    "instrumental", "locative", "vocative", "comparative", "superlative",
}

# Wiktionary links an entry to another word for many reasons. Only a link carrying one of
# these tags means "this is an inflected form of that word".
GRAMMAR_TAGS = INFLECTION_TAGS | {
    "first-person", "second-person", "third-person", "past", "present", "future",
    "imperative", "conditional", "participle", "impersonal",
}

# Links that aren't inflections, even if they also carry a grammar tag.
RELATED_WORD_TAGS = {
    "diminutive", "augmentative", "abbreviation", "alternative", "misspelling", "noun-from-verb",
}

# Wiktionary defines "dziewczynka" and "nauczycielka" by pointing at another word, but they
# name something of their own, so they count as real words.
OWN_WORD_TAGS = {"diminutive", "augmentative"}

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


def is_inflected_form(entry: dict, pos: str) -> bool:
    """Is this entry in a word's table really a form of that word?"""
    form = entry.get("form") or ""
    tags = set(entry.get("tags", []))
    if not form or " " in form or tags & NON_FORM_TAGS:
        return False
    # Verb tables mark a verb's partner with an aspect ("pójść" lists "iść").
    return not tags <= ASPECT_TAGS if pos == "verb" else bool(tags & INFLECTION_TAGS)


def build_word_forms(records, translated_words: set[str]) -> dict[str, list[str]]:
    """Map each form to every translated word it could belong to.

    Unlike the verb table, this keeps forms that could belong to several words, as in
    {"meble": ["mebel", "meble"]}. The app can settle those using the rest of the book.
    """
    candidates = defaultdict(set)
    for record in records:
        word, pos = record.get("word", "").lower(), record.get("pos")
        if word not in translated_words or pos not in KEPT_POS:
            continue
        candidates[word].add(word)
        for entry in record.get("forms", []):
            if is_inflected_form(entry, pos):
                candidates[entry["form"].lower()].add(word)
    return {form: sorted(words) for form, words in candidates.items()}


def is_inflection_link(sense: dict) -> bool:
    """Does this sense say the entry is an inflected form of another word?

    "pani" links to "pan" as its "female equivalent", but it's a different word.
    """
    tags = set(sense.get("tags", []))
    gloss = (sense.get("glosses") or [""])[-1]
    return (
        bool(sense.get("form_of"))
        and bool(tags & GRAMMAR_TAGS)
        and not tags & RELATED_WORD_TAGS
        and "equivalent" not in gloss
    )


def build_lemma_options(records) -> dict:
    """List the real dictionary words, and the words each spelling could belong to.

    An entry that is only a form of another word, like "szedł", isn't a real word here. A
    female version or diminutive is, because it names something of its own.
    Options are grouped by part of speech and stored as text, like "noun=rozum;verb=rozumieć",
    because a million small dictionaries would take far more memory.
    """
    real_words = set()
    options = defaultdict(lambda: defaultdict(set))
    verbal_noun_records = []
    other_nouns = set()
    for record in records:
        word, pos = record.get("word", "").lower(), record.get("pos")
        if not word or pos not in KEPT_POS:
            continue
        senses = record.get("senses", [])
        if pos == "noun":
            if senses and all(_is_verbal_noun_sense(sense) for sense in senses):
                verbal_noun_records.append(record)
            else:
                other_nouns.add(word)
        if any(_names_its_own_word(sense) for sense in senses):
            real_words.add(word)
            options[word][pos].add(word)
            for entry in record.get("forms", []):
                if is_inflected_form(entry, pos):
                    options[entry["form"].lower()][pos].add(word)
        for sense in senses:
            if is_inflection_link(sense):
                for link in sense["form_of"]:
                    options[word][pos].add(link["word"].lower())

    def encode(by_pos: dict) -> str:
        parts = []
        for pos in sorted(by_pos):
            # A phrase like "chłop pańszczyźniany" can't be a lemma for one word.
            words = sorted(word for word in by_pos[pos] if not re.search(r"[ ,;=]", word))
            if words:
                parts.append(f"{pos}={','.join(words)}")
        return ";".join(parts)

    encoded = {form: encode(by_pos) for form, by_pos in options.items()}
    return {
        "real_words": sorted(real_words),
        "options": {form: value for form, value in encoded.items() if value},
        "verbal_nouns": _verbal_nouns(verbal_noun_records, other_nouns, options),
    }


def _names_its_own_word(sense: dict) -> bool:
    if not sense.get("form_of"):
        return True
    gloss = (sense.get("glosses") or [""])[-1]
    return bool(set(sense.get("tags", [])) & OWN_WORD_TAGS) or "equivalent" in gloss


def _is_verbal_noun_sense(sense: dict) -> bool:
    return bool(sense.get("form_of")) and "verbal noun of" in " ".join(sense.get("glosses", []))


def _verbal_nouns(records: list[dict], other_nouns: set[str], options: dict) -> dict[str, str]:
    """Map the forms of nouns like "robienie" ("doing") to their verb, "robić".

    A noun with a meaning of its own stays separate, like "mieszkanie" ("apartment"). So
    does a noun with two possible verbs, or a spelling that belongs to another word.
    """
    verbs = defaultdict(set)
    spellings = defaultdict(set)
    for record in records:
        word = record["word"].lower()
        spellings[word].add(word)
        for sense in record["senses"]:
            verbs[word].update(link["word"].lower() for link in sense["form_of"])
        for entry in record.get("forms", []):
            if is_inflected_form(entry, "noun"):
                spellings[word].add(entry["form"].lower())

    claims = defaultdict(set)
    for word, forms in spellings.items():
        if len(verbs[word]) == 1 and word not in other_nouns:
            verb = next(iter(verbs[word]))
            for form in forms:
                others = {w for words in options.get(form, {}).values() for w in words} - {word, verb}
                if not others:
                    claims[form].add(verb)
    return {form: next(iter(found)) for form, found in claims.items() if len(found) == 1}


def _words_after(word: str, real_words: set[str], options: dict[str, str]) -> set[str]:
    """The words an entry points to next, or nothing if it's a real word itself."""
    if word in real_words:
        return set()
    following = set()
    for group in options.get(word, "").split(";"):
        following.update(group.partition("=")[2].split(","))
    return following - {word, ""}


def shorten_chains(options: dict[str, str], real_words: set[str]) -> dict[str, str]:
    """Point spellings straight at the final word: "lepsze" to "dobry", not "lepszy".

    On a tie, like "większy" (from "duży" or "wielki"), it stops at the entry it reached.
    """
    shortened = {}
    for form, encoded in options.items():
        groups = []
        for group in encoded.split(";"):
            pos, _, words = group.partition("=")
            final = set()
            for word in words.split(","):
                following = _words_after(word, real_words, options)
                final |= following if len(following) == 1 else {word}
            groups.append(f"{pos}={','.join(sorted(final))}")
        shortened[form] = ";".join(groups)
    return shortened


def fold_leftovers(
    word_forms: dict[str, list[str]], real_words: set[str], options: dict[str, str]
) -> dict[str, str]:
    """Add the spellings the options miss, each pointing straight to its final word.

    These are mostly forms of comparatives and participles, whose own entries point to
    another word: "lepsze" goes through "lepszy" to "dobry". On a tie, like "największy"
    (from "duży" or "wielki"), it stops at the entry it reached. They're stored under "any",
    which matches no part of speech, so they only replace a lemma that isn't a real word.
    """
    folded = {}
    for form, words in word_forms.items():
        if form in options or " " in form:
            continue
        final = set()
        for word in words:
            following = _words_after(word, real_words, options)
            final |= following if len(following) == 1 else {word}
        final = sorted(word for word in final if not re.search(r"[ ,;=]", word))
        if final:
            folded[form] = f"any={','.join(final)}"
    return folded


def write_compressed_json(path: Path, data: dict) -> None:
    # mtime=0 means a rebuild with the same data gives an identical file for Git.
    path.write_bytes(
        gzip.compress(json.dumps(data, ensure_ascii=False, sort_keys=True).encode(), mtime=0)
    )


def main(source: str) -> None:
    with open(source, encoding="utf-8") as handle:
        table = build_table(json.loads(line) for line in handle)
    with open(source, encoding="utf-8") as handle:
        word_forms = build_word_forms((json.loads(line) for line in handle), set(table))
    with open(source, encoding="utf-8") as handle:
        lemma_options = build_lemma_options(json.loads(line) for line in handle)
    real_words = set(lemma_options["real_words"])
    folded = fold_leftovers(word_forms, real_words, lemma_options["options"])
    lemma_options["options"] = {**shorten_chains(lemma_options["options"], real_words), **folded}
    write_compressed_json(LEMMA_OPTIONS_FILE, lemma_options)
    print(
        f"{len(lemma_options['real_words']):,} real words, {len(lemma_options['options']):,} spellings, "
        f"{len(folded):,} of them leftovers, "
        f"{len(lemma_options['verbal_nouns']):,} verbal noun forms, "
        f"{LEMMA_OPTIONS_FILE.stat().st_size / 1e6:.1f} MB"
    )
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
