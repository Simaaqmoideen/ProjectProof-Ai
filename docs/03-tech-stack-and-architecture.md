# ProjectProof AI: Tech Stack and Architecture

This is a recommended stack chosen for a small team and one semester. Every choice has a reason and an alternative, so you can swap anything you are more comfortable with. Pin exact versions in lockfiles when you start; this document deliberately does not.

## 1. Stack summary

| Layer | Choice | Why | Acceptable alternative |
|---|---|---|---|
| Frontend | React + TypeScript + Vite | Fast to build, large ecosystem, types catch mistakes | Next.js |
| Styling | Tailwind CSS | Design tokens map directly to a Tailwind theme when `DESIGN.md` is chosen | CSS modules |
| Frontend data | TanStack Query, React Router, React Hook Form + Zod | Caching, routing, validated forms | Redux Toolkit |
| Backend | Python 3.12 + FastAPI | Automatic API docs, easy to call AI libraries and PDF tools | Node + Express or NestJS |
| ORM and migrations | SQLAlchemy 2 + Alembic | Versioned schema changes | Prisma (if using Node) |
| Validation | Pydantic v2 | Same models validate API input and AI JSON output | Zod (if using Node) |
| Database | PostgreSQL 14+ | Constraints, triggers, JSONB, partial indexes (the schema relies on them) | MySQL needs the triggers and partial indexes rewritten |
| Auth | Argon2id password hashing, short-lived JWT access token, refresh token in an HttpOnly cookie | Standard, no third-party dependency | Managed auth (Auth0, Clerk, Supabase Auth) |
| File storage | Local disk in development, S3-compatible object storage in production | Keeps files out of the database | Supabase Storage, Cloudflare R2, MinIO |
| QR codes | `qrcode` library | Generates PNG/SVG server-side | `segno` |
| PDF | WeasyPrint (HTML to PDF) | Certificate is designed as HTML, so it can reuse the web styling | ReportLab |
| Resume text | `pypdf` (text PDFs); optional OCR for scanned files | Needed before AI analysis | `pdfminer.six` |
| LLM | One provider behind your own `LLMClient` interface | Lets you log, cap cost, validate and swap | Any hosted model API or a local model |
| Code similarity | In-house winnowing fingerprints (see 06) | Runs offline, explainable, no external service | A hosted similarity service |
| Email | SMTP or a transactional email API | Verification, reset, notifications | Console output in development |
| Background work | FastAPI background tasks to start; a small worker (RQ or Celery) if jobs get slow | Similarity checks and AI calls must not block requests | None needed for a small demo |
| Rate limiting | `slowapi` in memory for one instance; Redis if you run several | Protects login and the public page | Reverse proxy limits |
| Testing | pytest, Vitest, Playwright | Backend, frontend, end-to-end | Cypress |
| Quality | Ruff, mypy (optional), ESLint, Prettier, pre-commit | Consistent code | Flake8 |
| Containers | Docker and Docker Compose | One command to run everything | Plain local install |
| CI | GitHub Actions: lint, tests, build on each pull request | Catches breakage early | GitLab CI |

## 2. Architecture

```mermaid
flowchart LR
  subgraph Browser
    SPA[React app]
    PUB[Public verification page]
  end
  SPA -->|HTTPS JSON| API
  PUB -->|HTTPS JSON| API
  subgraph Server
    API[FastAPI application]
    JOBS[Background worker]
    API --> SVC[Service layer]
    SVC --> REPO[Repository layer]
    SVC --> AIS[AI service layer]
    SVC --> FILES[File service]
    SVC --> MAIL[Email service]
    JOBS --> SVC
  end
  REPO --> DB[(PostgreSQL)]
  FILES --> OBJ[(Object storage)]
  AIS --> LLM[LLM provider]
  AIS --> SIM[Similarity engine]
  MAIL --> SMTP[Email provider]
```

