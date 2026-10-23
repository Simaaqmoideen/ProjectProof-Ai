-- ProjectProof AI: PostgreSQL schema, version 2 (tested on PostgreSQL 16, see 02-database-schema.md section 6)
-- Run once on an empty database:  psql "$DATABASE_URL" -f schema.sql
-- In a real project, split this into Alembic migrations. See 02-database-schema.md for the meaning of each table.

CREATE EXTENSION IF NOT EXISTS citext;

-- ---------------------------------------------------------------- enums
CREATE TYPE user_role           AS ENUM ('student','company','recruiter','admin');
CREATE TYPE approval_status     AS ENUM ('pending','approved','rejected','suspended');
CREATE TYPE member_role         AS ENUM ('owner','reviewer');
CREATE TYPE difficulty_level    AS ENUM ('beginner','intermediate','advanced');
CREATE TYPE project_category    AS ENUM ('development','data','design','other');
CREATE TYPE project_status      AS ENUM ('draft','open','closed','cancelled','removed');
CREATE TYPE task_status         AS ENUM ('todo','in_progress','done');
CREATE TYPE application_status  AS ENUM ('applied','rejected','withdrawn','in_progress','submitted','changes_requested','completed','failed');
CREATE TYPE checkin_status      AS ENUM ('submitted','accepted','needs_work');
CREATE TYPE evaluation_decision AS ENUM ('approved','changes_requested','rejected');
CREATE TYPE appeal_status       AS ENUM ('open','upheld','overturned','withdrawn');
CREATE TYPE certificate_status  AS ENUM ('issued','revoked');
CREATE TYPE revocation_reason   AS ENUM ('fraud','plagiarism','evaluation_overturned','company_error','other');
CREATE TYPE flag_kind           AS ENUM ('similarity','anomaly','manual');
CREATE TYPE flag_status         AS ENUM ('open','dismissed','confirmed');
CREATE TYPE skill_source        AS ENUM ('self','resume','verified_project');
CREATE TYPE ai_confidence       AS ENUM ('low','medium','high');

-- ---------------------------------------------------------------- helpers
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION forbid_modify() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION '% is append-only: % is not allowed', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------- identity
CREATE TABLE users (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email            citext NOT NULL UNIQUE,
  password_hash    text NOT NULL,
  role             user_role NOT NULL,
  is_active        boolean NOT NULL DEFAULT true,
  email_verified_at timestamptz,
  last_login_at    timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_role ON users (role);

CREATE TABLE refresh_tokens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  text NOT NULL UNIQUE,
  expires_at  timestamptz NOT NULL,
  revoked_at  timestamptz,
  user_agent  text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id);

