// The one place that knows how to talk to the backend.
const API_URL = 'http://127.0.0.1:8000'

// "async" means this function can pause at each "await" while waiting on the
// network, without freezing the page. It works like async/await in Python.
export async function analyzeBook(file) {
  // FormData packages a file the same way a browser form upload does. We don't set a
  // Content-Type header: the browser adds the right one, including a required boundary.
  const formData = new FormData()
  formData.append('file', file)

  let response
  try {
    response = await fetch(`${API_URL}/analyze`, { method: 'POST', body: formData })
  } catch {
    // fetch only throws when no response came back at all, such as a stopped server.
    throw new Error('Could not reach the server. Is the backend running?')
  }

  // fetch does NOT throw on error statuses like 415 or 422, so we have to check.
  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  return response.json()
}

async function readErrorMessage(response) {
  try {
    const body = await response.json()
    // Our API explains its errors in a "detail" field.
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // The error wasn't JSON, so fall through to the general message.
  }
  return `Something went wrong on the server (error ${response.status}).`
}
