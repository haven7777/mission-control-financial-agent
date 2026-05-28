import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.filing_store import chunks_exist, store_chunks, search_chunks
from app.services.embeddings import embed_batch

_TICKER = "_TESTFIL"

def _cleanup():
    from app.services.supabase_client import get_supabase_client
    get_supabase_client().table("filing_chunks").delete().eq("ticker", _TICKER).execute()

def test_filing_store():
    _cleanup()

    assert not chunks_exist(_TICKER), "expected no cached chunks before test"
    print("✓ chunks_exist returns False for missing ticker")

    texts = [
        "Risk: Interest rate fluctuations may reduce demand for our products.",
        "MD&A: Revenue grew 15% driven by strong enterprise software sales.",
    ]
    embeddings = embed_batch(texts)
    store_chunks(
        ticker=_TICKER,
        form_type="10-K",
        filing_date="2024-11-01",
        section="risk_factors",
        chunks=[texts[0]],
        embeddings=[embeddings[0]],
    )
    store_chunks(
        ticker=_TICKER,
        form_type="10-K",
        filing_date="2024-11-01",
        section="mda",
        chunks=[texts[1]],
        embeddings=[embeddings[1]],
    )
    print("✓ store_chunks inserted 2 rows")

    assert chunks_exist(_TICKER), "expected chunks to exist after store"
    print("✓ chunks_exist returns True after store")

    query_emb = embed_batch(["business risks revenue growth"])[0]
    results = search_chunks(_TICKER, query_emb, top_k=5)
    assert len(results) == 2, f"expected 2 results, got {len(results)}"
    for r in results:
        assert "section" in r and "content" in r and "similarity" in r
        print(f"  section={r['section']} similarity={r['similarity']:.3f}")
    print("✓ search_chunks returned correct results")

    _cleanup()
    assert not chunks_exist(_TICKER), "cleanup failed"
    print("✓ cleanup OK")

if __name__ == "__main__":
    test_filing_store()
