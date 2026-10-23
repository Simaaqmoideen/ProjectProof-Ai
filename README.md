<div align="center">
  <img src="docs/assets/projectproof-hero.svg" alt="ProjectProof AI — a live, verifiable record of completed project work" width="100%" />

  <h1>ProjectProof AI</h1>
  <p><strong>Real project work. Human-reviewed results. Proof anyone can verify.</strong></p>
  <p>
    Companies publish practical projects, students complete them, and recruiters verify the outcome with a live certificate record and QR code.
  </p>
  <p>
    <code>React</code> · <code>TypeScript</code> · <code>FastAPI</code> · <code>PostgreSQL</code> · <code>AI drafts, people decide</code>
  </p>
</div>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#how-the-proof-loop-works">Proof loop</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#api-and-verification">API</a> ·
  <a href="#documentation">Documentation</a>
</p>

---

## What is ProjectProof?

ProjectProof AI is a project-based experience platform. Approved companies post scoped projects; students apply, complete milestones and submit work; company reviewers evaluate the result; and successful completions receive a certificate with a unique verification ID and QR code.

The public verification page reads the current certificate record from PostgreSQL on every request. A recruiter can scan the QR code or enter the verification ID to see whether the record is issued or revoked.

> **A certificate is a ProjectProof platform record, not formal employment experience.** It documents a reviewed project completion and must not be presented as proof of employment.

### Trust, by design

| Principle | What it means in the product |
| --- | --- |
| **Live means live** | Public verification reads the database view for each request and sends `Cache-Control: no-store`. |
| **People make decisions** | AI can draft or summarize. A person accepts AI suggestions and a company reviewer decides whether work passes. |
| **One certificate path** | Certificate issue and revocation run through the certificate service and transaction rules. |
| **Privacy first** | Student profiles are private by default; the public verification response contains only approved fields. |
| **Auditable administration** | Administrative and company state changes are recorded in the append-only audit log. |

## How the proof loop works

![Student project journey from application through verified certificate](assets/student-journey.svg)

```mermaid
flowchart LR
    A[Company is approved] --> B[Company publishes a project]
    B --> C[Student applies]
    C --> D[Company selects a student]
    D --> E[Milestones and check-ins]
    E --> F[Student submits work]
    F --> G[Company reviewer evaluates]
    G -->|Approved| H[Certificate service transaction]
    G -->|Changes requested| E
    G -->|Rejected| I[Appeal path]
    I -->|Overturned| G
    H --> J[Certificate + ID + QR]
    H --> K[XP + badges + audit + notifications]
    J --> L[Public live verification]
    L --> M{Later revoked?}
    M -->|No| N[Shows current issued record]
    M -->|Yes| O[Shows revoked record after fresh lookup]
```

The approval transaction is atomic: the application completion, certificate, XP event, badge recalculation, audit row and notifications succeed together or roll back together. PDF rendering and email happen after that transaction and can be retried.

## Architecture

```mermaid
flowchart LR
    subgraph Client[Browser]
        WEB[React + TypeScript app]
        VERIFY[Public verification page]
    end

    WEB -->|JSON over HTTPS| API[FastAPI routers]
    VERIFY -->|fresh lookup, no-store| API

    subgraph Backend[Backend layers]
        API --> SVC[Services: business rules]
        SVC --> REPO[Repositories: parameterized queries]
        SVC --> AI[AI boundary: validated drafts]
        SVC --> FILES[File and PDF services]
        SVC --> MAIL[Email service]
    end

    REPO --> DB[(PostgreSQL)]
    AI --> LLM[Configured LLM provider]
    AI --> SIM[Local similarity engine]
    FILES --> STORE[(Local storage in dev<br/>private object storage in production)]
    MAIL --> SMTP[SMTP provider]
```

### Main data relationships

```mermaid
erDiagram
    USER ||--o| STUDENT_PROFILE : has
    USER ||--o| COMPANY : owns
    USER ||--o| RECRUITER_PROFILE : has
    COMPANY ||--o{ PROJECT : publishes
    PROJECT ||--o{ MILESTONE : defines
    STUDENT_PROFILE ||--o{ APPLICATION : submits
    PROJECT ||--o{ APPLICATION : receives
    APPLICATION ||--o{ SUBMISSION : contains
    APPLICATION ||--o{ EVALUATION : reviewed_by
    APPLICATION ||--o| CERTIFICATE : may_issue
    CERTIFICATE ||--o{ XP_EVENT : records
    USER ||--o{ AUDIT_LOG : performs
```

