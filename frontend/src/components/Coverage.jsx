import { useState } from 'react'
import { coveragePercent } from '../lemmaUtils.js'

function Coverage({ lemmas, totalTokens }) {
  // No other component needs topN, so it lives here rather than in App.
  // A good rule: keep state in the lowest component that needs it.
  const [topN, setTopN] = useState(500)

  // Asking for the top 500 of a 17-word list really means the top 17. A blank, zero or
  // negative box means at least the top word, rather than a nonsense figure.
  const shown = Math.max(1, Math.min(topN, lemmas.length))
  const percent = coveragePercent(lemmas, totalTokens, shown)

  return (
    <section className="coverage">
      <p className="coverage-figure">{percent.toFixed(1)}%</p>
      <div>
        <p>
          of the book is covered by the top <strong>{shown}</strong> lemmas in your filtered
          list.
        </p>
        <label className="coverage-control">
          Top
          <input
            type="number"
            min="1"
            value={topN}
            onChange={(event) => setTopN(Number(event.target.value))}
          />
          lemmas
        </label>
      </div>
    </section>
  )
}

export default Coverage
