-- Enable pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- Store embedded text chunks from SEC filings.
-- Embeddings use OpenAI text-embedding-3-small (1536 dims, unit-normalized).
CREATE TABLE IF NOT EXISTS filing_chunks (
    id           uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker       text        NOT NULL,
    form_type    text        NOT NULL,      -- '10-K' or '10-Q'
    section      text        NOT NULL,      -- 'risk_factors' or 'mda'
    chunk_index  int         NOT NULL,
    content      text        NOT NULL,
    embedding    vector(1536),
    filing_date  text,                      -- ISO date string e.g. '2024-11-01', nullable
    fetched_at   timestamptz DEFAULT now(),
    CONSTRAINT uq_filing_chunk UNIQUE (ticker, form_type, chunk_index)
);

-- B-tree index for fast ticker + form_type lookups (existence check, delete, select)
CREATE INDEX IF NOT EXISTS idx_filing_chunks_ticker
    ON filing_chunks (ticker, form_type);

-- Semantic search function called from Python via .rpc().
-- Uses sequential scan within ticker — correct for small per-ticker chunk counts
-- (typically 10-20 chunks per ticker with our 15K char section cap + 1.5K chunk size).
CREATE OR REPLACE FUNCTION match_filing_chunks(
    p_ticker    text,
    p_embedding vector(1536),
    p_top_k     int DEFAULT 5
)
RETURNS TABLE(section text, content text, form_type text, filing_date text, similarity float)
LANGUAGE sql STABLE
AS $$
    SELECT
        section,
        content,
        form_type,
        filing_date,
        1 - (embedding <=> p_embedding) AS similarity
    FROM filing_chunks
    WHERE ticker = p_ticker
      AND embedding IS NOT NULL
    ORDER BY embedding <=> p_embedding
    LIMIT GREATEST(p_top_k, 1);
$$;
