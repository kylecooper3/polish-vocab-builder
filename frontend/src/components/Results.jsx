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
import Statistics from './Statistics.jsx'

function Results({ result, filename }) {
  const [view, setView] = useState('words')
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({
    pos: 'ALL',
    minCount: 1,
    hideStopwords: false,
    dictionary: 'ALL',
  })
  const [sortKey, setSortKey] = useState('rank')
  const [sortDirection, setSortDirection] = useState('asc')
  // The lemmas unticked for export. A Set is a list that can answer "is this in here?" quickly.
  const [leftOut, setLeftOut] = useState(new Set())
  const [editingExport, setEditingExport] = useState(false)

  function toggleLeftOut(lemma) {
    // As with filters, React needs a new Set to notice the change, not an edited old one.
    const next = new Set(leftOut)
    if (next.has(lemma)) {
      next.delete(lemma)
    } else {
      next.add(lemma)
    }
    setLeftOut(next)
  }

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
  const exportRows = rows.filter((entry) => !leftOut.has(entry.lemma))

  function handleExport() {
    // Exports every matching row in the current order, not just those drawn on screen.
    const bookName = filename.replace(/\.[^.]+$/, '')
    downloadTextFile(toAnkiCsv(exportRows), `${bookName}-anki.csv`)
  }

  return (
    <>
      <div className="summary-bar">
        <p className="book-summary">
          <strong>{filename}</strong>: {totalTokens.toLocaleString()} words counted,{' '}
          {uniqueLemmas.toLocaleString()} unique lemmas
        </p>

        {/* Hidden rather than removed, so it keeps its setting between views. */}
        <div className="summary-coverage" hidden={view !== 'words'}>
          {/* Passing values down as attributes is how a parent gives a child its props. */}
          <Coverage lemmas={filtered} totalTokens={totalTokens} />
        </div>

        <div className="view-switch" role="group" aria-label="Choose a view">
          <button type="button" aria-pressed={view === 'words'} onClick={() => setView('words')}>
            Word list
          </button>
          <button type="button" aria-pressed={view === 'stats'} onClick={() => setView('stats')}>
            Statistics
          </button>
        </div>
      </div>

      {/* Also hidden rather than removed, so the word list keeps its place and "Show more". */}
      <div hidden={view !== 'words'}>
        <Filters
          search={search}
          onSearchChange={setSearch}
          filters={filters}
          onFilterChange={updateFilter}
          posCodes={posOptions(lemmas)}
        >
          <button
            type="button"
            className="button filters-action"
            onClick={handleExport}
            disabled={exportRows.length === 0}
          >
            Export {exportRows.length.toLocaleString()} to CSV for Anki
          </button>
        </Filters>

        <p className="result-count" aria-live="polite">
          {rows.length.toLocaleString()} of {lemmas.length.toLocaleString()} lemmas match ·{' '}
          <button
            type="button"
            className="text-button"
            aria-pressed={editingExport}
            onClick={() => setEditingExport(!editingExport)}
          >
            {editingExport ? 'Done editing' : 'Edit export list'}
          </button>
          {leftOut.size > 0 && (
            <>
              {' '}· {leftOut.size.toLocaleString()} left out of the export{' '}
              <button type="button" className="text-button" onClick={() => setLeftOut(new Set())}>
                Include all
              </button>
            </>
          )}
        </p>

        <ResultsTable
          rows={rows}
          sortKey={sortKey}
          sortDirection={sortDirection}
          onSort={handleSort}
          leftOut={leftOut}
          onToggleLeftOut={toggleLeftOut}
          showExportColumn={editingExport}
        />
      </div>

      {view === 'stats' && <Statistics result={result} />}
    </>
  )
}

export default Results
