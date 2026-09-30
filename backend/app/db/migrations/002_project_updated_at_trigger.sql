-- Keep research project modification times accurate for every database client.

CREATE OR REPLACE FUNCTION set_research_project_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS research_projects_updated_at ON research_projects;

CREATE TRIGGER research_projects_updated_at
BEFORE UPDATE ON research_projects
FOR EACH ROW
EXECUTE FUNCTION set_research_project_updated_at();
