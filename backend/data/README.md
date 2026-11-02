# Translation data

`translations.json` maps Polish words to short English translations. It's built by `scripts/build_translations.py`, which also shows exactly how the source data was filtered and shortened.

## Source and license

- **Source:** [English Wiktionary](https://en.wiktionary.org/), by its contributors.
- **Extracted by:** [kaikki.org](https://kaikki.org/dictionary/Polish/index.html) using Wiktextract, from the 2026-10-01 Wiktionary dump. See Tatu Ylonen, "Wiktextract: Wiktionary as Machine-Readable Structured Data", LREC 2022.
- **Changes:** selected, shortened and reformatted by this project, plus a small number of hand-written entries listed in `MANUAL_ENTRIES` in the build script.
- **License:** this file is shared under the [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/). This covers the data file only, not the rest of the project's code.
