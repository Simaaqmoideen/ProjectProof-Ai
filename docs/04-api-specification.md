# ProjectProof AI: API Specification

REST over HTTPS, JSON bodies. FastAPI will generate the full OpenAPI document automatically; this file defines the contract the generated document must match. Base path: `/api/v1`.

## 1. Conventions

**Authentication.** `Authorization: Bearer <access_token>` on every route except those marked *public*. The refresh token lives in an HttpOnly, Secure, SameSite=Lax cookie and is used only by `/auth/refresh`.

**Roles.** `student`, `company`, `recruiter`, `admin`. A route lists who may call it. Anyone else gets `403`. A user asking for another user's record gets `404`, not `403`, so IDs cannot be probed.

**IDs.** UUIDs, except `verification_id` (e.g. `EXP-2026-AB12-9821`) and `qr_token`.

**Timestamps.** ISO 8601 in UTC.

**Pagination.** `?page=1&page_size=20` (max 100). Responses: `{ "items": [...], "page": 1, "page_size": 20, "total": 134 }`.

**Errors.** Always this shape:
```json
{ "error": { "code": "validation_error", "message": "Human-readable summary", "details": [ { "field": "email", "issue": "invalid" } ], "request_id": "..." } }
```

| Status | Code | When |
|---|---|---|
| 400 | `validation_error` | Body or query failed validation |
| 401 | `unauthenticated` | Missing or expired token |
| 403 | `forbidden` | Role not allowed, or account not approved or not verified |
| 404 | `not_found` | Missing, or not visible to this user |
| 409 | `conflict` | Duplicate or invalid state transition |
| 413 | `file_too_large` | Upload over limit |
| 422 | `ai_output_invalid` | AI returned unusable output (the user sees a retry message) |
| 429 | `rate_limited` | Too many requests or AI quota used |
| 503 | `ai_unavailable` | AI provider down; manual path still works |

**Idempotency.** `POST` actions that must not repeat (apply, submit, approve, revoke) accept an `Idempotency-Key` header and return the first result for a repeated key.

**Rate limits (defaults).** Login 5 per minute per IP and account. Public verification 30 per minute per IP. AI routes follow the per-user daily limit. Resume and file uploads 10 per hour per user.

## 2. Auth

| Method and path | Who | Purpose |
|---|---|---|
| `POST /auth/register` | public | Create account (`role` is student, company or recruiter) |
| `POST /auth/verify-email` | public | Confirm email with a one-time token |
| `POST /auth/login` | public | Returns access token, sets refresh cookie |
| `POST /auth/refresh` | cookie | New access token |
| `POST /auth/logout` | any | Revokes the refresh token |
| `POST /auth/forgot-password` | public | Sends reset link (always responds the same) |
| `POST /auth/reset-password` | public | Sets new password with token |
| `GET /me` | any | Current user and role-specific status |

```json
// POST /auth/register
{ "email": "ananya@example.com", "password": "********", "role": "student", "full_name": "Ananya R." }
// 201
{ "id": "…", "role": "student", "email_verified": false }
```

Password rules: at least 10 characters, checked against a list of common passwords. No composition rules.

## 3. Students

| Method and path | Who | Purpose |
|---|---|---|
| `GET /students/me` | student | Own profile |
| `PUT /students/me` | student | Update profile fields |
| `PUT /students/me/visibility` | student | `{ "is_public": true, "show_full_name_on_verification": false }`; logs consent |
| `GET /students/me/skills` | student | Own skills |
| `PUT /students/me/skills` | student | Replace skills list `[{ "skill": "Python", "proficiency": 4 }]` |
| `POST /students/me/resume` | student | Upload PDF (multipart) |
| `DELETE /students/me/resume` | student | Remove file and parsed data |
| `GET /students/me/dashboard` | student | Next action, active projects, XP, level, badges, stats |
| `GET /students/me/certificates` | student | Own certificates |
| `GET /students/me/portfolio` | student | Verified project history from `v_student_portfolio` (FR-STU-10), issued and revoked |
| `PUT /students/me/github` | student | `{ "username": "octocat" }`; reads the public profile and repositories through GitHub's public API; stores nothing but the username until an analysis is accepted (FR-STU-8) |
| `GET /students/me/github` | student | Languages, repository count, recent activity; labelled "self-linked, not verified" |
| `DELETE /students/me/github` | student | Unlink and delete the stored GitHub summary |
| `POST /students/me/export` | student | Prepare data export |
| `DELETE /students/me` | student | Anonymise account (requires password) |

