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
export function applyFilters(lemmas, { pos, minCount, hideStopwords }) {
  return lemmas.filter(
    (entry) =>
      (pos === 'ALL' || entry.pos === pos) &&
      entry.count >= minCount &&
      !(hideStopwords && entry.is_stopword),
  )
}

// Finds a word by its dictionary form or by any form seen in the book,
// so searching "psa" finds "pies" if that form appeared.
export function searchLemmas(lemmas, query) {
  const text = query.trim().toLowerCase()
  if (!text) return lemmas
  return lemmas.filter(
    (entry) =>
      entry.lemma.includes(text) || entry.forms.some((form) => form.includes(text)),
  )
}

export function sortLemmas(lemmas, key, direction) {
  // [...lemmas] sorts a copy. Array.sort changes the array it's given, and React
  // expects us never to change existing data directly.
  const sorted = [...lemmas].sort((a, b) => {
    if (typeof a[key] === 'number') return a[key] - b[key]
    // 'pl' puts Polish letters in the right place: "ł" comes right after "l", not after "z".
    return String(a[key]).localeCompare(String(b[key]), 'pl')
  })
  return direction === 'asc' ? sorted : sorted.reverse()
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
