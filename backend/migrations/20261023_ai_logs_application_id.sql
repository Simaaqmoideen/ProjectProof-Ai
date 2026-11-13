-- FR-WRK-5: scope mentor usage records to their application.
ALTER TABLE ai_logs
    ADD COLUMN application_id uuid REFERENCES applications(id) ON DELETE SET NULL;

UPDATE ai_logs
   SET application_id = COALESCE(
       NULLIF(output->>'application_id', '')::uuid,
       NULLIF(output->>'_application_id', '')::uuid
   )
 WHERE feature = 'mentor'
   AND COALESCE(output->>'application_id', output->>'_application_id') IS NOT NULL;

CREATE INDEX idx_ai_logs_application_feature
    ON ai_logs (application_id, feature, created_at DESC);
