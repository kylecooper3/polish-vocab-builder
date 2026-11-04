import { useState } from 'react'
import {
  applyFilters,
  downloadTextFile,
  posOptions,
  searchLemmas,
  sortLemmas,
  toAnkiCsv,
} from '../lemmaUtils.js'
import Coverage from './Coverage.jsx'
import Filters from './Filters.jsx'
import ResultsTable from './ResultsTable.jsx'

function Results({ result, filename }) {
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({
    pos: 'ALL',
    minCount: 1,
    hideStopwords: false,
    dictionary: 'ALL',
  })
  const [sortKey, setSortKey] = useState('rank')
  const [sortDirection, setSortDirection] = useState('asc')

  function updateFilter(name, value) {
    // {...filters} copies the old object, then we overwrite one field. Passing React a
    // new object, rather than changing the old one, is how it notices the change.
    setFilters({ ...filters, [name]: value })
  }

  function handleSort(key) {
    if (key === sortKey) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      // For counts, the biggest number first is the more useful starting point.
      setSortDirection(key === 'count' ? 'desc' : 'asc')
    }
  }

  // None of these need their own state: they can always be worked out from the state
  // above. Storing them separately would just create copies that could get out of sync.
  const { lemmas, total_tokens: totalTokens, unique_lemmas: uniqueLemmas } = result
  const filtered = applyFilters(lemmas, filters)
  const rows = sortLemmas(searchLemmas(filtered, search), sortKey, sortDirection)

  function handleExport() {
    // Exports every matching row in the current order, not just those drawn on screen.
    const bookName = filename.replace(/\.[^.]+$/, '')
    downloadTextFile(toAnkiCsv(rows), `${bookName}-anki.csv`)
  }

  return (
    <>
      <p className="book-summary">
        <strong>{filename}</strong>: {totalTokens.toLocaleString()} words counted,{' '}
        {uniqueLemmas.toLocaleString()} unique lemmas
      </p>

      {/* Passing values down as attributes is how a parent gives a child its props. */}
      <Coverage lemmas={filtered} totalTokens={totalTokens} />

      <Filters
        search={search}
        onSearchChange={setSearch}
        filters={filters}
        onFilterChange={updateFilter}
        posCodes={posOptions(lemmas)}
      />

      <div className="results-bar">
        <p className="result-count" aria-live="polite">
          {rows.length.toLocaleString()} of {lemmas.length.toLocaleString()} lemmas match
        </p>
        <button
          type="button"
          className="button"
          onClick={handleExport}
          disabled={rows.length === 0}
        >
          Export {rows.length.toLocaleString()} to CSV for Anki
        </button>
      </div>

      <ResultsTable
        rows={rows}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={handleSort}
      />
    </>
  )
}

export default Results
