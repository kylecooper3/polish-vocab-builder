import { useState } from 'react'
import { MERGE_METHOD_LABELS, PAGE_SIZE, filterMerges } from '../lemmaUtils.js'

// A read-only list of every merge, so a person can judge them against their sentences.
function MergeReview({ merges, lemmas }) {
  const [search, setSearch] = useState('')
  const [kind, setKind] = useState('ALL')
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  // The word list already holds each word's final translation, so the API doesn't need
  // to send it twice. A Map is a dictionary, like Python's dict.
  const translations = new Map(lemmas.map((entry) => [entry.lemma, entry.translation]))
  const rows = filterMerges(merges, search, kind)

  return (
    <section className="merge-review" aria-labelledby="review-heading">
      <h2 id="review-heading">Check the merges</h2>
      <p className="section-note">
        Each row is a lemma spaCy gave that isn&apos;t in the dictionary, and the word the app merged it
        into. Read the sentence to judge whether that&apos;s right. This list is for checking only, so
        it doesn&apos;t change the results.
      </p>

      <div className="filters">
        <label className="field field-wide">
          Search
          <input
            type="search"
            placeholder="Any lemma or form"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <label className="field">
          Show
          <select value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="ALL">All merges</option>
            <option value="only_match">{MERGE_METHOD_LABELS.only_match}</option>
            <option value="tie_break">{MERGE_METHOD_LABELS.tie_break}</option>
            <option value="NEW_ROW">Created a new word</option>
          </select>
        </label>
      </div>

      <p className="result-count merge-count" aria-live="polite">
        {rows.length.toLocaleString()} of {merges.length.toLocaleString()} merges match
      </p>

      {rows.length === 0 ? (
        <p className="empty">No merges match.</p>
      ) : (
        <>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>spaCy gave</th>
                  <th>Merged into</th>
                  <th>Translation</th>
                  <th>Count</th>
                  <th>Forms in the book</th>
                  <th>How</th>
                  <th>Example</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, visibleCount).map((merge) => (
                  <tr key={merge.from_lemma}>
                    <td lang="pl">{merge.from_lemma}</td>
                    <td lang="pl" className="lemma">{merge.to_lemma}</td>
                    <td className="translation">{translations.get(merge.to_lemma) || '—'}</td>
                    <td className="number">{merge.count}</td>
                    <td lang="pl" className="forms">{merge.forms.join(', ')}</td>
                    <td className="merge-how">
                      {MERGE_METHOD_LABELS[merge.method]}
                      {merge.new_row && <span className="tag merge-tag">new word</span>}
                    </td>
                    <td lang="pl" className="example">{merge.example}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {rows.length > visibleCount && (
            <div className="show-more">
              <p>
                Showing the first {visibleCount.toLocaleString()} of {rows.length.toLocaleString()}
              </p>
              <button
                type="button"
                className="button"
                onClick={() => setVisibleCount(visibleCount + PAGE_SIZE)}
              >
                Show {PAGE_SIZE} more
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default MergeReview
