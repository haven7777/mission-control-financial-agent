import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.edgar import get_latest_filing_text
from app.services.filing_parser import extract_sections, chunk_text

def test_parser():
    html, form_type, _ = get_latest_filing_text("AAPL")
    sections = extract_sections(html)
    print("Sections found:", list(sections.keys()))
    for name, text in sections.items():
        print(f"  {name}: {len(text):,} chars")
        assert len(text) > 200, f"section {name!r} is too short ({len(text)} chars)"

    chunks = chunk_text(sections["risk_factors"])
    print(f"Risk factors → {len(chunks)} chunks")
    assert len(chunks) >= 2, "expected at least 2 chunks"
    for c in chunks:
        assert len(c) >= 100, f"chunk too short: {len(c)}"
        assert len(c) <= 1700, f"chunk too long: {len(c)}"
    print("✓ parser OK")

if __name__ == "__main__":
    test_parser()
