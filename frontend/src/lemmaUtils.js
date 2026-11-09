// Plain JavaScript logic with no React in it, which keeps it easy to read and test.

// spaCy's part-of-speech codes, in words a learner would recognize.
const POS_LABELS = {
  ADJ: 'Adjective',
  ADP: 'Preposition',
  ADV: 'Adverb',
  AUX: 'Auxiliary verb',
  CCONJ: 'Conjunction',
  DET: 'Determiner',
  INTJ: 'Interjection',
  NOUN: 'Noun',
  NUM: 'Number',
  PART: 'Particle',
  PRON: 'Pronoun',
  SCONJ: 'Subordinating conjunction',
  VERB: 'Verb',
}

export function posLabel(pos) {
  return POS_LABELS[pos] ?? pos
}

// The part-of-speech options that actually appear in this book.
export function posOptions(lemmas) {
  const codes = new Set(lemmas.map((entry) => entry.pos))
  return [...codes].sort((a, b) => posLabel(a).localeCompare(posLabel(b)))
}

// Decides which words you want to study. Keeps the API's order, most frequent first.
export function applyFilters(lemmas, { pos, minCount, hideStopwords, dictionary }) {
  return lemmas.filter(
    (entry) =>
      (pos === 'ALL' || entry.pos === pos) &&
      entry.count >= minCount &&
      !(hideStopwords && entry.is_stopword) &&
      matchesDictionaryFilter(entry, dictionary),
  )
}

// A blank translation means the word isn't in the dictionary. That could be a word an
// author invented, a rare real word or a spaCy mistake, and the app can't tell which.
function matchesDictionaryFilter(entry, dictionary) {
  if (dictionary === 'KNOWN') return entry.translation !== ''
  if (dictionary === 'UNKNOWN') return entry.translation === ''
  return true
}

// Splits a sentence into pieces, marking the words the backend counted for this row. It
// goes by position rather than spelling, because "to" can belong to "ten" in one place
// and to "to" in another. Array.from counts characters the way Python does: plain string
// positions in JavaScript would drift after a character like an emoji.
export function splitBySpans(sentence, spans) {
  const characters = Array.from(sentence)
  const piece = (from, to, isMatch) => ({ text: characters.slice(from, to).join(''), isMatch })

  const pieces = []
  let position = 0
  for (const [start, end] of spans) {
    pieces.push(piece(position, start, false), piece(start, end, true))
    position = end
  }
  pieces.push(piece(position, characters.length, false))
  return pieces.filter((part) => part.text)
}

// Turns a time into words: "under a second", "32 seconds" or "2 min 5 sec".
export function formatDuration(milliseconds) {
  const seconds = Math.round(milliseconds / 1000)
  if (seconds < 1) return 'under a second'
  if (seconds === 1) return '1 second'
  if (seconds < 60) return `${seconds} seconds`
  return `${Math.floor(seconds / 60)} min ${seconds % 60} sec`
}

// How many rows to draw at a time in the long tables.
export const PAGE_SIZE = 200

// The four groups a row can fall into, worked out from the API's match_stats. Each one
// gets its share of all rows and of all word occurrences, because the two differ a lot:
// a merged word is often rare, so it can be many rows but little of the book.
export function matchGroups(stats) {
  const groups = [
    {
      key: 'in_dictionary',
      label: 'In the dictionary',
      description: "spaCy's lemma was found as it was.",
    },
    {
      key: 'merged',
      label: 'Merged',
      description: "spaCy's lemma was replaced, because the form in the book pointed to another word.",
    },
    {
      key: 'unresolved',
      label: 'Possible match, not merged',
      description: "The form matched the dictionary, but the app couldn't settle on one word.",
    },
    {
      key: 'no_match',
      label: 'No match',
      description: 'Not found at all: an invented word, a rare word or a spaCy mistake.',
    },
  ]
  const totalRows = groups.reduce((sum, group) => sum + stats[group.key].rows, 0)
  const totalOccurrences = groups.reduce((sum, group) => sum + stats[group.key].occurrences, 0)
  const share = (part, total) => (total === 0 ? 0 : (part / total) * 100)

  return {
    totalRows,
    totalOccurrences,
    groups: groups.map((group) => ({
      ...group,
      rows: stats[group.key].rows,
      occurrences: stats[group.key].occurrences,
      rowShare: share(stats[group.key].rows, totalRows),
      occurrenceShare: share(stats[group.key].occurrences, totalOccurrences),
    })),
  }
}

export const MERGE_METHOD_LABELS = { only_match: 'Only match', tie_break: 'Tie-break' }

// Narrows the merge list by how each merge was decided and by any word it involves.
export function filterMerges(merges, query, kind) {
  const text = query.trim().toLowerCase()
  return merges.filter(
    (merge) =>
      (kind === 'ALL' ||
        (kind === 'NEW_ROW' ? merge.new_row : merge.method === kind)) &&
      (!text ||
        merge.from_lemma.includes(text) ||
        merge.to_lemma.includes(text) ||
        merge.forms.some((form) => form.includes(text))),
  )
}

// Finds a word by its dictionary form, any form seen in the book, or its English
// meaning. So "dog" finds "pies", and so does "psa" if the book uses that form.
export function searchLemmas(lemmas, query) {
  const text = query.trim().toLowerCase()
  if (!text) return lemmas
  return lemmas.filter(
    (entry) =>
      entry.lemma.includes(text) ||
      entry.forms.some((form) => form.includes(text)) ||
      entry.translation.toLowerCase().includes(text),
  )
}

export function sortLemmas(lemmas, key, direction) {
  // Flipping the comparison, rather than reversing the sorted list, keeps words that tie
  // in their original rank order: sort leaves equal items where they were.
  const sign = direction === 'asc' ? 1 : -1
  // [...lemmas] sorts a copy. Array.sort changes the array it's given, and React
  // expects us never to change existing data directly.
  return [...lemmas].sort((a, b) => {
    if (typeof a[key] === 'number') return sign * (a[key] - b[key])
    // 'pl' puts Polish letters in the right place: "ł" comes right after "l", not after "z".
    return sign * String(a[key]).localeCompare(String(b[key]), 'pl')
  })
}

// CSV format for importing into Anki: one card per line, with the word, its translation
// and an example. There's no header row because Anki would turn it into a flashcard.
// Doubling any quote mark and wrapping each field in quotes stops commas or quotes in
// a sentence breaking the columns.
export function toAnkiCsv(lemmas) {
  const quote = (text) => `"${text.replaceAll('"', '""')}"`
  return (
    lemmas
      .map((entry) => [entry.lemma, entry.translation, entry.example].map(quote).join(','))
      .join('\n') + '\n'
  )
}

// Browsers have no "save file" function for text made in the page. So we wrap the text
// in a Blob (file-like data), give it a temporary URL, and click a hidden download link.
// \uFEFF is an invisible marker saying the file is UTF-8. Without it, Excel guesses another
// encoding and "łódź" turns into "Å‚Ã³dÅº". Anki ignores the marker when importing.
export function downloadTextFile(text, filename) {
  const url = URL.createObjectURL(new Blob(['\uFEFF', text], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

// What share of all counted words in the book do the first topN lemmas account for?
// totalTokens always covers the whole book, so hiding stopwords lowers this figure
// instead of flattering it.
export function coveragePercent(lemmas, totalTokens, topN) {
  if (totalTokens === 0) return 0
  const covered = lemmas
    .slice(0, topN)
    .reduce((sum, entry) => sum + entry.count, 0)
  return (covered / totalTokens) * 100
}
