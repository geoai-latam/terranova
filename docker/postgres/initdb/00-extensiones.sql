-- Terranova: extensiones de la base (se crean al iniciar una base vacía).
-- postgis para el dataset curado (F4.1); vector (pgvector) para el descubrimiento (G6/ADR-0028).
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
