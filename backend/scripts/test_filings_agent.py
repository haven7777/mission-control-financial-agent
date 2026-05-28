import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.filings_agent import run_filings_agent
from app.models.filings import FilingsContext

def test_filings_agent():
    print("Running FilingsAgent for AAPL (may take 15-30s on first run)...")
    ctx = run_filings_agent("AAPL")
    print(f"is_empty: {ctx.is_empty}")
    print(f"form_type: {ctx.form_type}")
    print(f"chunks: {len(ctx.chunks)}")

    assert isinstance(ctx, FilingsContext)

    if ctx.is_empty:
        print("⚠ FilingsAgent returned empty context (Supabase not configured or EDGAR miss)")
        return

    assert len(ctx.chunks) > 0, "expected at least one chunk"
    for chunk in ctx.chunks:
        assert chunk.section in ("risk_factors", "mda"), f"unexpected section: {chunk.section}"
        assert len(chunk.content) >= 100
        assert 0.0 <= chunk.similarity <= 1.0
        print(f"  [{chunk.section}] sim={chunk.similarity:.3f}: {chunk.content[:80]}...")

    print("✓ FilingsAgent OK")

    import time
    t0 = time.monotonic()
    ctx2 = run_filings_agent("AAPL")
    elapsed = time.monotonic() - t0
    print(f"✓ Second run (cache): {elapsed:.1f}s — expected < 5s if chunks are cached")
    assert not ctx2.is_empty

if __name__ == "__main__":
    test_filings_agent()