This is a high-level view; the canonical tables, constraints and views are in [`schema.sql`](schema.sql) and [`docs/02-database-schema.md`](docs/02-database-schema.md).

### Match score composition

The deterministic project-match score is a weighted formula. The weights live in backend configuration and are documented in the product and AI specifications.

<div align="center">
  <img src="docs/assets/match-score.svg" alt="Match score weights: skills 50%, difficulty fit 20%, experience 20%, availability 10%" width="720" />
</div>

## Product areas

| Area | Capabilities |
| --- | --- |
| **Accounts and trust** | Student, company, recruiter and admin roles; email verification; approval queues; role and ownership checks. |
| **Projects and applications** | Company projects, milestones and tasks; browsing, recommendations, match breakdowns, application review and applicant comparison. |
| **Student workspace** | Check-ins, task progress, submission versions, evaluation feedback, appeals, XP, levels and badges. |
| **Certificates** | Transactional issue and revocation, PDF, verification ID, QR code and public live record. |
| **Recruiter tools** | Search approved, public student profiles and open verified-project portfolios. |
| **AI assistance** | Resume and project drafts, ranking, pre-review, skill-gap and mentor features where configured. AI results are drafts; people decide and accept. |
| **Admin controls** | Company and recruiter approvals, reports and flags, project removal, certificate revocation, platform stats and audit log. |

GitHub information is public, self-linked context. It is labelled **“self-linked, not verified”** and does not affect XP, badges, match experience or certificate verification.

## Technology

| Layer | Stack |
| --- | --- |
| Web | React 18, TypeScript, Vite, React Router, Tailwind CSS |
| API | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2 |
| Database | PostgreSQL 14+; the Compose setup uses PostgreSQL 16 |
| Schema source | PostgreSQL definition in `schema.sql`; versioned migrations belong in `backend/migrations/` |
| Certificates | Server-side QR generation and PDF rendering |
| Tests and quality | pytest, Ruff, Vitest, Playwright, GitHub Actions |
| Local services | Docker Compose or a local PostgreSQL instance |

## Quick start

### Prerequisites