**Three principles drive the design**
1. **The server owns every business rule.** The browser asks; the server decides. XP, status changes, certificate issue and visibility are never trusted from the client.
2. **The database is the last line of defence.** The schema blocks illegal certificate edits, duplicate applications and tampering with the audit log even if application code has a bug.
3. **AI is behind one door.** All AI calls go through the AI service layer, which validates output, logs it, caps cost and never writes results to business tables without a person accepting them.

## 3. Backend layout

```
backend/
  app/
    main.py                 # app factory, middleware, router registration
    config.py               # settings loaded from environment
    db.py                   # engine and session
    deps.py                 # auth, role checks, current user
    models/                 # SQLAlchemy models, one file per area
    schemas/                # Pydantic request and response models
    api/                    # routers: auth, students, companies, projects,
                            #   applications, workspace, submissions, evaluations,
                            #   certificates, public, recruiter, admin, ai, notifications,
                            #   tasks, portfolio, github
    services/               # business logic: applications, evaluation, certificate,
                            #   xp, badges, trust_score, notifications, audit,
                            #   recommendations, tasks, project_removal, portfolio, platform_stats,
                            #   github (public API client, read-only)
    repositories/           # database queries (no business rules)
    ai/
      client.py             # LLMClient interface and provider adapter
      prompts/              # versioned prompt files
      schemas.py            # Pydantic models for each AI output
      matching.py           # deterministic match score, missing skills, recommendation score (BR-10)
      similarity.py         # winnowing fingerprints
      features/             # resume, brief, prereview, ranking, skill_gap, github_analysis, mentor, ...
    core/
      security.py           # hashing, tokens
      ids.py                # verification ID and QR token generation
      rate_limit.py
      logging.py
  migrations/               # Alembic
  tests/
```

**GitHub client (v2).** `services/github.py` calls GitHub's public REST API with a timeout, reads only public data (user, public repositories, languages), caches the result for 24 hours, and never stores a token. If GitHub is slow, rate limited or the username does not exist, the profile page shows a clear message and everything else works. Nothing outside `services/github.py` calls GitHub.

**Project removal (v2).** `services/project_removal.py` is the only place that sets a project to `removed`, so the rejection of applicants, withdrawal of work, trust score change, audit row and notifications happen together in one transaction.

**Layer rules:** routers handle HTTP only; services hold business rules; repositories hold queries; nothing outside `ai/` calls the LLM provider; nothing outside `services/certificate.py` creates certificates.

## 4. Frontend layout

```
frontend/
  src/
    app/                    # routes, providers, layout shells per role
    features/               # auth, student, company, recruiter, admin, verification
    components/             # shared UI components (built from the design system)
    lib/                    # api client, auth helpers, formatters
    styles/                 # theme tokens
    test/
```

The public verification page is its own small route group with no login and no navigation. Keep its bundle light so it loads fast on a phone.

## 5. The most important transaction: issuing a certificate

This must be atomic: either everything happens or nothing does.

```
on approve_evaluation(evaluation):
  begin transaction
    lock the application row
    check application.status is 'submitted'
    check reviewer belongs to the project's company
    check overall_score >= 60
    set application.status = 'completed', completed_at = now
    compute xp from the formula (never from client input)
    generate verification_id (retry on unique collision) and qr_token
    compute content_hash
    insert certificate
    insert xp_event
    recalculate badges from issued certificates
    insert audit_log row
    insert notifications
  commit
  after commit: render certificate PDF and send email (retryable)
```

Revocation is the mirror image in one transaction: set the certificate to revoked with reason, insert a negative XP event, recalculate badges, write the audit log, notify the student.

## 6. Public verification request

1. Rate limit by IP address.
2. Look up `v_public_verification` by QR token (or by verification ID on the manual-entry route).
3. Record a `verification_lookups` row with a hashed IP.
4. Return only the fields in the view. Apply the student's name or initials preference.
5. Send `Cache-Control: no-store` so a revoked record can never be served from a cache.
6. If not found, return the same response shape and timing for every unknown value so IDs cannot be enumerated.

