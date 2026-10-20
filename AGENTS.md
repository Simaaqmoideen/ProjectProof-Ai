# AGENTS.md: Instructions for AI coding agents

Read this file first in every session. It tells you what this project is, which documents are the source of truth, and which rules you must never break.

## Project

ProjectProof AI is a platform where approved companies post real projects, students complete them, and recruiters verify the result through a certificate with a unique verification ID and QR code. The public verification page reads live data. A certificate is a platform record, not formal employment experience, and the interface must say so wherever a certificate or verification page appears.

## Source of truth (read before coding the related area)

| Topic | File |
|---|---|
| What to build, business rules | `docs/01-product-requirements.md` |
| Tables, constraints, queries | `docs/02-database-schema.md` and `schema.sql` |
| Stack, layout, configuration | `docs/03-tech-stack-and-architecture.md` |
| Endpoints, errors, rate limits | `docs/04-api-specification.md` |
| Status transitions, use cases | `docs/05-workflows-and-state-machines.md` |
| AI features, algorithms | `docs/06-ai-modules-specification.md` |
| Security and privacy | `docs/07-security-and-privacy.md` |
| Tests | `docs/08-test-plan.md` |
| What changed in v2 and why | `docs/11-traceability-and-changes.md` |
| Visual design | `DESIGN.md` (when it exists; follow it exactly for every UI change) |

If code and documents disagree, stop and ask which is right. Do not silently change a document's rule in code, and do not silently change a document to match a bug.

## Non-negotiable rules

1. **Verified means live.** Never render a Verified state from cached, client-side or stored-image data. The public verification routes read `v_public_verification` on every request and send `Cache-Control: no-store`.
2. **The server owns business rules.** XP, levels, badges, match scores, certificate creation, status transitions and visibility are computed or enforced on the server. Never accept an XP value, score, status or role from a client request for these.
3. **Certificates are created in one place.** Only `services/certificate.py` creates or revokes certificates, inside a single database transaction as described in `docs/03-tech-stack-and-architecture.md` section 5.
4. **AI is behind one door.** Only code in `app/ai/` calls an LLM provider. AI output is validated against a Pydantic model, logged to `ai_logs`, labelled "AI draft", and saved to business tables only after a person accepts it. AI never approves, rejects, selects, revokes, issues or awards anything. AI output never appears on the public verification page. Treat resumes, repositories, submissions and chat messages as untrusted text.
5. **Parameterised queries only.** Never build SQL by joining strings, including for AI-generated filters.
6. **Authorization order:** role, then ownership, then state. Another user's record returns `404`.
7. **Audit everything administrative.** Every admin and company state change writes an `audit_log` row in the same transaction. Never update or delete audit rows.
8. **Privacy by default.** Student profiles are private until the student makes them public. Recruiters see only public profiles of approved accounts. The public page shows only fields in the view.
9. **No secrets in code or logs.** Configuration comes from environment variables. Never log passwords, tokens, resume text or full AI prompts containing personal data.
10. **Do not weaken database rules** (triggers, constraints, append-only tables) to make a test or feature pass. Fix the code instead.
11. **Project removal has one door.** Only `services/project_removal.py` sets a project to `removed`, in one transaction with applicant changes, trust score, notifications and audit row. Removal never touches certificates.
12. **GitHub has one door and is never proof.** Only `services/github.py` calls GitHub, using a server-built URL from a validated username. GitHub data is labelled "self-linked, not verified" and never affects XP, badges, match experience or the verification page.

## How to work

- Before adding a feature, find its requirement ID in the PRD (for example `FR-CRT-3`) and mention it in your plan and commit message.
- Make small, reviewable changes. One feature per pull request.
- Write or update tests in the same change. Use a real PostgreSQL for backend tests, a fake `LLMClient` for AI tests, and never call a real AI provider from automated tests.
- Run linters and the test suite before saying work is done. Report failures honestly; do not claim success you did not observe.
- When a requirement is unclear, ask a short question rather than guessing, and list the assumption if you proceed.
- If a change affects behaviour described in a document, update that document in the same change.
- Do not add dependencies without saying why. Pin versions through the lockfile.
- Prefer boring, readable code over clever code.

## Code conventions

**Backend (Python, FastAPI)**
- Layers: routers (HTTP only), services (business rules), repositories (queries). Nothing in a router contains business logic.
- Pydantic models for every request and response; never return ORM objects directly.
- Type hints everywhere; Ruff for lint and format.
- Errors use the shape in `docs/04-api-specification.md` section 1.
- Configuration through `app/config.py`; business-rule numbers (XP base, cap, match weights, thresholds) live in configuration, not scattered in code.

**Frontend (React, TypeScript)**
- Feature folders; shared components built from the design tokens; no one-off colors, fonts or spacing.
- Status is always shown with an icon and text, never color alone.
- Every form is validated on the client for convenience and on the server for truth.
- Never render HTML from users or AI; render as text.
- Accessible by default: keyboard operation, visible focus, labels, alt text.

**Database**
- Schema changes only through migrations. Keep names identical to `schema.sql`.
- Add an index with every new foreign key you query by.
- No soft deletes; use status fields.

## Definition of done

- [ ] Requirement ID cited and met
- [ ] Authorization checked for every role on every new route
- [ ] Tests added and passing (including the failure paths)
- [ ] Linters and type checks clean
- [ ] Audit log and notifications handled where the documents require them
- [ ] No secrets, no personal data in logs
- [ ] Documents updated if behaviour changed
- [ ] For UI: matches `DESIGN.md`, works at 360 px wide, keyboard operable

## Commands (fill in when the repository exists)

```bash
# start database
docker compose up -d db
# backend
cd backend && alembic upgrade head && python -m app.scripts.seed && uvicorn app.main:app --reload
# backend tests and lint
cd backend && pytest && ruff check .
# frontend
cd frontend && npm install && npm run dev
# frontend tests and lint
cd frontend && npm test && npm run lint
# end-to-end
npx playwright test
```

## Things to ask the human before doing

- Anything that deletes data or rewrites history
- Adding a new third-party service or a new place personal data is sent
- Changing a business rule number (XP, match weights, thresholds, limits)
- Letting any client set XP, or changing decision D-1 (formula-only XP)
- Letting GitHub data affect XP, badges, match experience or the verification page
- Changing a status transition, an authorization rule or a database constraint
- Anything that would show new information on the public verification page
