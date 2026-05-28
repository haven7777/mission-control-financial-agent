-- Phase 6: Master Code access control
-- Run once in the Supabase SQL Editor.

CREATE TABLE IF NOT EXISTS master_codes (
    id         uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    code       text        NOT NULL UNIQUE,
    is_active  boolean     NOT NULL DEFAULT true,
    created_at timestamptz DEFAULT now()
);

-- Fast lookup by code value
CREATE INDEX IF NOT EXISTS idx_master_codes_code ON master_codes (code);

-- Seed one beta code — change this before any public distribution!
INSERT INTO master_codes (code, is_active)
VALUES ('DEEP-RESEARCH-BETA-2026', true)
ON CONFLICT (code) DO NOTHING;
