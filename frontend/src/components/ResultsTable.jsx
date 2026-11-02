import { useState } from 'react'
import { posLabel } from '../lemmaUtils.js'

// Drawing all 12,700 rows of a novel made filter changes about 3.5 times slower (669 ms
// against 194 ms in development mode), so we only draw this many at a time. Search,
// filters and export still use the full list.
const PAGE_SIZE = 200

// Plain data describing the sortable columns, so we don't repeat the same JSX four times.
const SORTABLE_COLUMNS = [
  { key: 'rank', label: 'Rank' },
  { key: 'lemma', label: 'Lemma' },
  { key: 'count', label: 'Count' },
  { key: 'pos', label: 'Part of speech' },
]

function ResultsTable({ rows, sortKey, sortDirection, onSort }) {
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE)

  // A component is just a function, so an ordinary "if" can return a message
  // instead of an empty table.
  if (rows.length === 0) {
    return <p className="empty">No lemmas match these filters.</p>
  }

  return (
    // A "fragment" (<>) groups elements without adding anything extra to the page.
    <>
      {/* The wrapper lets a wide table scroll sideways on a phone instead of the whole page. */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              {SORTABLE_COLUMNS.map((column) => {
                const isActive = column.key === sortKey
                const ariaSort = sortDirection === 'asc' ? 'ascending' : 'descending'
                return (
                  // aria-sort tells screen readers how the table is currently sorted.
                  <th key={column.key} aria-sort={isActive ? ariaSort : 'none'}>
                    <button type="button" onClick={() => onSort(column.key)}>
                      {column.label}
                      {/* "a && b" shows b only when a is true: a common JSX pattern. */}
                      {isActive && <span aria-hidden="true">{sortDirection === 'asc' ? ' ▲' : ' ▼'}</span>}
                    </button>
                  </th>
                )
              })}
              <th>Forms seen</th>
              <th>Example</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, visibleCount).map((entry) => (
              <tr key={entry.lemma}>
                <td className="number">{entry.rank}</td>
                <td lang="pl">
                  <span className="lemma">{entry.lemma}</span>
                  {entry.is_stopword && <span className="tag">stopword</span>}
                </td>
                <td className="number">{entry.count}</td>
                <td>{posLabel(entry.pos)}</td>
                <td lang="pl" className="forms">{entry.forms.join(', ')}</td>
                <td lang="pl" className="example">{entry.example}</td>
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
  )
}

export default ResultsTable