- Docker Desktop with Docker Compose, **or** PostgreSQL 14+ installed locally
- For running outside Docker: Python 3.12+, Node.js 20+, npm, and [uv](https://docs.astral.sh/uv/)

### Option A — Docker Compose

1. Create the root environment file. In PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   Or on macOS/Linux:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env`. Use the Psycopg 3 URL format expected by this backend, replace the development secret, and set the frontend origin:

   ```dotenv
   DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/projectproof
   JWT_SECRET=replace-with-a-long-random-secret
   FRONTEND_URL=http://localhost:5173
   ```

3. Create `frontend/.env` so the Vite proxy can reach the API container by its Compose service name:

   ```dotenv
   VITE_BACKEND_URL=http://api:8000
   ```

4. Build and start the services, then load demo data:

   ```bash
   docker compose up --build -d
   docker compose exec api python scripts/seed.py
   ```

5. Open the app and API:

   - Web app: [http://localhost:5173](http://localhost:5173)
   - API health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
   - Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

The Compose database maps host port `5433` to container port `5432`. `schema.sql` is loaded when PostgreSQL initializes a **new** data volume. Keep the volume if you need its data; do not remove it as a routine troubleshooting step. The seed script prints development demo credentials—never reuse those credentials in a deployed environment.

To inspect startup problems, run `docker compose ps` and `docker compose logs -f api db frontend`.

### Option B — Local PostgreSQL

Create a `projectproof` database, apply the schema once, and configure the backend to use your local database. For a PostgreSQL server on the default port:

```bash
createdb -U postgres projectproof
psql -U postgres -d projectproof -f schema.sql
```

Create `backend/.env` with your local connection and frontend URL:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/projectproof
JWT_SECRET=replace-with-a-long-random-secret
FRONTEND_URL=http://localhost:5173
```

Then run the API and frontend in separate terminals:

```bash
cd backend
uv sync --locked --extra dev
uv run python scripts/seed.py
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm ci
npm run dev
```

For a phone to scan a QR code during local development, use the PC’s LAN address in `FRONTEND_URL` (for example `http://192.168.1.20:5173`), start Vite with `npm run dev -- --host 0.0.0.0`, and keep the phone on the same network. For scans from anywhere, deploy to a public HTTPS domain instead.

## API and verification

The API base path is `/api/v1`. FastAPI serves the interactive schema at `/docs`.

| Route | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/health` | Public | Liveness check |
| `POST /api/v1/auth/register` and `/login` | Public | Account creation and sign-in |
| `GET /api/v1/projects` | Authenticated roles | Browse open projects and filters |
| `POST /api/v1/projects/{id}/applications` | Student | Apply to a project |
| `POST /api/v1/applications/{id}/submissions` | Student owner | Submit project work |
| `POST /api/v1/submissions/{id}/evaluation` | Company reviewer | Record a human evaluation |
| `GET /api/v1/certificates/{id}/pdf` | Authorized owner, issuer or admin | Download certificate PDF |
| `GET /api/v1/public/verify/{qr_token}` | Public | Verify a QR link against live data |
| `GET /api/v1/public/verify-id/{verification_id}` | Public | Verify by typed ID |

Public verification is rate-limited, returns only the public view, and sends `Cache-Control: no-store`. A revoked certificate is shown as revoked on the next fresh lookup. The verification page never includes private feedback, email addresses or AI output.

## Development checks

Run these from the relevant folder:

```bash
# Backend
cd backend
uv run ruff check .
uv run pytest

# Frontend
cd frontend
npm run lint
npm test -- --run
npm run build
```

End-to-end tests use Playwright and require the app, database and browser dependencies to be available:

```bash
cd frontend
npx playwright test
```

The CI workflow is in [`.github/workflows/ci.yml`](.github/workflows/ci.yml). See [`docs/08-test-plan.md`](docs/08-test-plan.md) for requirement-mapped scenarios.

## Deployment checklist

- Set `FRONTEND_URL` to the canonical public **HTTPS** origin before generating QR codes or PDFs.
- Set a strong, unique `JWT_SECRET`; store secrets in the hosting platform, never in Git.
- Configure the frontend API proxy/origin and backend CORS for the deployed domains.
- Use a managed PostgreSQL database with tested backups; keep it off the public internet.
- Use private object storage for uploaded files and signed/authenticated download routes.
- Configure real SMTP and an explicitly chosen AI provider only if those features are enabled.
- Disable or replace seeded demo accounts and development-only credentials.
- Exclude public verification routes from CDN/browser caching.
- Check a fresh QR scan, a not-found response and a revoked certificate after deployment.

QR links use `FRONTEND_URL`. A QR printed into an older PDF cannot change when the domain setting changes, so regenerate PDFs after moving to a permanent public domain.

## Documentation

| Document | Covers |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | Project rules for contributors and coding agents |
| [`DESIGN.md`](DESIGN.md) | UI colors, type, spacing and component direction |
| [`docs/00-README.md`](docs/00-README.md) | Index and reading order for the specification set |
| [`docs/01-product-requirements.md`](docs/01-product-requirements.md) | Product scope, requirements and business rules |
| [`docs/02-database-schema.md`](docs/02-database-schema.md) | Tables, constraints and views |
| [`docs/03-tech-stack-and-architecture.md`](docs/03-tech-stack-and-architecture.md) | Architecture, configuration and deployment choices |
| [`docs/04-api-specification.md`](docs/04-api-specification.md) | Routes, request/response contracts and errors |
| [`docs/05-workflows-and-state-machines.md`](docs/05-workflows-and-state-machines.md) | Allowed state changes and end-to-end workflows |
| [`docs/06-ai-modules-specification.md`](docs/06-ai-modules-specification.md) | AI boundaries, algorithms and draft acceptance |
| [`docs/07-security-and-privacy.md`](docs/07-security-and-privacy.md) | Threats, access control and privacy |
| [`docs/08-test-plan.md`](docs/08-test-plan.md) | Test cases and acceptance criteria |
| [`docs/09-project-plan-and-demo.md`](docs/09-project-plan-and-demo.md) | Build phases and demo runbook |
| [`docs/10-college-report-pack.md`](docs/10-college-report-pack.md) | Report and presentation planning |
| [`docs/11-traceability-and-changes.md`](docs/11-traceability-and-changes.md) | Requirement traceability and v2 changes |
| [`docs/12-phase8-demo-runbook.md`](docs/12-phase8-demo-runbook.md) | Phase 8 demo preparation |

## Contributing

1. Read `AGENTS.md` and the source-of-truth document for the area you are changing.
2. Cite the relevant requirement ID in the plan and commit message for feature work.
3. Keep business rules on the server, use parameterized queries, and add tests with the change.
4. Update the specification when behavior changes; do not silently make code and docs disagree.
5. Never commit `.env`, credentials, personal data or generated private uploads.

See [`AGENTS.md`](AGENTS.md) for the full contribution and security rules.
