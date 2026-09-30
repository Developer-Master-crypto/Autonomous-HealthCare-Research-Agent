-- ==============================================================================
-- ResearchOps Database Schema Migration: 001_initial_schema.sql
-- Target: Supabase / PostgreSQL (Postgres 15+)
-- Team: Spideyx | GATEWAYS 2026
-- ==============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. research_projects
CREATE TABLE IF NOT EXISTS research_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    region VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_projects_status ON research_projects(status);
CREATE INDEX IF NOT EXISTS idx_research_projects_created_at ON research_projects(created_at DESC);

-- 2. research_tasks
CREATE TABLE IF NOT EXISTS research_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
    task_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_tasks_project_id ON research_tasks(research_project_id);
CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);

-- 3. sources
CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    domain VARCHAR(255),
    source_type VARCHAR(100) NOT NULL DEFAULT 'other',
    publisher VARCHAR(255),
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reliability_score DOUBLE PRECISION CHECK (reliability_score IS NULL OR (reliability_score >= 0.0 AND reliability_score <= 1.0))
);

CREATE INDEX IF NOT EXISTS idx_sources_url ON sources(url);
CREATE INDEX IF NOT EXISTS idx_sources_domain ON sources(domain);

-- 4. facilities
CREATE TABLE IF NOT EXISTS facilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(100) DEFAULT 'acute_care_hospital',
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    phone VARCHAR(50),
    website TEXT,
    trauma_level VARCHAR(50),
    total_beds INT CHECK (total_beds IS NULL OR total_beds >= 0),
    icu_beds INT CHECK (icu_beds IS NULL OR icu_beds >= 0),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facilities_coords ON facilities(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_facilities_state ON facilities(state);

-- 5. services
CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100),
    description TEXT
);

CREATE INDEX IF NOT EXISTS idx_services_category ON services(category);

-- 6. facility_services
CREATE TABLE IF NOT EXISTS facility_services (
    facility_id UUID NOT NULL REFERENCES facilities(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    evidence_source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'operational',
    notes TEXT,
    PRIMARY KEY (facility_id, service_id)
);

CREATE INDEX IF NOT EXISTS idx_facility_services_service ON facility_services(service_id);

-- 7. research_claims
CREATE TABLE IF NOT EXISTS research_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'unverified',
    confidence DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_claims_project ON research_claims(research_project_id);

-- 8. claim_evidence
CREATE TABLE IF NOT EXISTS claim_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES research_claims(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    evidence_text TEXT NOT NULL,
    confidence DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim ON claim_evidence(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_evidence_source ON claim_evidence(source_id);

-- 9. conflicts
CREATE TABLE IF NOT EXISTS conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
    topic VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    source_ids JSONB DEFAULT '[]'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'unresolved',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conflicts_project ON conflicts(research_project_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);

-- 10. geographic_observations
CREATE TABLE IF NOT EXISTS geographic_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
    area VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    observation_type VARCHAR(100) NOT NULL,
    observation_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geo_obs_project ON geographic_observations(research_project_id);
CREATE INDEX IF NOT EXISTS idx_geo_obs_coords ON geographic_observations(latitude, longitude);

-- 11. service_gaps
CREATE TABLE IF NOT EXISTS service_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
    area VARCHAR(255) NOT NULL,
    service VARCHAR(255) NOT NULL,
    evidence TEXT,
    confidence DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)),
    severity VARCHAR(50) DEFAULT 'medium',
    nearest_facility_distance_km DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_service_gaps_project ON service_gaps(research_project_id);
CREATE INDEX IF NOT EXISTS idx_service_gaps_severity ON service_gaps(severity);

-- 12. research_reports
CREATE TABLE IF NOT EXISTS research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_project_id UUID NOT NULL REFERENCES research_projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_reports_project ON research_reports(research_project_id);