## 4. Companies and recruiters

| Method and path | Who | Purpose |
|---|---|---|
| `POST /companies` | company | Register company (multipart with registration document) |
| `GET /companies/me` | company | Company, status, trust score and what affects it |
| `PUT /companies/me` | company | Edit description and website (domain changes need admin review) |
| `GET /companies/me/stats` | company | Projects, selections, completions, pending reviews |
| `POST /companies/me/members` | company owner | Add a reviewer account |
| `POST /recruiters` | recruiter | Complete recruiter profile (organization, work email domain) |
| `GET /recruiters/me` | recruiter | Own profile and approval status |

## 5. Projects

| Method and path | Who | Purpose |
|---|---|---|
| `GET /projects` | student, recruiter, admin | List open projects. Filters: `skill`, `difficulty`, `category`, `q`, `sort=match\|newest\|xp` |
| `GET /projects/recommended` | student | Open projects ranked by the recommendation score with a reason each (FR-APP-10, BR-10) |
| `GET /projects/{id}` | authenticated | Detail; students also get their match breakdown |
| `POST /projects/{id}/report` | student, recruiter, company | `{ "reason", "note" }`; opens a manual flag (FR-ADM-9) |
| `POST /companies/me/projects` | approved company | Create draft |
| `PUT /projects/{id}` | owning company | Edit draft (locked fields enforced after first selection) |
| `PUT /projects/{id}/milestones` | owning company | Replace milestones list. Each milestone may carry `tasks: [{ "title", "description" }]` (0 to 10; FR-WRK-7). Rejected with `409` after the first selection |
| `POST /projects/{id}/publish` | owning company | draft to open; checks approval and the new-company limit |
| `POST /projects/{id}/close` | owning company | Stop applications |
| `POST /projects/{id}/cancel` | owning company | Cancel; notifies applicants |

`xp_max` appears in project responses and is rejected if sent in a request body.

```json
// GET /projects/{id} (student)
{ "id": "…", "title": "Build an E-Commerce API", "company": { "name": "Nova Labs", "approved": true },
  "difficulty": "intermediate", "duration_days": 14, "xp_max": 151,
  "skills": ["Python","Flask","MySQL","REST API"],
  "match": { "score": 94, "breakdown": { "skills": 100, "difficulty": 90, "experience": 85, "availability": 90 } } }
```

## 6. Applications and selection

| Method and path | Who | Purpose |
|---|---|---|
| `POST /projects/{id}/applications` | student | Apply; stores match score and breakdown |
| `GET /applications` | student | Own applications |
| `GET /applications/{id}` | student (owner), company (project owner) | Detail |
| `POST /applications/{id}/withdraw` | student | Withdraw before submission |
| `GET /projects/{id}/applications` | owning company | Applicants with filters and sort |
| `POST /applications/{id}/select` | owning company | applied to in_progress; sets `started_at` and `due_at`; respects `max_selected` |
| `POST /applications/{id}/reject` | owning company | applied to rejected |
| `GET /projects/{id}/applications/compare?ids=a,b,c` | owning company | 2 or 3 applicants side by side: skills, match breakdown, XP, verified project count, GitHub summary, cover note (FR-APP-6) |

## 7. Workspace, submissions, evaluation

