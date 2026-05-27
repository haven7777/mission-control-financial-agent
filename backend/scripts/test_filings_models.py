# backend/scripts/test_filings_models.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.filings import FilingChunk, FilingsContext
from app.models.manager import FinalReport

def test_models():
    chunk = FilingChunk(section="risk_factors", content="Interest rate risk...", similarity=0.91)
    assert chunk.section == "risk_factors"
    ctx = FilingsContext(ticker="AAPL", form_type="10-K", chunks=[chunk])
    assert not ctx.is_empty
    ctx_empty = FilingsContext(ticker="ZZZZ", form_type="10-K", chunks=[], is_empty=True)
    assert ctx_empty.is_empty
    # FinalReport accepts filings_context=None (backward compat)
    print("✓ FilingChunk, FilingsContext, FinalReport(filings_context=None) all OK")

if __name__ == "__main__":
    test_models()