CREATE TABLE student_profiles (
  user_id        uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  full_name      text NOT NULL,
  headline       text,
  bio            text,
  college        text,
  graduation_year smallint CHECK (graduation_year BETWEEN 2000 AND 2100),
  github_username text,
  github_summary jsonb,
  github_analyzed_at timestamptz,
  resume_file_key text,
  resume_parsed  jsonb,
  is_public      boolean NOT NULL DEFAULT false,
  show_full_name_on_verification boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_student_profiles_public ON student_profiles (user_id) WHERE is_public;

CREATE TABLE companies (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name                text NOT NULL,
  website             text,
  email_domain        citext,
  description         text,
  registration_doc_key text,
  status              approval_status NOT NULL DEFAULT 'pending',
  trust_score         smallint NOT NULL DEFAULT 50 CHECK (trust_score BETWEEN 0 AND 100),
  reviewed_by         uuid REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at         timestamptz,
  rejection_reason    text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_companies_domain_active ON companies (email_domain)
  WHERE email_domain IS NOT NULL AND status <> 'rejected';
CREATE INDEX idx_companies_status ON companies (status);

CREATE TABLE company_members (
  company_id  uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  member_role member_role NOT NULL DEFAULT 'reviewer',
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (company_id, user_id)
);
CREATE UNIQUE INDEX uq_company_members_user ON company_members (user_id);

CREATE TABLE recruiter_profiles (
  user_id            uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  full_name          text NOT NULL,
  organization       text NOT NULL,
  work_email_domain  citext,
  status             approval_status NOT NULL DEFAULT 'pending',
  reviewed_by        uuid REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at        timestamptz,
  rejection_reason   text,
  created_at         timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- skills
CREATE TABLE skills (
  id        integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name      citext NOT NULL UNIQUE,
  category  text
);

CREATE TABLE student_skills (
  student_id  uuid NOT NULL REFERENCES student_profiles(user_id) ON DELETE CASCADE,
  skill_id    integer NOT NULL REFERENCES skills(id),
  proficiency smallint NOT NULL DEFAULT 1 CHECK (proficiency BETWEEN 1 AND 5),
  source      skill_source NOT NULL DEFAULT 'self',
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (student_id, skill_id)
);
CREATE INDEX idx_student_skills_skill ON student_skills (skill_id);

-- ---------------------------------------------------------------- projects
CREATE TABLE projects (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id           uuid NOT NULL REFERENCES companies(id),
  created_by           uuid NOT NULL REFERENCES users(id),
  title                text NOT NULL,
  description          text NOT NULL,
  category             project_category NOT NULL DEFAULT 'development',
  difficulty           difficulty_level NOT NULL,
  duration_days        integer NOT NULL CHECK (duration_days BETWEEN 1 AND 120),
  xp_max               integer NOT NULL CHECK (xp_max BETWEEN 0 AND 1000),
  max_selected         smallint NOT NULL DEFAULT 1 CHECK (max_selected >= 1),
  application_deadline timestamptz,
  status               project_status NOT NULL DEFAULT 'draft',
  ai_generated         boolean NOT NULL DEFAULT false,
  published_at         timestamptz,
  removed_by           uuid REFERENCES users(id) ON DELETE SET NULL,
  removed_at           timestamptz,
  removal_reason       text,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CHECK ((status = 'removed') = (removed_at IS NOT NULL)),
  CHECK (status <> 'removed' OR removal_reason IS NOT NULL)
);
CREATE INDEX idx_projects_company_status ON projects (company_id, status);
CREATE INDEX idx_projects_status_category ON projects (status, category);

CREATE TABLE project_skills (
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  skill_id   integer NOT NULL REFERENCES skills(id),
  PRIMARY KEY (project_id, skill_id)
);
CREATE INDEX idx_project_skills_skill ON project_skills (skill_id);

CREATE TABLE milestones (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id     uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  position       smallint NOT NULL CHECK (position > 0),
  title          text NOT NULL,
  description    text,
  due_day_offset integer NOT NULL CHECK (due_day_offset >= 1),
  UNIQUE (project_id, position)
);

-- Tasks inside milestones. application_id NULL = defined by the company for every student;
-- application_id set = a personal sub-task the student added for their own work.
CREATE TABLE tasks (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  milestone_id   uuid NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  application_id uuid,
  position       smallint NOT NULL CHECK (position > 0),
  title          text NOT NULL,
  description    text,
  created_by     uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_tasks_milestone ON tasks (milestone_id, application_id);

-- ---------------------------------------------------------------- applications and work
CREATE TABLE applications (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id       uuid NOT NULL REFERENCES projects(id),
  student_id       uuid NOT NULL REFERENCES student_profiles(user_id),
  status           application_status NOT NULL DEFAULT 'applied',
  cover_note       text,
  match_score      numeric(5,2) CHECK (match_score BETWEEN 0 AND 100),
  match_breakdown  jsonb,
  applied_at       timestamptz NOT NULL DEFAULT now(),
  decided_at       timestamptz,
  decided_by       uuid REFERENCES users(id) ON DELETE SET NULL,
  status_reason    text,
  started_at       timestamptz,
  due_at           timestamptz,
  completed_at     timestamptz,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  UNIQUE (project_id, student_id)
);
CREATE INDEX idx_applications_student ON applications (student_id, status);
CREATE INDEX idx_applications_project ON applications (project_id, status);

CREATE TABLE milestone_checkins (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  milestone_id   uuid NOT NULL REFERENCES milestones(id),
  note           text,
  evidence_url   text,
  status         checkin_status NOT NULL DEFAULT 'submitted',
  submitted_at   timestamptz NOT NULL DEFAULT now(),
  reviewed_by    uuid REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at    timestamptz,
  review_note    text
);
CREATE INDEX idx_checkins_application ON milestone_checkins (application_id, milestone_id);

-- A student's progress on each task (company tasks and personal sub-tasks).
CREATE TABLE task_progress (
  application_id uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  task_id        uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  status         task_status NOT NULL DEFAULT 'todo',
  completed_at   timestamptz,
  updated_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (application_id, task_id),
  CHECK ((status = 'done') = (completed_at IS NOT NULL))
);
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE;

CREATE TABLE submissions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id    uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  version           smallint NOT NULL DEFAULT 1,
  repo_url          text,
  file_key          text,
  notes             text,
  similarity_score  numeric(4,3) CHECK (similarity_score BETWEEN 0 AND 1),
  similarity_report jsonb,
  ai_prereview      jsonb,
  submitted_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (application_id, version),
  CHECK (repo_url IS NOT NULL OR file_key IS NOT NULL)
);

CREATE TABLE evaluations (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id  uuid NOT NULL UNIQUE REFERENCES submissions(id) ON DELETE CASCADE,
  reviewer_id    uuid NOT NULL REFERENCES users(id),
  rubric_scores  jsonb,
  overall_score  smallint NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
  feedback       text NOT NULL,
  public_summary text,
  used_ai_draft  boolean NOT NULL DEFAULT false,
  decision       evaluation_decision NOT NULL,
  evaluated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE appeals (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_id   uuid NOT NULL REFERENCES evaluations(id),
  student_id      uuid NOT NULL REFERENCES student_profiles(user_id),
  reason          text NOT NULL,
  status          appeal_status NOT NULL DEFAULT 'open',
  resolved_by     uuid REFERENCES users(id) ON DELETE SET NULL,
  resolution_note text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  resolved_at     timestamptz
);
CREATE UNIQUE INDEX uq_appeals_one_open ON appeals (evaluation_id) WHERE status = 'open';

-- ---------------------------------------------------------------- proof and rewards
CREATE TABLE certificates (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id    uuid NOT NULL UNIQUE REFERENCES applications(id),
  verification_id   text NOT NULL UNIQUE CHECK (verification_id ~ '^EXP-[0-9]{4}-[A-Z0-9]{4}-[0-9]{4}$'),
  qr_token          text NOT NULL UNIQUE,
  status            certificate_status NOT NULL DEFAULT 'issued',
  xp_awarded        integer NOT NULL CHECK (xp_awarded >= 0),
  content_hash      text NOT NULL,
  issued_at         timestamptz NOT NULL DEFAULT now(),
  revoked_at        timestamptz,
  revoked_by        uuid REFERENCES users(id) ON DELETE SET NULL,
  revocation_reason revocation_reason,
  revocation_note   text,
  CHECK ((status = 'revoked') = (revoked_at IS NOT NULL))
);
CREATE INDEX idx_certificates_status ON certificates (status);

CREATE TABLE levels (
  level   smallint PRIMARY KEY,
  name    text NOT NULL,
  min_xp  integer NOT NULL UNIQUE
);

CREATE TABLE xp_events (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id     uuid NOT NULL REFERENCES student_profiles(user_id),
  certificate_id uuid NOT NULL REFERENCES certificates(id),
  amount         integer NOT NULL CHECK (amount <> 0),
  reason         text NOT NULL DEFAULT 'project_completed',
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (certificate_id, reason)
);
CREATE INDEX idx_xp_events_student ON xp_events (student_id);

CREATE TABLE badges (
  id          smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code        text NOT NULL UNIQUE,
  name        text NOT NULL,
  description text NOT NULL,
  rule        jsonb NOT NULL
);

CREATE TABLE student_badges (
  student_id uuid NOT NULL REFERENCES student_profiles(user_id) ON DELETE CASCADE,
  badge_id   smallint NOT NULL REFERENCES badges(id),
  awarded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (student_id, badge_id)
);

-- ---------------------------------------------------------------- safety and operations
CREATE TABLE flags (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind         flag_kind NOT NULL,
  entity_type  text NOT NULL,
  entity_id    uuid NOT NULL,
  score        numeric(5,3),
  details      jsonb,
  status       flag_status NOT NULL DEFAULT 'open',
  reviewed_by  uuid REFERENCES users(id) ON DELETE SET NULL,
  reviewed_at  timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_flags_status ON flags (status, kind);

CREATE TABLE ai_logs (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id        uuid REFERENCES users(id) ON DELETE SET NULL,
  application_id uuid REFERENCES applications(id) ON DELETE SET NULL,
  feature        text NOT NULL,
  prompt_version text,
  model          text,
  input_ref      text,
  output         jsonb,
  confidence     ai_confidence,
  accepted       boolean,
  tokens_in      integer,
  tokens_out     integer,
  latency_ms     integer,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_ai_logs_user_time ON ai_logs (user_id, created_at DESC);
CREATE INDEX idx_ai_logs_feature ON ai_logs (feature, created_at DESC);
CREATE INDEX idx_ai_logs_application_feature ON ai_logs (application_id, feature, created_at DESC);

CREATE TABLE audit_log (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id    uuid REFERENCES users(id) ON DELETE SET NULL,
  action      text NOT NULL,
  entity_type text,
  entity_id   text,
  detail      jsonb,
  ip_hash     text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_entity ON audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_time ON audit_log (created_at DESC);

CREATE TABLE notifications (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type       text NOT NULL,
  title      text NOT NULL,
  body       text,
  link       text,
  read_at    timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user ON notifications (user_id, read_at);

CREATE TABLE consent_log (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       text NOT NULL,
  granted    boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE verification_lookups (
  id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  certificate_id uuid REFERENCES certificates(id) ON DELETE SET NULL,
  lookup_kind    text NOT NULL CHECK (lookup_kind IN ('qr','id')),
  found          boolean NOT NULL,
  ip_hash        text,
  created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_lookups_time ON verification_lookups (created_at DESC);

-- ---------------------------------------------------------------- triggers
CREATE TRIGGER trg_users_updated        BEFORE UPDATE ON users            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_students_updated     BEFORE UPDATE ON student_profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_companies_updated    BEFORE UPDATE ON companies        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_projects_updated     BEFORE UPDATE ON projects         FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_applications_updated BEFORE UPDATE ON applications     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_task_progress_updated BEFORE UPDATE ON task_progress   FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- A personal sub-task may only be tracked by the application that owns it.
CREATE OR REPLACE FUNCTION task_progress_owner_check() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM tasks t WHERE t.id = NEW.task_id
             AND t.application_id IS NOT NULL AND t.application_id <> NEW.application_id) THEN
    RAISE EXCEPTION 'this task belongs to another application';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_task_progress_owner BEFORE INSERT OR UPDATE ON task_progress FOR EACH ROW EXECUTE FUNCTION task_progress_owner_check();

-- Append-only tables
CREATE TRIGGER trg_audit_append_only BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION forbid_modify();
CREATE TRIGGER trg_xp_append_only    BEFORE UPDATE OR DELETE ON xp_events FOR EACH ROW EXECUTE FUNCTION forbid_modify();

-- Certificates: only revocation may change a row, and a revoked certificate stays revoked.
CREATE OR REPLACE FUNCTION certificates_guard() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'certificates cannot be deleted; revoke instead';
  END IF;
  IF NEW.application_id  IS DISTINCT FROM OLD.application_id
     OR NEW.verification_id IS DISTINCT FROM OLD.verification_id
     OR NEW.qr_token        IS DISTINCT FROM OLD.qr_token
     OR NEW.xp_awarded      IS DISTINCT FROM OLD.xp_awarded
     OR NEW.content_hash    IS DISTINCT FROM OLD.content_hash
     OR NEW.issued_at       IS DISTINCT FROM OLD.issued_at THEN
    RAISE EXCEPTION 'certificate fields are immutable; only revocation fields may change';
  END IF;
  IF OLD.status = 'revoked' AND NEW.status <> 'revoked' THEN
    RAISE EXCEPTION 'a revoked certificate cannot be reinstated; issue a new one through a new evaluation';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_certificates_guard BEFORE UPDATE OR DELETE ON certificates FOR EACH ROW EXECUTE FUNCTION certificates_guard();

-- A certificate can only be issued for a completed application.
CREATE OR REPLACE FUNCTION certificate_requires_completed() RETURNS trigger AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM applications a WHERE a.id = NEW.application_id AND a.status = 'completed') THEN
    RAISE EXCEPTION 'certificate can only be issued for a completed application';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_certificate_requires_completed BEFORE INSERT ON certificates FOR EACH ROW EXECUTE FUNCTION certificate_requires_completed();

-- ---------------------------------------------------------------- views
CREATE VIEW v_student_progress AS
SELECT sp.user_id AS student_id,
       COALESCE(x.total_xp, 0) AS total_xp,
       (SELECT l.level FROM levels l WHERE l.min_xp <= COALESCE(x.total_xp, 0) ORDER BY l.min_xp DESC LIMIT 1) AS level
FROM student_profiles sp
LEFT JOIN (SELECT student_id, SUM(amount)::int AS total_xp FROM xp_events GROUP BY student_id) x
       ON x.student_id = sp.user_id;

-- Everything the public verification page may show. The API reads this view live on every request.
CREATE VIEW v_public_verification AS
SELECT c.verification_id,
       c.qr_token,
       c.status,
       c.issued_at,
       c.revoked_at,
       c.revocation_reason,
       p.title            AS project_title,
       p.difficulty,
       p.duration_days,
       co.name            AS company_name,
       co.status          AS company_status,
       sp.full_name,
       sp.show_full_name_on_verification,
       a.applied_at, a.started_at, a.completed_at,
       e.public_summary,
       e.evaluated_at,
       ARRAY(SELECT s.name::text FROM project_skills ps JOIN skills s ON s.id = ps.skill_id
             WHERE ps.project_id = p.id ORDER BY s.name) AS skills
FROM certificates c
JOIN applications a        ON a.id = c.application_id
JOIN projects p            ON p.id = a.project_id
JOIN companies co          ON co.id = p.company_id
JOIN student_profiles sp   ON sp.user_id = a.student_id
JOIN submissions su        ON su.application_id = a.id
JOIN evaluations e         ON e.submission_id = su.id AND e.decision = 'approved';

-- A student's portfolio: every certificate they hold. The API adds the is_public check for recruiters
-- and shows only issued records by default; revoked ones are shown as Revoked, never hidden silently.
CREATE VIEW v_student_portfolio AS
SELECT sp.user_id AS student_id,
       sp.is_public,
       c.verification_id, c.qr_token, c.status, c.xp_awarded, c.issued_at, c.revoked_at,
       p.title AS project_title, p.category, p.difficulty, p.duration_days,
       co.name AS company_name,
       a.completed_at,
       e.public_summary,
       ARRAY(SELECT s.name::text FROM project_skills ps JOIN skills s ON s.id = ps.skill_id
             WHERE ps.project_id = p.id ORDER BY s.name) AS skills
FROM certificates c
JOIN applications a      ON a.id = c.application_id
JOIN projects p          ON p.id = a.project_id
JOIN companies co        ON co.id = p.company_id
JOIN student_profiles sp ON sp.user_id = a.student_id
JOIN submissions su      ON su.application_id = a.id
JOIN evaluations e       ON e.submission_id = su.id AND e.decision = 'approved';

-- Platform-wide counts for the admin dashboard (one row).
CREATE VIEW v_platform_stats AS
SELECT (SELECT count(*) FROM users WHERE role = 'student' AND is_active)                AS active_students,
       (SELECT count(*) FROM companies WHERE status = 'approved')                       AS approved_companies,
       (SELECT count(*) FROM recruiter_profiles WHERE status = 'approved')              AS approved_recruiters,
       (SELECT count(*) FROM projects WHERE status = 'open')                            AS open_projects,
       (SELECT count(*) FROM projects WHERE status = 'removed')                         AS removed_projects,
       (SELECT count(*) FROM applications WHERE status IN ('in_progress','submitted','changes_requested')) AS active_applications,
       (SELECT count(*) FROM applications WHERE status = 'completed')                   AS completed_applications,
       (SELECT count(*) FROM certificates WHERE status = 'issued')                      AS certificates_issued,
       (SELECT count(*) FROM certificates WHERE status = 'revoked')                     AS certificates_revoked,
       (SELECT count(*) FROM flags WHERE status = 'open')                               AS open_flags,
       (SELECT count(*) FROM appeals WHERE status = 'open')                             AS open_appeals,
       (SELECT count(*) FROM verification_lookups WHERE created_at > now() - interval '30 days') AS lookups_30d;

-- ---------------------------------------------------------------- reference data
INSERT INTO levels (level, name, min_xp) VALUES
  (1, 'Starter', 0), (2, 'Contributor', 200), (3, 'Builder', 400),
  (4, 'Practitioner', 600), (5, 'Specialist', 900), (6, 'Expert', 1300);

INSERT INTO badges (code, name, description, rule) VALUES
  ('first_project', 'First project', 'Complete your first verified project',
     '{"type":"verified_completions","min":1}'),
  ('fast_learner', 'Fast learner', 'Complete 3 verified projects',
     '{"type":"verified_completions","min":3}'),
  ('developer', 'Developer', 'Complete 5 verified development projects',
     '{"type":"verified_completions","category":"development","min":5}'),
  ('consistent_contributor', 'Consistent contributor', 'Complete verified projects from 3 different companies',
     '{"type":"distinct_companies","min":3}'),
  ('project_champion', 'Project champion', 'Complete 10 verified projects',
     '{"type":"verified_completions","min":10}');

INSERT INTO skills (name, category) VALUES
  ('Python','language'),('JavaScript','language'),('TypeScript','language'),('Java','language'),('C++','language'),
  ('HTML','web'),('CSS','web'),('React','web'),('Node.js','web'),('Flask','backend'),('Django','backend'),
  ('FastAPI','backend'),('Spring Boot','backend'),('REST API','backend'),
  ('SQL','data'),('MySQL','data'),('PostgreSQL','data'),('Pandas','data'),('Machine Learning','data'),
  ('Data Visualization','data'),('Power BI','data'),('Tableau','data'),
  ('Git','tools'),('Docker','tools'),('Flutter','mobile'),('React Native','mobile'),('UI Design','design')
ON CONFLICT (name) DO NOTHING;