| Method and path | Who | Purpose |
|---|---|---|
| `GET /applications/{id}/workspace` | student, company | Milestones with due dates, check-ins, status |
| `POST /applications/{id}/checkins` | student | `{ "milestone_id", "note", "evidence_url" }` |
| `POST /checkins/{id}/review` | owning company | `{ "status": "accepted" \| "needs_work", "review_note" }` |
| `PUT /applications/{id}/tasks/{task_id}/progress` | student (owner) | `{ "status": "todo" \| "in_progress" \| "done" }` on a company task or the student's own sub-task (FR-WRK-7) |
| `POST /applications/{id}/milestones/{milestone_id}/tasks` | student (owner) | `{ "title", "description" }`; creates a personal sub-task (FR-WRK-8); only while the application is `in_progress` or `changes_requested` |
| `DELETE /applications/{id}/tasks/{task_id}` | student (owner) | Delete a personal sub-task only; company tasks return `409` |
| `POST /applications/{id}/submissions` | student | Submit repo URL and/or file; creates next version (max 3) |
| `GET /submissions/{id}` | student, company | Detail with similarity result and AI pre-review (company sees both; student sees pre-review only if the company shares it) |
| `POST /submissions/{id}/evaluation` | company reviewer | Record the decision (see below) |
| `GET /evaluations/{id}` | student, company | Detail |
| `POST /evaluations/{id}/appeal` | student | `{ "reason" }`, within 7 days |

```json
// POST /submissions/{id}/evaluation
{ "rubric_scores": { "functionality": 90, "code_quality": 85, "documentation": 80 },
  "overall_score": 87, "feedback": "…", "public_summary": "All 6 milestones met. …",
  "decision": "approved", "used_ai_draft": false }
// 201 when approved:
{ "evaluation_id": "…", "application_status": "completed",
  "certificate": { "verification_id": "EXP-2026-AB12-9821", "xp_awarded": 139, "status": "issued" } }
```

`overall_score` below 60 with `approved` returns `409 conflict`. The certificate is created in the same transaction (see 03).

## 8. Certificates and public verification

| Method and path | Who | Purpose |
|---|---|---|
| `GET /certificates/{id}/pdf` | student (owner), company (issuer), admin | Certificate PDF |
| `POST /certificates/{id}/revocation-request` | company (issuer) | `{ "reason", "note" }`; opens a flag |
| `GET /public/verify/{qr_token}` | **public** | Verification record by QR token |
| `GET /public/verify-id/{verification_id}` | **public** | Same record by typed ID |

```json
// GET /public/verify/{qr_token}  (always Cache-Control: no-store)
{ "verification_id": "EXP-2026-AB12-9821", "status": "issued",
  "project": { "title": "Build an E-Commerce API", "difficulty": "intermediate", "duration_days": 14 },
  "company": { "name": "Nova Labs", "approved": true },
  "student": { "display_name": "Ananya R." },
  "evaluation": { "summary": "All 6 milestones met. …", "evaluated_at": "2026-08-20T10:12:00Z" },
  "skills": ["Python","Flask","MySQL","REST API"],
  "timeline": { "applied_at": "…", "started_at": "…", "completed_at": "…" },
  "qr_code_data_uri": "data:image/png;base64,…",
  "checked_at": "2026-10-03T10:42:00Z",
  "disclaimer": "This is a ProjectProof verification record. It is not formal employment experience." }
// revoked example: "status": "revoked", plus "revoked_at" and "revocation_reason" (category only)
// unknown value: 404 with the standard error body, same timing as a found record
```

The live public response includes a `qr_code_data_uri` PNG for the record's QR-token URL so the verification page can display a scannable code. The QR token remains encoded in the image and is not returned as a separate response field.

The public response never includes email, private feedback, AI output or internal IDs.

## 9. Recruiter

| Method and path | Who | Purpose |
|---|---|---|
| `GET /recruiter/students` | approved recruiter | Search public students: `skills`, `min_xp`, `min_verified`, `verified_only`. Sorted by verified project count, then XP (FR-REC-4) |
| `GET /recruiter/students/{id}` | approved recruiter | Public portfolio (FR-STU-10 data), each project with its verification link; only if `is_public`, otherwise `404` |
| `POST /recruiter/search/interpret` | approved recruiter | Plain text to a validated filter object the recruiter can edit |

## 10. Admin

