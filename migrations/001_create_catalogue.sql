-- Migration: Create catalogue table in schema "dataiesb-aurya"
-- Run against the Postgres instance that Trino connects to.

CREATE SCHEMA IF NOT EXISTS "dataiesb-aurya";

CREATE TABLE IF NOT EXISTS "dataiesb-aurya".catalogue (
    pk   TEXT NOT NULL,
    sk   TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (pk, sk)
);

-- Index for SK prefix queries (begins_with equivalent)
CREATE INDEX IF NOT EXISTS idx_catalogue_sk ON "dataiesb-aurya".catalogue (pk, sk text_pattern_ops);
