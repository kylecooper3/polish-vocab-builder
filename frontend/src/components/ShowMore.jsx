import { PAGE_SIZE } from '../lemmaUtils.js'

// The button under a long table that draws the next PAGE_SIZE rows.
function ShowMore({ shown, total, onMore }) {
  if (total <= shown) return null
  return (
    <div className="show-more">
      <p>
        Showing the first {shown.toLocaleString()} of {total.toLocaleString()}
      </p>
      <button type="button" className="button" onClick={onMore}>
        Show {PAGE_SIZE} more
      </button>
    </div>
  )
}

export default ShowMore
