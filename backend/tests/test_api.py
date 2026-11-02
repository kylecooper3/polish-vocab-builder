"""End-to-end tests: send real uploads through the whole pipeline."""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.main import app

BOOK_HTML = "<p>Mam psa. Masz kota. On ma dom. Mój pies bardzo lubi długie spacery po lesie.</p>"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _upload(client, filename, data, **params):
    return client.post("/analyze", files={"file": (filename, data)}, params=params)


def test_pdf_upload_returns_lemma_list(client, make_pdf):
    response = _upload(client, "book.pdf", make_pdf([BOOK_HTML]))
    assert response.status_code == 200
    body = response.json()
    assert body["total_tokens"] > 0

    entry = next(item for item in body["lemmas"] if item["lemma"] == "mieć")
    assert entry["count"] == 3
    assert set(entry) == {
        "lemma", "count", "rank", "pos", "translation", "forms", "example", "is_stopword",
    }


def test_epub_upload_returns_lemma_list(client, make_epub):
    html = f"<html><body>{BOOK_HTML}</body></html>"
    response = _upload(client, "book.epub", make_epub([html]))
    assert response.status_code == 200
    assert any(item["lemma"] == "pies" for item in response.json()["lemmas"])


def test_exclude_stopwords_keeps_ranks_and_totals(client, make_pdf):
    data = make_pdf([BOOK_HTML])
    full = _upload(client, "book.pdf", data).json()
    filtered = _upload(client, "book.pdf", data, exclude_stopwords=True).json()

    assert all(not item["is_stopword"] for item in filtered["lemmas"])
    assert len(filtered["lemmas"]) < len(full["lemmas"])
    assert filtered["total_tokens"] == full["total_tokens"]

    ranks = {item["lemma"]: item["rank"] for item in full["lemmas"]}
    assert all(item["rank"] == ranks[item["lemma"]] for item in filtered["lemmas"])


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_cors_allows_the_frontend(client, origin):
    response = client.post(
        "/analyze", files={"file": ("notes.txt", b"hello")}, headers={"Origin": origin}
    )
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_does_not_allow_other_sites(client):
    response = client.post(
        "/analyze",
        files={"file": ("notes.txt", b"hello")},
        headers={"Origin": "https://example.com"},
    )
    assert "access-control-allow-origin" not in response.headers


def test_unsupported_type_returns_415(client):
    assert _upload(client, "notes.txt", b"hello").status_code == 415


def test_corrupt_file_returns_400(client):
    assert _upload(client, "fake.pdf", b"not a pdf").status_code == 400


def test_pdf_with_no_text_returns_422(client, make_pdf):
    # A page with no text layer is what a scanned book looks like to us.
    response = _upload(client, "scan.pdf", make_pdf(["<p></p>"]))
    assert response.status_code == 422
    assert "scanned" in response.json()["detail"]


def test_garbled_text_returns_422_with_advice(client, make_epub):
    html = "<html><body><p>Sprawiedliwym గest to, że గa గuż wiem, గak గest.</p></body></html>"
    response = _upload(client, "book.epub", make_epub([html]))
    assert response.status_code == 422
    assert "EPUB" in response.json()["detail"]


def test_oversized_file_returns_413(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 10)
    assert _upload(client, "big.pdf", b"x" * 11).status_code == 413
