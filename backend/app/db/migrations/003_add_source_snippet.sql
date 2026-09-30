-- Preserve the search excerpt used to identify a source during discovery.

ALTER TABLE sources ADD COLUMN IF NOT EXISTS snippet TEXT;
