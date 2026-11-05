# Translation data

`translations.json` maps Polish words to short English translations. It's built by `scripts/build_translations.py`, which also shows exactly how the source data was filtered and shortened.

## Source and license

- **Source:** [English Wiktionary](https://en.wiktionary.org/), by its contributors.
- **Extracted by:** [kaikki.org](https://kaikki.org/dictionary/Polish/index.html) using Wiktextract, from the 2026-10-01 Wiktionary dump. See Tatu Ylonen, "Wiktextract: Wiktionary as Machine-Readable Structured Data", LREC 2022.
- **Changes:** selected, shortened and reformatted by this project.
- **License:** this file is shared under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/). This covers the data file only, not the rest of the project's code.

## Word forms

`word_forms.json.gz` maps forms of all kinds to every dictionary word they could belong to, such as `krążkiem` to `krążek`, or `meble` to both `mebel` and `meble`. It's built by the same script from the same source, and is shared under the same license. The app uses it as a fallback for lemmas that aren't in the dictionary. Related words listed in an entry, such as the diminutive `piesek` under `pies`, are left out, because they're different words.

`lemma_options.json.gz` holds the same kind of information, grouped by part of speech, such as `rozumie` to `noun=rozum;verb=rozumieć`, plus a list of the real dictionary words. An entry that's only a form of another word, like `szedł`, isn't counted as real. The app uses it to check each of spaCy's answers. It's built by the same script and shared under the same license.

## Hand-written fixes

`translation_overrides.json` holds fixes for common words where the automatic result was poor or missing. These entries are written by hand rather than taken from Wiktionary, and they replace the automatic translation when the app loads. To change one, edit the file and restart the backend. No rebuild is needed.

The words to review were chosen using the top 1,000 lemmas of the [KWJP frequency lists](https://kwjp.pl/lists/doc/about/en) (Institute of Computer Science, Polish Academy of Sciences), compiled from a balanced corpus of contemporary Polish. That list states no license on its site, so it isn't included in this repository.
