import { posLabel } from '../lemmaUtils.js'

// Plain data describing the sortable columns, so we don't repeat the same JSX four times.
const SORTABLE_COLUMNS = [
  { key: 'rank', label: 'Rank' },
  { key: 'lemma', label: 'Lemma' },
  { key: 'count', label: 'Count' },
  { key: 'pos', label: 'Part of speech' },
]

function ResultsTable({ rows, sortKey, sortDirection, onSort }) {
  // A component is just a function, so an ordinary "if" can return a message
  // instead of an empty table.
  if (rows.length === 0) {
    return <p className="empty">No lemmas match these filters.</p>
  }

  return (
    // The wrapper lets a wide table scroll sideways on a phone instead of the whole page.
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
          {rows.map((entry) => (
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
  )
}

export default ResultsTable
