import { posLabel } from '../lemmaUtils.js'

// PROPS are a component's inputs, like a Python function's arguments. The parent
// (App) owns these values. This component only displays them and reports changes
// by calling the functions it was given.
function Filters({ search, onSearchChange, filters, onFilterChange, posCodes }) {
  return (
    <section className="filters" aria-label="Filters">
      <label className="field field-wide">
        Search
        {/* A "controlled input": React sets what the box shows (value), and every
            keystroke calls onChange to update the state. */}
        <input
          type="search"
          placeholder="Lemma or any form, e.g. psa"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>

      <label className="field">
        Part of speech
        <select
          value={filters.pos}
          onChange={(event) => onFilterChange('pos', event.target.value)}
        >
          <option value="ALL">All</option>
          {/* JSX has no loop syntax, so we turn the list into elements with map().
              "key" gives each item an identity React can track between updates. */}
          {posCodes.map((code) => (
            <option key={code} value={code}>
              {posLabel(code)}
            </option>
          ))}
        </select>
      </label>

      <label className="field field-narrow">
        Minimum count
        <input
          type="number"
          min="1"
          value={filters.minCount}
          onChange={(event) => onFilterChange('minCount', Number(event.target.value))}
        />
      </label>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={filters.hideStopwords}
          onChange={(event) => onFilterChange('hideStopwords', event.target.checked)}
        />
        Hide stopwords
      </label>
    </section>
  )
}

export default Filters
