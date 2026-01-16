CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_gyms_subdominio_lower ON gyms (lower(subdominio));
CREATE INDEX IF NOT EXISTS idx_gyms_status ON gyms (status);
