import { useState } from 'react'
import Coverage from './components/Coverage.jsx'
import Filters from './components/Filters.jsx'
import ResultsTable from './components/ResultsTable.jsx'
import { applyFilters, posOptions, searchLemmas, sortLemmas } from './lemmaUtils.js'
import { sampleResult } from './sampleData.js'

// A COMPONENT is a function that returns what should appear on screen. React calls it
// whenever its data changes, then updates only the parts of the page that differ.
function App() {
  // STATE is data that can change while the app runs. useState gives us the current
  // value and a function to update it. An ordinary variable wouldn't work here: calling
  // the setter is what tells React to run this function again and redraw the page.
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({ pos: 'ALL', minCount: 1, hideStopwords: false })
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
  const { lemmas, total_tokens: totalTokens } = sampleResult
  const filtered = applyFilters(lemmas, filters)
  const rows = sortLemmas(searchLemmas(filtered, search), sortKey, sortDirection)

  // JSX looks like HTML but is really JavaScript, which is why it uses "className"
  // ("class" is a reserved word) and can include values in {curly braces}.
  return (
    <main className="page">
      <header>
        <h1>Polish Vocab Builder</h1>
        <p className="subtitle">
          Study the words that matter most, counted by dictionary form.
        </p>
      </header>

      {/* Passing values down as attributes is how a parent gives a child its props. */}
      <Coverage lemmas={filtered} totalTokens={totalTokens} />

      <Filters
        search={search}
        onSearchChange={setSearch}
        filters={filters}
        onFilterChange={updateFilter}
        posCodes={posOptions(lemmas)}
      />

      <p className="result-count" aria-live="polite">
        Showing {rows.length} of {lemmas.length} lemmas
      </p>

      <ResultsTable
        rows={rows}
        sortKey={sortKey}
        sortDirection={sortDirection}
        onSort={handleSort}
      />
    </main>
  )
}

export default App
