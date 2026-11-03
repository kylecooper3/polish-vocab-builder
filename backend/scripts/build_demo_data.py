"""Save the sample book's results for the static demo, so it needs no server.

From the backend folder, run:

    python -m scripts.build_demo_data
"""

from pathlib import Path

from app.cleaning import clean_pages
from app.extraction import extract_pages
from app.lemmas import AnalysisResult, analyze_text, load_model

ROOT = Path(__file__).parents[2]
SAMPLE_BOOK = ROOT / "sample" / "katarynka.epub"
OUTPUT_FILE = ROOT / "frontend" / "public" / "demo" / "katarynka.json"


def analyze_sample() -> AnalysisResult:
    pages = extract_pages(SAMPLE_BOOK.read_bytes(), SAMPLE_BOOK.name)
    return analyze_text(clean_pages(pages), load_model())


def main() -> None:
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    OUTPUT_FILE.write_text(analyze_sample().model_dump_json() + "\n", encoding="utf-8", newline="\n")
    print(f"{OUTPUT_FILE.stat().st_size / 1000:.0f} KB")


if __name__ == "__main__":
    main()
