-- Store source-content extraction outcomes without treating inaccessible pages as analyzed.

ALTER TABLE sources ADD COLUMN IF NOT EXISTS extracted_text TEXT;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(50) NOT NULL DEFAULT 'pending';
ALTER TABLE sources ADD COLUMN IF NOT EXISTS extraction_error TEXT;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ;
