"""The web layer: receives an upload, runs the pipeline, returns JSON."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.cleaning import clean_pages, looks_garbled
from app.extraction import UnreadableFileError, UnsupportedFormatError, extract_pages
from app.lemmas import AnalysisResult, analyze_text, load_model

MAX_UPLOAD_BYTES = 50 * 1024 * 1024

# Browsers only let these sites read our responses: the Vite dev server, by either name.
ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model at startup so the first user doesn't wait for it.
    load_model()
    yield


app = FastAPI(title="Polish Vocab Builder", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST"],
)


# A plain "def" (not "async def") makes FastAPI run this in a worker thread, so
# a slow book doesn't stop the server from answering other requests.
@app.post("/analyze", response_model=AnalysisResult)
def analyze(file: UploadFile = File(...), exclude_stopwords: bool = False):
    # Reading one byte past the limit tells us the file is too big without
    # loading all of a huge upload into memory.
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File is larger than the 50 MB limit.")

    try:
        pages = extract_pages(data, file.filename or "")
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except UnreadableFileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    text = clean_pages(pages)

    # Checked before spaCy, so a bad file fails in a second rather than after a minute.
    if looks_garbled(text):
        raise HTTPException(
            status_code=422,
            detail=(
                "This file's text can't be read reliably. Its hidden text layer may be "
                "damaged, or it may not be in Polish. If it's a PDF, try an EPUB edition."
            ),
        )

    result = analyze_text(text, load_model())

    if result.total_tokens == 0:
        raise HTTPException(
            status_code=422,
            detail="No text found. This may be a scanned book, which needs OCR.",
        )

    # Ranks and total_tokens still describe the whole book, so coverage figures
    # stay honest when stopwords are hidden.
    if exclude_stopwords:
        result.lemmas = [entry for entry in result.lemmas if not entry.is_stopword]
    return result
