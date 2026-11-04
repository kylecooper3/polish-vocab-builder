import { useEffect, useState } from 'react'

function UploadZone({ onFile, disabled, compact }) {
  const [isDragging, setIsDragging] = useState(false)

  // useEffect is for connecting to things outside React, here the browser window.
  // Normally a file dropped on a page makes the browser open it, which would navigate
  // away from our app if someone narrowly missed the box. So we switch that off.
  useEffect(() => {
    function blockDefault(event) {
      event.preventDefault()
    }
    window.addEventListener('dragover', blockDefault)
    window.addEventListener('drop', blockDefault)

    // The function we return is the "cleanup". React runs it when this component goes
    // away, so listeners don't pile up.
    return () => {
      window.removeEventListener('dragover', blockDefault)
      window.removeEventListener('drop', blockDefault)
    }
    // The empty [] means "run this once, when the component first appears".
  }, [])

  function handleDrop(event) {
    setIsDragging(false)
    const file = event.dataTransfer.files[0]
    if (file && !disabled) onFile(file)
  }

  function handleChoose(event) {
    const file = event.target.files[0]
    if (file) onFile(file)
    // Clearing the input lets you choose the same file again later.
    event.target.value = ''
  }

  // Building the class name from state is how the box changes appearance while dragging.
  const className = `drop-zone${isDragging ? ' drop-zone-active' : ''}${disabled ? ' drop-zone-disabled' : ''}${compact ? ' drop-zone-compact' : ''}`

  return (
    // A <label> makes the whole box act like the file button, for mouse and keyboard.
    <label
      className={className}
      onDragOver={() => setIsDragging(true)}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <input
        className="visually-hidden"
        type="file"
        accept=".pdf,.epub"
        disabled={disabled}
        onChange={handleChoose}
      />
      <strong>Drop a Polish book here</strong>
      <span>or click to choose a PDF or EPUB (50 MB max)</span>
    </label>
  )
}

export default UploadZone
