# backend/scripts/test_edgar_service.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.edgar import get_latest_filing_text, FilingNotFoundError

def test_edgar():
    result = get_latest_filing_text("AAPL")
    assert isinstance(result, tuple) and len(result) == 3
    text, form_type, filing_date = result
    print(f"form_type: {form_type}")
    print(f"filing_date: {filing_date}")
    print(f"text length: {len(text):,} chars")
    assert form_type in ("10-K", "10-Q"), f"unexpected form type: {form_type}"
    assert len(text) > 10_000, "filing text seems too short"
    assert filing_date is not None
    assert "item" in text.lower() or "annual report" in text.lower()
    print("✓ EDGAR fetch OK")

    try:
        get_latest_filing_text("ZZZZZZZZ")
        assert False, "should have raised FilingNotFoundError"
    except FilingNotFoundError as e:
        print(f"✓ unknown ticker raised FilingNotFoundError: {e}")

if __name__ == "__main__":
    test_edgar()
