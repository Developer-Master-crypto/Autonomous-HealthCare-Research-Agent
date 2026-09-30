-- Scope retrieved sources and facilities to a research project and persist the
-- full normalized workflow in a single PostgREST RPC transaction.

ALTER TABLE sources
    DROP CONSTRAINT IF EXISTS sources_url_key,
    ADD COLUMN IF NOT EXISTS research_project_id UUID REFERENCES research_projects(id) ON DELETE CASCADE;
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_project_url
    ON sources(research_project_id, url) WHERE research_project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sources_project_id ON sources(research_project_id);

ALTER TABLE facilities
    ADD COLUMN IF NOT EXISTS research_project_id UUID REFERENCES research_projects(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_facilities_project_id ON facilities(research_project_id);

ALTER TABLE conflicts
    ADD COLUMN IF NOT EXISTS claim_a_id UUID REFERENCES research_claims(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS claim_b_id UUID REFERENCES research_claims(id) ON DELETE SET NULL;

ALTER TABLE service_gaps
    ADD COLUMN IF NOT EXISTS status VARCHAR(50),
    ADD COLUMN IF NOT EXISTS summary TEXT,
    ADD COLUMN IF NOT EXISTS limitations JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE services
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE facility_services
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE OR REPLACE FUNCTION persist_research_bundle(p_records JSONB)
RETURNS VOID
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    item JSONB;
    table_name TEXT;
    record_data JSONB;
    resolved_service_id UUID;
BEGIN
    IF jsonb_typeof(p_records) <> 'array' THEN
        RAISE EXCEPTION 'Research bundle must be an array';
    END IF;

    FOR item IN SELECT value FROM jsonb_array_elements(p_records)
    LOOP
        table_name := item->>'table';
        IF table_name IS NULL OR table_name NOT IN (
            'research_tasks', 'facilities', 'services', 'facility_services',
            'research_claims', 'claim_evidence', 'conflicts',
            'geographic_observations', 'service_gaps', 'research_reports'
        ) THEN
            RAISE EXCEPTION 'Unsupported research bundle table';
        END IF;
        record_data := item->'data';
        IF table_name = 'services' THEN
            EXECUTE format(
                'INSERT INTO %I.%I SELECT (jsonb_populate_record(NULL::%I.%I, $1)).* ON CONFLICT (name) DO NOTHING',
                current_schema(), table_name, current_schema(), table_name
            ) USING record_data;
        ELSIF table_name = 'facility_services' THEN
            EXECUTE format('SELECT id FROM %I.services WHERE lower(name) = lower($1)', current_schema())
                INTO resolved_service_id USING record_data->>'service_name';
            IF resolved_service_id IS NULL THEN
                RAISE EXCEPTION 'Research bundle references an unstored service';
            END IF;
            record_data := (record_data - 'service_name') || jsonb_build_object('service_id', resolved_service_id);
            EXECUTE format(
                'INSERT INTO %I.%I SELECT (jsonb_populate_record(NULL::%I.%I, $1)).* ON CONFLICT DO NOTHING',
                current_schema(), table_name, current_schema(), table_name
            ) USING record_data;
        ELSE
            EXECUTE format(
                'INSERT INTO %I.%I SELECT (jsonb_populate_record(NULL::%I.%I, $1)).* ON CONFLICT DO NOTHING',
                current_schema(), table_name, current_schema(), table_name
            ) USING record_data;
        END IF;
    END LOOP;
END;
$$;

REVOKE ALL ON FUNCTION persist_research_bundle(JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION persist_research_bundle(JSONB) TO service_role;
