import { useState } from 'react'
import { analyzeBook } from './api.js'
import Results from './components/Results.jsx'
import UploadZone from './components/UploadZone.jsx'

// A COMPONENT is a function that returns what should appear on screen. React calls it
// whenever its data changes, then updates only the parts of the page that differ.
function App() {
  // STATE is data that can change while the app runs. useState gives us the current
  // value and a function to update it. An ordinary variable wouldn't work here: calling
  // the setter is what tells React to run this function again and redraw the page.
  const [book, setBook] = useState(null) // { result, filename, id } once one is analyzed
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // Runs in response to a user action, so it doesn't need useEffect. The real work
  // happens inside analyzeBook, and the page stays usable while we await it.
  async function handleFile(file) {
    setIsLoading(true)
    setError('')
    try {
      const result = await analyzeBook(file)
      setBook({ result, filename: file.name, id: Date.now() })
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
      <header>
        <h1>Polish Vocab Builder</h1>
        <p className="subtitle">
          Study the words that matter most, counted by dictionary form.
        </p>
      </header>

      <UploadZone onFile={handleFile} disabled={isLoading} />

      {/* "a && b" shows b only when a is true, so these appear only when relevant. */}
      {isLoading && (
        <p className="status" role="status">
          <span className="spinner" aria-hidden="true" />
          Analyzing your book. A long novel can take a minute or more.
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