## 7. Configuration

All configuration comes from environment variables. Commit `.env.example`, never `.env`.

```dotenv
# App
APP_ENV=development
APP_BASE_URL=http://localhost:5173
API_BASE_URL=http://localhost:8000
SECRET_KEY=change-me-use-a-long-random-value

# Database
DATABASE_URL=postgresql+psycopg://projectproof:projectproof@localhost:5432/projectproof

# Auth
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=14
COOKIE_SECURE=false

# Storage
STORAGE_BACKEND=local            # local | s3
STORAGE_LOCAL_PATH=./storage
S3_ENDPOINT=
S3_BUCKET=
S3_ACCESS_KEY=
S3_SECRET_KEY=

# Email
EMAIL_BACKEND=console            # console | smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM=no-reply@projectproof.example

# AI
LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=                       # set per provider; never hard-code in source
AI_DAILY_LIMIT_PER_USER=30
AI_TIMEOUT_SECONDS=30

# Business rules (defaults match the PRD)
XP_BASE_PER_DAY=6
XP_CAP_PER_PROJECT=200
MATCH_WEIGHTS=skills:0.5,difficulty:0.2,experience:0.2,availability:0.1

# Limits
MAX_RESUME_MB=5
MAX_SUBMISSION_MB=25
VERIFY_RATE_LIMIT=30/minute
```

## 8. Local development

`docker-compose.yml` should start three services: `db` (PostgreSQL), `api` (FastAPI with reload) and `web` (Vite dev server).

```bash
cp .env.example .env
docker compose up -d db
cd backend && alembic upgrade head && python -m app.scripts.seed
uvicorn app.main:app --reload
cd ../frontend && npm install && npm run dev
```

The seed script creates: one admin, two approved companies, one pending company, five students, a handful of open projects, and a few completed projects with certificates (one revoked) so every screen has data from the first run.

## 9. Deployment (demo scale)

| Part | Simple option |
|---|---|
| Frontend | Static hosting for the built files |
| Backend | One container on any container host, behind HTTPS |
| Database | Managed PostgreSQL, with automatic backups turned on |
| Files | Object storage bucket, private, accessed by signed URLs |
| Domain | One domain; the QR links use it, so choose it before printing anything |

Checklist: HTTPS only, `COOKIE_SECURE=true`, strong `SECRET_KEY`, CORS limited to the frontend origin, database not publicly reachable, backups tested by restoring once, error tracking enabled.

## 10. Continuous integration

On every pull request: lint (Ruff, ESLint), type check, backend tests against a real PostgreSQL service container, frontend unit tests, and a build. Block merging if any step fails. Run the schema test cases in 02-database-schema.md as part of the backend tests.

## 11. Key decisions

| Decision | Choice | Reason | Revisit if |
|---|---|---|---|
| Monolith or microservices | Single backend application | One team, one deployment, simpler to debug | Never needed for this project |
| Server-rendered or single-page app | Single-page app, with a lightweight public page | Rich dashboards for logged-in users | Verification page needs better link previews (then render it on the server) |
| Rules in code or database | Both: business rules in services, integrity rules in the schema | A bug in code cannot corrupt proof records | |
| Where AI runs | Behind one service layer | Validation, logging, cost control, provider swap | |
| Similarity detection | In-house, non-AI algorithm | Explainable, free, runs offline | Hosted tools become acceptable |
| Match score | Deterministic formula, AI only explains | Defensible in a viva and testable | |
| Soft deletes | None; status fields instead | Fewer hidden rows and simpler queries | |

## 12. Known risks of this stack

- WeasyPrint needs system libraries; test PDF generation in the Docker image early.
- Free hosting tiers can sleep, which makes a first demo request slow. Warm the service before the demo.
- LLM providers change models and prices; keep the model name in configuration and prompts in versioned files.
