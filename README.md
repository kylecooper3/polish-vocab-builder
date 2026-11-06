# Polish Vocab Builder

[![Tests](https://github.com/kylecooper3/polish-vocab-builder/actions/workflows/tests.yml/badge.svg)](https://github.com/kylecooper3/polish-vocab-builder/actions/workflows/tests.yml)

Upload a Polish book as a PDF or EPUB and get a frequency list of its vocabulary, counted by dictionary form, so you can study the most useful words first. Each word comes with its English meaning, every form seen in the book, and an example sentence, and the list exports to Anki.

**[Try the live demo](https://kylecooper3.github.io/polish-vocab-builder/)**, which has one public-domain story already analyzed. You can filter, search and export, but uploading your own book needs the Python backend, so that only works when you [run the app yourself](#setup).

![The results screen, showing coverage, filters and a table of Polish words with translations](docs/screenshot.jpg)

## Why lemmatization matters for Polish

Polish is heavily inflected: a word changes form depending on its role in the sentence. `mam`, `masz` and `ma` are all forms of `mieć` ("to have"), and irregular forms can look nothing like the dictionary word, such as `szedł` from `iść` ("to go").

Counting raw words would split one word into many entries and bury the words that matter. In *Lalka* by Bolesław Prus, `mieć` appears in **34 different forms**. Lemmatization reduces each form to its dictionary form, or *lemma*, so all 34 count as one word to learn.

It also makes the results useful for planning. In that novel (111,198 counted words):

| Most frequent lemmas | Share of the book's words |
|---|---|
| Top 100 | 48.9% |
| Top 500 | 69.7% |
| Top 1,000 | 78.4% |
| Top 5,000 | 95.5% |

## Features

- **Upload** a PDF or EPUB by drag and drop
- **Sortable, searchable table** of lemmas with rank, count, part of speech, English translation, forms seen and an example sentence
- **Search in either language**, by any Polish form or English meaning
- **Filters** for part of speech, minimum count, stopwords and whether a word is in the dictionary, which can surface words an author invented
- **Coverage stat**, such as "the top 500 lemmas cover 69.7% of the book"
- **CSV export** for Anki, with the word, translation and example sentence, which also opens correctly in Excel
- **Per-word export toggle** to leave out single words you don't want on a flashcard
- **Statistics view** showing how the book's words matched the dictionary, with a searchable list of every merge to check by hand

## Architecture

```mermaid
flowchart TD
    A[React frontend] -->|POST /analyze with the file| B[FastAPI]

    subgraph pipeline [Backend pipeline]
        B --> C["extraction.py<br/>PDF or EPUB to raw text"]
        C --> D["cleaning.py<br/>hyphenation, headers, page numbers"]
        D --> E{Text readable?}
        E -->|No| F[Clear error message]
        E -->|Yes| G["lemmas.py<br/>spaCy lemmas and part of speech"]
        G --> H["translations.py<br/>English meaning for each lemma"]
    end

    H -->|JSON word list| A
    F -->|422 error| A
    A --> I[Filter, sort, search and coverage in the browser]
    I --> J[Anki CSV download]
```

**Stack:** Python, FastAPI, spaCy (`pl_core_news_lg`), PyMuPDF, ebooklib, BeautifulSoup, React, Vite. Tests use pytest and run on every push with GitHub Actions.

## Setup

You'll need Python 3.15 (developed and tested on this version) and Node.js. Installing the backend downloads the 574 MB Polish language model. Everything runs locally and costs nothing.

### Backend

```bash
cd backend
python -m venv .venv
```

Then install the packages and start the server. On Windows:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

On macOS or Linux:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

Leave this terminal running. The backend has no page of its own, so you don't need to open its address. If you're curious, its API docs are at `http://127.0.0.1:8000/docs`.

### Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

On Windows, if PowerShell says running scripts is disabled, use `npm.cmd` in place of `npm`.

### Open the app

Keep both terminals running, then go to `http://localhost:5173` in your browser. That's the only address you need.

To try it, drag a Polish PDF or EPUB onto the upload box. If you don't have one, use the free story included in this project: the file `katarynka.epub` in the `sample` folder.

**About the addresses:** `localhost` and `127.0.0.1` both mean your own computer, so your copy of the app is only available to you. `5173` and `8000` are the default ports of Vite and Uvicorn, the programs that run the frontend and backend. The app expects those exact ports (they're set in `frontend/src/api.js` and `backend/app/main.py`), so if another program is using one, close it before starting the app.

### Tests

From the `backend` folder, using the same Python as above:

```bash
python -m pytest
```

## API

`POST /analyze` takes a file as `multipart/form-data`, plus an optional `exclude_stopwords=true` query parameter.

```json
{
  "total_tokens": 3541,
  "unique_lemmas": 1263,
  "lemmas": [
    {
      "lemma": "mecenas",
      "count": 33,
      "rank": 14,
      "pos": "NOUN",
      "translation": "patron, sponsor; lawyer, advocate",
      "forms": ["mecenas", "mecenasa", "mecenasem", "mecenasowi"],
      "example": "Gdy został mecenasem, czoło, skutkiem natężonej pracy umysłowej, urosło mu aż do ciemienia...",
      "example_spans": [[11, 20]],
      "is_stopword": false
    }
  ],
  "match_stats": {
    "in_dictionary": { "rows": 1129, "occurrences": 3300 },
    "merged": { "rows": 165, "occurrences": 199 },
    "unresolved": { "rows": 0, "occurrences": 0 },
    "no_match": { "rows": 36, "occurrences": 42 }
  },
  "merges": [
    {
      "from_lemma": "krążk",
      "to_lemma": "krążek",
      "count": 1,
      "pos": "NOUN",
      "forms": ["krążkiem"],
      "example": "Czerwona wiśnia stała się dla niej wiśnią gładką, okrągłą i miękką...",
      "example_spans": [[113, 121]],
      "method": "only_match",
      "new_row": true
    }
  ]
}
```

`example_spans` gives the start and end position of each use of the word in its example, measured in characters, so the page can bold exactly the words counted for that row.

`match_stats` shows how spaCy's answers matched the dictionary. Each use of a word counts in the group its form landed in, and each spaCy row counts once, under its biggest group. `merges` lists each move from spaCy's lemma to another word, biggest first. `method` is `only_match` when a form pointed to one word, or `tie_break` when the word already in the book was chosen. `new_row` means the book had no correct row for that word. Both describe the whole book, even with `exclude_stopwords=true`.

| Status | Meaning |
|---|---|
| 400 | The file is corrupt or password-protected |
| 413 | The file is over the 50 MB limit |
| 415 | The file isn't a PDF or EPUB |
| 422 | No readable text, such as a scanned book or a damaged text layer |

## Design decisions

**A separate module for each stage.** Extraction, cleaning and lemmatization each have one job, take plain data and return plain data. That means each can be tested without the others, and the web layer stays thin.

**Refuse damaged PDFs instead of guessing.** A PDF can look perfect on screen while its hidden text layer is wrong. In one real PDF, every `j` came out as the Telugu letter `గ`, and some spaces vanished, so `Inaczej świat` became `Inaczeగświat`. That can't be reliably repaired, and a confident list of fake words would be worse for a learner than an error. The app checks for this before running spaCy, so a bad file fails in about a second.

**Process long books in small pieces, one at a time.** spaCy's memory use grows with text size. Measured on a 780,000-character novel, 20,000-character chunks processed one at a time used 79 MB on top of the model, compared with about 2,600 MB for larger chunks at spaCy's default batch size, at about the same speed. Chunking alone wasn't enough, because spaCy's default batching groups the chunks back together.

**Only run the parts of spaCy the app uses.** spaCy's Polish model has several parts, and the app reads only the lemma, part of speech, grammar tags and sentence breaks. Turning off the two it never reads, name recognition and the fine-grained tagger, made *Lalka* about 30% faster (32.6 to 22.9 seconds) with every word counted the same. Swapping the parser for spaCy's lighter sentence finder would save about 4 more seconds, but it cut dialogue such as "— mruczał radca Węgrowicz." into separate sentences, which made worse examples. The smaller Polish models weren't any faster, only lighter, and they changed about 1% of words, often for the worse.

**Clean up spaCy's output.** spaCy turns `myślałem` ("I thought") into `myśleć być`, because Polish past-tense endings behave like an attached form of "to be". The app keeps only the first word, so these count as `myśleć`. It also gives each lemma one stopword answer, since spaCy's list holds word forms and flags `mam` but not `masz`.

**Check spaCy against Wiktionary, one form at a time.** spaCy reads context but can invent words, turning `krążkiem` into `krążk` or `poszedłem` into `poszedć`. Wiktionary only has real words but can't read context. So once the whole book is read, each form's lemma and part of speech is compared with about 1 million Wiktionary forms:

1. If they agree, the lemma stays.
2. If spaCy's lemma isn't a real word, the form's dictionary word replaces it, using the part of speech to choose. An entry that's only a form of another word, like `rozumie`, doesn't count as real, so it goes to `rozumieć`. If several words still fit, the app picks the one already in this book, and otherwise leaves it alone.
3. If spaCy's lemma is a real word, it's only replaced when the form can't belong to it and exactly one other word fits, so `jedziemy` under `jeść` ("to eat") becomes `jechać` ("to go"). Only true inflections count, so `pani` ("Mrs.") doesn't become `pan` ("Mr."), and `ze` stays under `z`, because it's only another spelling.

This replaced two earlier checks, one for verbs while reading and one for whole rows at the end. Simply removing the verb check made results worse: on *Lalka*, it added 388 false rows. So did trusting Wiktionary whenever the two disagreed. The final rule took *Lalka* from 10,235 rows to 9,785 and from 1,371 blank rows to 1,260. In a sample of 100 changes judged against their sentences, 76 were better, 20 were debatable and 4 were worse, and most of the known bad cases were then listed as exceptions. That judging wasn't done by a native speaker.

**Keep every Wiktionary lookup in one list.** The app used to load two tables of forms, and only about 4% of the second was ever read. Moving that part into the first gave identical results on *Lalka* and cut peak memory from about 1.6 GB to about 1.3 GB. That part then stayed as a separate fallback list, until a closer look showed it was covering for a gap in the first one.

**Treat related words as words.** Wiktionary defines `dziewczynka` ("girl") and `nauczycielka` ("female teacher") by pointing at another word, so a rule meant for grammatical forms like `szedł` was skipping about 3,450 real words. Female versions and diminutives now count as their own words, which also fixed `biedaczka` and `kuzynek` being filed under the wrong gender. Everything else points straight at its final word, so `lepsze` goes to `dobry` without stopping at `lepszy`, and the fallback is gone. If the next step is a tie, it stops where it is. `większy` and `największy` are the superlatives of both `duży` and `wielki`, so a hand-written rule counts them under `duży`. On *Lalka*, this took the list from 9,750 rows to 9,617 with one fewer blank row. Of 60 sampled changes read against their sentences, one looked worse (`ogródki` in the idiom *bez ogródki*), though that judging wasn't done by a native speaker.

**Fold alternative spellings into the main word.** `patrzę` ("I look") could be `patrzeć` or `patrzyć`, so the app treated it as a tie and left it unresolved. But Wiktionary calls `patrzyć` an "alternative form of" `patrzeć`, so it's the same word. When one option is only an alternative form of another option for the same spelling, the alternative is dropped. It never folds into a word that isn't already an option, because some links point to dialect words: `ja` ("I") is listed as an alternative of `jo`. A word with a current meaning of its own isn't treated as an alternative either, so `ospa` ("pox") isn't folded into the rare `osep`. On *Lalka*, this settled 41 of the 101 unresolved uses and moved 66 uses in all, taking the book from 9,617 rows to 9,590. All 42 moved words were reviewed and none looked wrong, though not by a native speaker.

**Count verbal nouns under their verb.** `robienie` ("doing") is technically a noun, but it only names the action, so a learner studies it with `robić`. A word with a meaning of its own stays separate, like `mieszkanie` ("apartment"), and so does any word with two possible verbs, like `tępienie`, or a spelling that belongs to another word. This only applies to words tagged as nouns, because `zawzięcie` can also be an adverb. On *Lalka*, it moved 51 uses, taking the book to 9,750 rows and 1,222 blank rows. Each kind of change was read against its sentence, again not by a native speaker.

**Split pronouns by gender and number.** spaCy files `on` ("he"), `ona` ("she"), `ono` ("it"), `oni` and `one` (both "they") under one lemma. That's a fair grammatical view, but it shows a learner "she" under "he". The app uses spaCy's gender and number tags to give each its own row, with forms like `go` under `on` and `ją` under `ona`. A sample of 30 uses per row from *Lalka* showed this works for `on` and `ona` (all 30 correct in each), but exposed a problem with `ono`: only 7 of 30 were right, because `jego` and `nim` are spelled the same for "he" and "it" and spaCy often guessed "it". So only `ono` and `je` count as "it" now, and those shared forms stay under `on`.

**Make the corrections checkable.** An automatic merge looks just as confident when it's wrong, so the Statistics view lists each one with its sentence and how it was decided. The list is read-only, because undoing merges would add a second way for results to change and nowhere to save it. The figures are recorded at the moment each decision is made rather than worked out again afterwards, so they show what the app actually did.

**Say "not in dictionary", not "invented".** The app can't tell a word an author made up from a rare real word or a spaCy mistake, because all three simply have no entry. So the filter describes what's actually known. Combining it with a minimum count helps, because a word an author coined and keeps using comes up repeatedly.

**Filter in the browser, not on the server.** Analyzing a novel takes about 23 seconds, while filtering takes a fraction of one. The API returns every lemma with its stopword flag, so filters respond straight away without re-analyzing the book.

**Measure coverage honestly.** Coverage is always a share of every counted word in the book. Hiding stopwords lowers the figure, from 69.7% to 26.5% for the top 500 in *Lalka*, rather than making it look better.

**Draw 200 table rows at a time.** A novel can produce about 10,000 lemmas. Drawing them all made filter changes about 3.5 times slower, so the table draws 200 and offers "Show more", while search, filters and export still use the full list.

**A dictionary rather than machine translation.** A lone word has no context, so a translator has to guess, while a dictionary can show that `zamek` means both "lock" and "castle". English meanings come from Wiktionary, which is free, works offline and sends nothing to a third party. They cover 98% of the word occurrences in *Lalka*.

**Automatic rules, plus a small reviewed list for common words.** Rules handle over 145,000 words, but they get some common ones wrong. So about 180 hand-written fixes are applied on top, in [`translation_overrides.json`](backend/data/translation_overrides.json). The words to review were chosen from a frequency list of contemporary Polish rather than from one novel, which would skew toward its own vocabulary.

**A static demo instead of a hosted server.** The language model and word tables need a server with about 1.3 GB of memory, which isn't free to keep running everywhere. So the live demo is only the frontend on GitHub Pages, showing results saved ahead of time by the real pipeline. A test fails if those saved results stop matching the pipeline. The trade-off is that visitors can't upload their own book.

**Never store uploads.** Books are processed in memory and discarded, apart from a temporary file for EPUB parsing that's deleted straight away. `.gitignore` also blocks PDFs and EPUBs outside `sample/`, so copyrighted books can't be committed by accident.

## Limitations

- **Lemmatization isn't perfect.** spaCy's model makes mistakes, especially on rare words and older spelling. Characters' names are sometimes tagged as ordinary words, and ordinary words as names or verbs. A wrong lemma that's a real word is only caught when exactly one other word fits, so some get through, and merges were checked by sampling rather than one by one. spaCy's tags can also be wrong, which can send a word to the wrong entry, such as `zbroi` in "Austria zbroi się". Hyphenated compounds are counted as two separate words.
- **The two words for "they" are often mixed up.** `ich`, `im`, `nich` and `nimi` are spelled the same for `oni` and `one`, so spaCy has to guess from context. In a sample from *Lalka*, 22 of 30 `oni` uses and 17 of 30 `one` uses were right. Both rows show "they", so the meaning is still correct, but their counts are only rough. "It" is undercounted, because neuter uses of `jego` and `nim` are counted under `on`. Possessives also stay with their pronoun, so `jego` ("his") appears under `on` ("he").
- **Words outside the dictionary can be split.** With no dictionary entry to merge into, one word can appear as several rows if spaCy gives its forms different lemmas, as with `fizjognomia` and `fizjognomii` in *Lalka*. An author's invented word could be split the same way. Invented names are excluded along with all other names, because spaCy can't tell `Trurl` from `Warszawa`.
- **Translations don't use context.** `mecenas` shows both "patron" and "lawyer", but only one applies in a given book. Each entry shows at most two meanings, so a less common one may be missing, and the example sentence is there to help. About 13% of a novel's distinct words have no translation, though they make up only 2% of its word occurrences.
- **Hand-written translations are unverified.** They haven't been reviewed by a native speaker.
- **Word meanings can be merged.** `wybory` is counted under `wybór` ("choice"), so its separate meaning of "elections" isn't shown.
- **PDF cleaning has only been tested at full length on a generated PDF.** It was checked by laying out a novel with headers, page numbers and hyphenation, then comparing the results to its EPUB. Real PDFs from other publishers may differ, and their footnotes will be counted as text.
- **Publisher material can be counted.** Footnotes, title pages and notices are removed for standard EPUB markup and for Wolne Lektury books, but other publishers' front and back matter will be included.
- **Scanned books aren't supported,** because they have no text layer and would need OCR.
- **Only the backend has automated tests.** The frontend was tested by hand in a browser.
- **Stopwords come from spaCy's list,** which includes some useful words, such as `pan` ("sir").
- **Language isn't detected.** An English book would produce a meaningless list rather than an error.

## Future ideas

- **Distinctive words:** compare a book's frequencies with Polish in general, to surface the words that are unusually common in this particular book
- **Known-words list:** hide words you've already learned, and show what coverage you'd reach by learning the next 100
- **Choosing the right meaning from context,** using word-sense disambiguation
- **OCR** for scanned books
- **A hosted backend** so anyone can upload a book, on a host such as Hugging Face Spaces that can fit the app's roughly 1.3 GB memory use
- **Frontend tests** for filtering, sorting and CSV export

## License

This project's code is licensed under the [GNU General Public License v3.0](LICENSE). The data below keeps its own license.

- **Sample book:** *Katarynka* by Bolesław Prus, public domain, from [Wolne Lektury](https://wolnelektury.pl/katalog/lektura/katarynka/). See [`sample/README.md`](sample/README.md).
- **Translations and word forms:** derived from [English Wiktionary](https://en.wiktionary.org/) via [kaikki.org](https://kaikki.org/), under CC BY-SA 4.0. See [`backend/data/README.md`](backend/data/README.md).
- **Language model:** spaCy's `pl_core_news_lg` is GPL-3.0 licensed. It's downloaded during setup and isn't included in this repository.
