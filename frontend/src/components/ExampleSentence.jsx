import { splitAroundForms } from '../lemmaUtils.js'

// Shows a sentence with the word being studied in bold. React treats the text as plain
// text, so anything odd in a book's sentence can't turn into HTML on the page.
function ExampleSentence({ sentence, forms }) {
  return splitAroundForms(sentence, forms).map((piece, index) =>
    piece.isMatch ? <strong key={index}>{piece.text}</strong> : piece.text,
  )
}

export default ExampleSentence
