-- V4.0 Phase 4A: Report Cache schema
--
-- Run this ONCE in the Supabase SQL Editor:
--   Project dashboard → SQL Editor → New query → paste → Run
--
-- Phase 4B will ADD a `summary_embedding vector(1536)` column for pgvector
-- semantic search. Existing rows are unaffected — no migration needed.

CREATE TABLE IF NOT EXISTS reports (
    id           uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker       text        NOT NULL,
    report_json  jsonb       NOT NULL,
    generated_at timestamptz NOT NULL,
    created_at   timestamptz DEFAULT now()
);

-- Fast lookup: all reports for a ticker ordered newest-first
CREATE INDEX IF NOT EXISTS idx_reports_ticker_generated
    ON reports (ticker, generated_at DESC);
