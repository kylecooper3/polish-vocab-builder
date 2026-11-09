// Run with "npm test". Uses Node's built-in test runner, so it needs no extra packages.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { applyFilters, coveragePercent, sortLemmas, splitBySpans, toAnkiCsv } from './lemmaUtils.js'

test('the Anki export keeps quotes and commas inside their column', () => {
  const csv = toAnkiCsv([{ lemma: 'mówić', translation: 'to say, to speak', example: 'Rzekł: "Tak, panie".' }])
  assert.equal(csv, '"mówić","to say, to speak","Rzekł: ""Tak, panie""."\n')
})

test('the bold word is found by position, even after an emoji', () => {
  // "🙂" is one character to Python but two to a plain JavaScript string.
  const pieces = splitBySpans('🙂 To jest to.', [[2, 4], [10, 12]])
  assert.deepEqual(pieces, [
    { text: '🙂 ', isMatch: false },
    { text: 'To', isMatch: true },
    { text: ' jest ', isMatch: false },
    { text: 'to', isMatch: true },
    { text: '.', isMatch: false },
  ])
})

test('coverage is a share of the whole book, and zero for an empty one', () => {
  const lemmas = [{ count: 50 }, { count: 30 }, { count: 20 }]
  assert.equal(coveragePercent(lemmas, 200, 2), 40)
  assert.equal(coveragePercent([], 0, 500), 0)
})

test('sorting by count keeps tied words in rank order, in both directions', () => {
  const rows = [
    { rank: 1, count: 5 },
    { rank: 2, count: 1 },
    { rank: 3, count: 1 },
    { rank: 4, count: 1 },
  ]
  assert.deepEqual(sortLemmas(rows, 'count', 'desc').map((row) => row.rank), [1, 2, 3, 4])
  assert.deepEqual(sortLemmas(rows, 'count', 'asc').map((row) => row.rank), [2, 3, 4, 1])
})

test('filters combine, and a blank translation means "not in dictionary"', () => {
  const lemmas = [
    { lemma: 'i', pos: 'CCONJ', count: 9, is_stopword: true, translation: 'and' },
    { lemma: 'sepulka', pos: 'NOUN', count: 3, is_stopword: false, translation: '' },
    { lemma: 'pies', pos: 'NOUN', count: 1, is_stopword: false, translation: 'dog' },
  ]
  const pick = (filters) =>
    applyFilters(lemmas, { pos: 'ALL', minCount: 1, hideStopwords: false, dictionary: 'ALL', ...filters }).map(
      (entry) => entry.lemma,
    )
  assert.deepEqual(pick({ hideStopwords: true, minCount: 2 }), ['sepulka'])
  assert.deepEqual(pick({ dictionary: 'UNKNOWN' }), ['sepulka'])
  assert.deepEqual(pick({ pos: 'NOUN', dictionary: 'KNOWN' }), ['pies'])
})
