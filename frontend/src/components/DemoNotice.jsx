const REPO_URL = 'https://github.com/kylecooper3/polish-vocab-builder'

// Shown in place of the upload box, so nobody mistakes the demo for the full app.
function DemoNotice() {
  return (
    <section className="demo-notice">
      <strong>This is a demo with one book already analyzed</strong>
      <p>
        You're looking at real results for <em>Katarynka</em> by Bolesław Prus, a public-domain
        story. You can't upload your own book here, because that needs the Python backend, which
        only runs when you set up the app yourself. <a href={REPO_URL}>See the code and setup on GitHub</a>
      </p>
    </section>
  )
}

export default DemoNotice
