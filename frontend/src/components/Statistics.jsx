import { matchGroups } from '../lemmaUtils.js'
import MergeReview from './MergeReview.jsx'

function Statistics({ result }) {
  const { totalRows, totalOccurrences, groups } = matchGroups(result.match_stats)

  return (
    <>
      <section aria-labelledby="match-heading">
        <h2 id="match-heading">How words matched the dictionary</h2>
        <p className="section-note">
          Counted before merging: spaCy produced {totalRows.toLocaleString()} rows, which became{' '}
          {result.unique_lemmas.toLocaleString()} in the word list. Being in the dictionary doesn&apos;t
          prove a lemma is right, only that it&apos;s a real word.
        </p>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Group</th>
                <th>Words</th>
                <th>Share of words</th>
                <th>Occurrences</th>
                <th>Share of the book</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((group) => (
                <tr key={group.key}>
                  <td className="group-cell">
                    <span className="lemma">{group.label}</span>
                    <span className="group-description">{group.description}</span>
                  </td>
                  <td className="number">{group.rows.toLocaleString()}</td>
                  <td className="number">{group.rowShare.toFixed(1)}%</td>
                  <td className="number">{group.occurrences.toLocaleString()}</td>
                  <td className="number">{group.occurrenceShare.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">Total</th>
                <td className="number">{totalRows.toLocaleString()}</td>
                <td className="number">100%</td>
                <td className="number">{totalOccurrences.toLocaleString()}</td>
                <td className="number">100%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>

      <MergeReview merges={result.merges} lemmas={result.lemmas} />
    </>
  )
}

export default Statistics
