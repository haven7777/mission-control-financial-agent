-- Enable pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- Store embedded text chunks from SEC filings
CREATE TABLE IF NOT EXISTS filing_chunks (
    id           uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker       text        NOT NULL,
    form_type    text        NOT NULL,
    section      text        NOT NULL,
    chunk_index  int         NOT NULL,
    content      text        NOT NULL,
    embedding    vector(1536),
    filing_date  text,
    fetched_at   timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_filing_chunks_ticker
    ON filing_chunks (ticker, form_type, fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_filing_chunks_embedding
    ON filing_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE OR REPLACE FUNCTION match_filing_chunks(
    p_ticker    text,
    p_embedding vector(1536),
    p_top_k     int DEFAULT 5
)
RETURNS TABLE(section text, content text, similarity float)
LANGUAGE sql STABLE
AS $$
    SELECT
        section,
        content,
        1 - (embedding <=> p_embedding) AS similarity
    FROM filing_chunks
    WHERE ticker = p_ticker
      AND embedding IS NOT NULL
    ORDER BY embedding <=> p_embedding
    LIMIT p_top_k;
$$;
