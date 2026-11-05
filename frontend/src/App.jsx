import { useEffect, useState } from 'react'
import { analyzeBook, loadDemoResult } from './api.js'
import DemoNotice from './components/DemoNotice.jsx'
import Results from './components/Results.jsx'
import UploadZone from './components/UploadZone.jsx'
import { formatDuration } from './lemmaUtils.js'

// True only in the build published to GitHub Pages, which has no backend to talk to.
const IS_DEMO = import.meta.env.VITE_DEMO_MODE === 'true'

// A COMPONENT is a function that returns what should appear on screen. React calls it
// whenever its data changes, then updates only the parts of the page that differ.
function App() {
  // STATE is data that can change while the app runs. useState gives us the current
  // value and a function to update it. An ordinary variable wouldn't work here: calling
  // the setter is what tells React to run this function again and redraw the page.
  const [book, setBook] = useState(null) // { result, filename, id } once one is analyzed
  const [isLoading, setIsLoading] = useState(IS_DEMO)
  const [error, setError] = useState('')

  // The demo loads its saved results when the page opens, rather than after a user
  // action, which is the kind of job useEffect is for.
  useEffect(() => {
    if (!IS_DEMO) return
    loadDemoResult()
      .then((result) => setBook({ result, filename: 'katarynka.epub', id: 'demo' }))
      .catch((loadError) => setError(loadError.message))
      .finally(() => setIsLoading(false))
  }, [])

  // Runs in response to a user action, so it doesn't need useEffect. The real work
  // happens inside analyzeBook, and the page stays usable while we await it.
  async function handleFile(file) {
    setIsLoading(true)
    setError('')
    const startedAt = performance.now()
    try {
      const result = await analyzeBook(file)
      setBook({
        result,
        filename: file.name,
        id: Date.now(),
        analysisTime: performance.now() - startedAt,
      })
    } catch (uploadError) {
      setError(uploadError.message)
    } finally {
      // "finally" runs on success and failure, so the spinner can never get stuck.
      setIsLoading(false)
    }
  }

  // JSX looks like HTML but is really JavaScript, which is why it uses "className"
  // ("class" is a reserved word) and can include values in {curly braces}.
  return (
    <main className="page">
      <header className="top-bar">
        <h1>Polish Vocab Builder</h1>
        <p className="subtitle">
          Study the words that matter most, counted by dictionary form.
        </p>
        {/* The live demo loads saved results, so it has no analysis time to show. */}
        {book?.analysisTime !== undefined && (
          <p className="analysis-time">Analyzed in {formatDuration(book.analysisTime)}</p>
        )}
      </header>

      {IS_DEMO ? (
        <DemoNotice />
      ) : (
        <UploadZone onFile={handleFile} disabled={isLoading} compact={book !== null} />
      )}

      {/* "a && b" shows b only when a is true, so these appear only when relevant. */}
      {isLoading && (
        <p className="status" role="status">
          <span className="spinner" aria-hidden="true" />
          {IS_DEMO ? 'Loading the demo.' : 'Analyzing your book. A long novel can take a minute or more.'}
        </p>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {/* A new key tells React this is a different Results, so it starts over with
          fresh state. A filter from the last book can't carry over by accident. */}
      {book && <Results key={book.id} result={book.result} filename={book.filename} />}
    </main>
  )
}

export default App
