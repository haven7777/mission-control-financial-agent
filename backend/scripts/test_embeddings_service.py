import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.embeddings import embed_batch

def test_embeddings():
    texts = [
        "Interest rate risk may adversely affect our revenue.",
        "Revenue increased 12% year-over-year driven by iPhone sales.",
    ]
    embeddings = embed_batch(texts)
    assert len(embeddings) == 2, f"expected 2 embeddings, got {len(embeddings)}"
    for emb in embeddings:
        assert len(emb) == 1536, f"expected 1536 dims, got {len(emb)}"
        assert all(isinstance(x, float) for x in emb)
    print(f"✓ embed_batch returned {len(embeddings)} embeddings of dim {len(embeddings[0])}")

if __name__ == "__main__":
    test_embeddings()
