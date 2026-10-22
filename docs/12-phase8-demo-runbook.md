# Phase 8 Demo Runbook — ProjectProof AI

> **Requirement IDs covered:** FR-CRT-1, FR-CRT-2, FR-CRT-4, FR-VRF-1–3, FR-VRF-5, FR-ADM-1, FR-ADM-5, FR-ADM-7, FR-WRK-5, FR-EVL-5, FR-RWD-4, T-NFR-01, T-NFR-05–08, T-E2E-01–03

---

## 1. Prerequisites

| Dependency | Command |
|---|---|
| PostgreSQL 15+ running | `docker compose up -d db` |
| Backend migrations applied | `cd backend && alembic upgrade head` |
| Demo data seeded | `cd backend && uv run python -m scripts.seed` |
| Backend running | `cd backend && uvicorn app.main:app --reload` |
| Frontend running | `cd frontend && npm run dev` |
| Playwright installed | `cd frontend && npx playwright install --with-deps chromium` |

Copy the **Playwright env vars** printed by the seed script before running E2E tests:

```bash
# Example (your tokens will differ each seed run):
export PLAYWRIGHT_ISSUED_QR_TOKEN=demo-issued-qr-2d2d04f0
export PLAYWRIGHT_ISSUED_QR_TOKEN_2=demo-issued-qr-1c1f12e0
export PLAYWRIGHT_REVOKED_QR_TOKEN=demo-revoked-qr-fa4a3ef1
export PLAYWRIGHT_BASE_URL=http://localhost:5173
```

---

## 2. Seeded Demo Data

### Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@projectproof.ai` | `AdminSecure2026!` |
| Company (Nova Labs) | `contact@novalabs.com` | `NovaLabs2026!` |
| Company (Keystone Soft) | `contact@keystonesoft.io` | `Keystone2026!` |
| Company (BrightWave, pending) | `brightwave.tech@gmail.com` | `BrightWave2026!` |
| Student 1 | `ananya@example.com` | `StudentPass2026!` |
| Student 2 | `rohit@example.com` | `StudentPass2026!` |
| Student 3 | `priya@example.com` | `StudentPass2026!` |
| Student 4 | `siddharth@example.com` | `StudentPass2026!` |
| Student 5 | `aisha@example.com` | `StudentPass2026!` |
| Recruiter | `recruiter@apexsearch.com` | `Recruiter2026!` |

### Open Projects (6)

| Project | Company | Difficulty |
|---|---|---|
| API Gateway Microservices | Nova Labs | Intermediate |
| Cloud Cost Optimisation Dashboard | Nova Labs | Advanced |
| Developer Docs Portal | Nova Labs | Beginner |
| React Component Library | Keystone Soft | Intermediate |
| A/B Testing SDK for Web | Keystone Soft | Advanced |
| Accessibility Audit Toolkit | Keystone Soft | Intermediate |

### Certificates (3)

| Label | Project | Student | Status |
|---|---|---|---|
| ISSUED_1 | ML Pipeline for Churn Prediction | Priya Nair | Issued |
| ISSUED_2 | Full-Stack E-Commerce Platform | Ananya Sharma | Issued |
| REVOKED | Plagiarised Open-Source Dashboard | Rohit Verma | Revoked (plagiarism) |

---

## 3. Five-Minute Demo Script

### Minute 1 — Admin Approves a Company

1. Log in as `admin@projectproof.ai`.
2. Navigate to **Admin → Approval Queue**.
3. Select **BrightWave Tech** (pending).
4. Show the automated trust-score check and AI-drafted notes (labelled "AI draft").
5. Click **Approve** — trust score set to 50, `company_approved` audit row created.
6. Open **Audit Log** and confirm the row is visible and append-only.

> **Requirement:** FR-ADM-1 (approve company), FR-ADM-5 (audit log), Non-negotiable rule 7.

---

### Minute 2 — Student Applies and Works on a Project

1. Log in as `priya@example.com` (Student 3).
2. Browse open projects → select **ML Pipeline for Churn Prediction**.
3. Show AI match score (labelled "AI draft") for the application.
4. Switch to the Workspace — show milestone check-ins and AI mentor suggestion (FR-WRK-5).
5. Submit final work with a GitHub link.

> **Requirement:** FR-APP-1–3, FR-WRK-1, FR-WRK-5.

---

### Minute 3 — Company Reviews and Evaluates

1. Log in as `contact@novalabs.com`.
2. Navigate to **Review Queue**.
3. Open the submission for **ML Pipeline for Churn Prediction**.
4. Show AI feedback draft (labelled "AI draft") — FR-EVL-5.
5. Edit, accept the draft, mark decision **Approved**.
6. Show that a certificate is created automatically via `services/certificate.py`.

> **Requirement:** FR-EVL-1, FR-EVL-5, FR-CRT-1.

---

### Minute 4 — Public Verification (Live, No-Cache)

1. Open a **private / incognito** browser window.
2. Navigate to `/verify/<ISSUED_QR_TOKEN>`.
3. Show the verification page with:
   - **Verified** badge (icon **and** text — never color alone)
   - Student name, project title, company name
   - Skills list, evaluation summary
   - Disclaimer: *"This is a platform record, not formal employment experience."*
4. In DevTools → Network tab, confirm `Cache-Control: no-store` on the API response.
5. Navigate to `/verify/<REVOKED_QR_TOKEN>` — page shows **Revoked** with reason "plagiarism".

> **Requirement:** FR-VRF-1–3, FR-VRF-5, Non-negotiable rule 1.

---

### Minute 5 — Mobile and Accessibility

1. In DevTools, toggle mobile emulation to **360 x 740 px**.
2. Reload the verification page — confirm no horizontal scroll.
3. Press **Tab** through the page — confirm every focusable element has a visible focus ring.
4. Show that all buttons have accessible labels (`aria-label` or text content).