| Method and path | Who | Purpose |
|---|---|---|
| `GET /admin/companies?status=pending` | admin | Approval queue with automatic check results |
| `POST /admin/companies/{id}/approve` | admin | Approve (writes audit log) |
| `POST /admin/companies/{id}/reject` | admin | `{ "reason" }` |
| `POST /admin/companies/{id}/request-info` | admin | Message to company |
| `POST /admin/companies/{id}/suspend` | admin | Closes open projects |
| `GET /admin/recruiters`, `POST /admin/recruiters/{id}/approve\|reject` | admin | Same for recruiters |
| `GET /admin/flags` | admin | Queue; filter by kind and status |
| `POST /admin/flags/{id}/resolve` | admin | `{ "status": "dismissed" \| "confirmed", "note" }` |
| `GET /admin/appeals` | admin | Queue |
| `POST /admin/appeals/{id}/resolve` | admin | `{ "status": "upheld" \| "overturned", "note" }` |
| `GET /admin/projects` | admin | Browse all projects by status, including reported ones |
| `POST /admin/projects/{id}/remove` | admin | `{ "reason", "note" }`; reason required. Sets `removed`, rejects `applied` and withdraws `in_progress` applications with `status_reason = project_removed`, notifies everyone, lowers trust score, writes the audit log, all in one transaction (FR-ADM-8) |
| `POST /admin/certificates/{id}/revoke` | admin | `{ "reason": "fraud\|plagiarism\|evaluation_overturned\|company_error\|other", "note" }` |
| `GET /admin/audit-log` | admin | Read-only, filters: actor, action, entity, date |
| `POST /admin/users/{id}/suspend`, `.../reactivate` | admin | Account control |
| `GET /admin/stats` | admin | Platform statistics from `v_platform_stats` (FR-ANA-3) |

## 11. AI routes

All AI routes: authenticated, quota checked, response includes `{ "ai": { "label": "AI draft", "confidence": "low\|medium\|high", "log_id": 123 }, "result": { … } }`. Nothing is saved until the client calls the accept route, which sends `log_id` and the (possibly edited) values.

| Method and path | Who | Tier |
|---|---|---|
| `POST /ai/resume/analyze` | student | AI highlight |
| `POST /ai/resume/accept` | student | AI highlight |
| `POST /ai/projects/brief` | approved company | AI highlight |
| `GET /ai/projects/{id}/match` | student | AI highlight (deterministic score plus explanation) |
| `POST /ai/projects/{id}/rank-applicants` | owning company | AI highlight |
| `POST /ai/submissions/{id}/prereview` | owning company | AI highlight |
| `POST /ai/skill-gap` | student | AI highlight (v2); body `{ "project_id" }`; missing skills are deterministic, AI orders the learning |
| `POST /ai/github/analyze` | student with linked GitHub | AI highlight (v2) |
| `POST /ai/github/accept` | student | AI highlight (v2); saves only the accepted items |
| `POST /ai/evaluations/draft-feedback` | company reviewer | Stretch |
| `POST /ai/mentor/chat` | student with active project | Stretch |
| `POST /ai/roadmap` | student | Stretch |
| `POST /ai/rewrite/resume-bullets` | student | Stretch |
| `POST /ai/interview/start`, `/answer` | student | Stretch |
| `POST /ai/log/{id}/feedback` | any | Records accepted or dismissed |

## 12. Notifications and misc

| Method and path | Who | Purpose |
|---|---|---|
| `GET /notifications` | any | Own notifications, newest first |
| `POST /notifications/{id}/read`, `POST /notifications/read-all` | any | Mark read |
| `GET /skills?q=` | authenticated | Skill autocomplete |
| `GET /health` | public | Liveness for hosting checks (no details) |

## 13. Cross-cutting rules

- Every route checks role, then ownership, then state, in that order.
- Admin and company state changes write an `audit_log` row in the same transaction.
- File uploads: check size, check the real type (not the file name), store under a random key, never serve from a path the user controls, serve downloads through signed or authenticated routes.
- Never log passwords, tokens, resume text or full AI prompts containing personal data.
- Response models are explicit; never return a database row directly.
