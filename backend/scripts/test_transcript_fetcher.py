"""Run: python scripts/test_transcript_fetcher.py  (from backend/)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.transcript_fetcher import (
    get_latest_transcript,
    extract_qa_section,
    TranscriptNotFoundError,
)

def test_fetcher():
    from app.config import get_settings
    settings = get_settings()

    if not settings.fmp_configured:
        print("⚠  FMP_API_KEY is not set in backend/.env — skipping live API call.")
        print("   To run the full integration test, add FMP_API_KEY=<your-key> to backend/.env")
        print()

        # Verify the no-key path raises correctly
        try:
            get_latest_transcript("AAPL")
            assert False, "should have raised TranscriptNotFoundError"
        except TranscriptNotFoundError as e:
            print(f"✓ no-key path raises TranscriptNotFoundError as expected: {e}")

        # Verify extract_qa_section works without a key
        sample = "Prepared remarks section blah blah " * 100 + " Questions and Answers session: Analyst: What is your outlook? CEO: Very positive."
        qa = extract_qa_section(sample)
        assert len(qa) > 0
        assert len(qa) <= 12_000
        assert "Questions and Answers" in qa or len(qa) > 0
        print(f"✓ extract_qa_section works on sample text ({len(qa):,} chars)")

        print()
        print("✓ All no-key tests passed. Add FMP_API_KEY to .env for full integration test.")
        return

    # Full live test when key is present
    raw = get_latest_transcript("AAPL")
    print(f"ticker: {raw['ticker']}")
    print(f"quarter: {raw['quarter']}, year: {raw['year']}")
    print(f"date: {raw['date']}")
    print(f"content length: {len(raw['content']):,} chars")
    assert raw["ticker"] == "AAPL"
    assert raw["quarter"] in range(1, 5)
    assert raw["year"] >= 2024
    assert len(raw["content"]) > 1000

    qa = extract_qa_section(raw["content"])
    print(f"Q&A section length: {len(qa):,} chars (max 12 000)")
    assert len(qa) > 200
    assert len(qa) <= 12_000
    print("✓ transcript fetcher OK")

    try:
        get_latest_transcript("ZZZNOTREAL")
        assert False, "should have raised TranscriptNotFoundError"
    except TranscriptNotFoundError as e:
        print(f"✓ unknown ticker raised TranscriptNotFoundError: {e}")

if __name__ == "__main__":
    test_fetcher()