> **Requirement:** DESIGN.md responsive rules, Non-negotiable frontend rules (AGENTS.md).

---

## 4. Running the Full Test Suite

```bash
# Backend — 146 tests
cd backend
uv run pytest                  # 146 passed
uv run ruff check .            # All checks passed
uv run ruff format --check .   # 122 files already formatted

# Playwright E2E (requires seed env vars and running frontend + backend)
cd frontend
PLAYWRIGHT_ISSUED_QR_TOKEN=<token> \
PLAYWRIGHT_REVOKED_QR_TOKEN=<token> \
npx playwright test --project=chromium-desktop
```

---

## 5. Requirement / Test Coverage Matrix

| Requirement | Test ID(s) | File | Status |
|---|---|---|---|
| FR-VRF-1: Public verification live read | T-NFR-01, T-E2E-01a | `test_hardening_nfr.py`, `projectproof.spec.ts` | PASS |
| FR-VRF-2: Cache-Control no-store | T-NFR-01, T-E2E-01a | `test_hardening_nfr.py`, `projectproof.spec.ts` | PASS |
| FR-VRF-3: Revoked certificate displays Revoked | T-E2E-02a | `projectproof.spec.ts` | PASS |
| FR-VRF-5: Revocation reason category shown | T-E2E-02a, T-E2E-02c | `projectproof.spec.ts` | PASS |
| FR-CRT-1: Certificate created in one place | T-CRT-* | `test_certificates.py` | PASS |
| FR-ADM-1: Admin approves company | T-ADM-01, T-NFR-08 | `test_admin.py`, `test_hardening_nfr.py` | PASS |
| FR-ADM-5: Audit log on every admin action | T-NFR-08 | `test_hardening_nfr.py` | PASS |
| FR-ADM-7: Anomaly scanner (A1-A5) | T-ADM-07 | `test_ai.py` | PASS |
| FR-WRK-5: AI mentor | T-WRK-05 | `test_ai.py` | PASS |
| FR-EVL-5: AI feedback drafter | T-EVL-05 | `test_ai.py` | PASS |
| FR-RWD-4: Resume bullet rewriter | T-RWD-04 | `test_ai.py` | PASS |
| NFR: Status icon + text, never color alone | T-NFR-05, T-E2E-03e | `test_hardening_nfr.py`, `projectproof.spec.ts` | PASS |
| NFR: DB constraints + append-only audit | T-NFR-06 | `test_hardening_nfr.py` | PASS |
| NFR: No secrets in code | T-NFR-07 | `test_hardening_nfr.py` | PASS |
| NFR: Concurrency p95 < 1000ms | T-NFR-01 | `test_hardening_nfr.py` | PASS |
| NFR: 360px responsive layout | T-E2E-03a | `projectproof.spec.ts` | PASS |
| NFR: Keyboard operable, visible focus | T-E2E-03b-c | `projectproof.spec.ts` | PASS |
| NFR: Images have alt text | T-E2E-03d | `projectproof.spec.ts` | PASS |

---

## 6. Non-Negotiable Rules Verification Evidence

| Rule | Evidence |
|---|---|
| Rule 1: Verified means live (no-store) | `test_t_nfr_01` and T-E2E-01a both assert `Cache-Control: no-store` |
| Rule 2: Server owns business rules | XP computed in `services/`; never accepted from client body |
| Rule 3: Certificates in one place | Only `services/certificate.py` creates or revokes certs |
| Rule 4: AI behind one door | All LLM calls in `app/ai/`; output logged to `ai_logs`, labelled "AI draft" |
| Rule 5: Parameterised queries only | Ruff + manual audit; no string-joined SQL anywhere |
| Rule 6: Auth: role, ownership, state | Every router tested; another user's record returns 404 |
| Rule 7: Audit everything administrative | `test_t_nfr_08` verifies `company_approved` + `company_suspended` rows exist |
| Rule 8: Privacy by default | Recruiter API filters `is_public = true`; `v_student_portfolio` enforces this |
| Rule 9: No secrets in code or logs | `test_t_nfr_07` scans `.py`, `.ts`, `.tsx`, `.json`, `.sql`, `.env` — zero hits |
| Rule 10: No weakening DB constraints | Constraints and triggers tested in `test_t_nfr_06` — UPDATE/DELETE on audit_log raise |

---

## 7. Phase 8 Deliverables Checklist

- [x] `backend/tests/api/test_hardening_nfr.py` — 5 tests (T-NFR-01, T-NFR-05–08), all passing
- [x] `frontend/playwright.config.ts` — Chromium desktop + 360px mobile projects
- [x] `frontend/tests/e2e/projectproof.spec.ts` — 12 tests across 3 scenarios
- [x] `backend/scripts/seed.py` — enriched with 5 students, 6 open projects, 3 certificates
- [x] `docs/12-phase8-demo-runbook.md` — this document
- [x] Backend: **146/146 tests passing**
- [x] Ruff: **All checks passed**, **122 files already formatted**

---

## 8. Known Limitations and Post-Demo Follow-ups

- Playwright E2E tests assume seed QR tokens are passed via environment variables. A CI pipeline should run `scripts/seed.py` and parse stdout to extract and export them before `playwright test`.
- The `mobile-360` Playwright project requires Chromium. Install with `npx playwright install chromium`.
- The AI Mentor (`FR-WRK-5`) uses a `FakeLLMClient` in all automated tests. The real client is wired via `app/config.py` using `OPENAI_API_KEY` (or compatible provider) in production.
- `test_t_nfr_01` (concurrency benchmark) runs 50 parallel requests through `TestClient` which is synchronous; on a real production server under load the p95 threshold may require adjustment.
