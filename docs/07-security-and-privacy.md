# ProjectProof AI: Security and Privacy

This is an engineering document, not legal advice. Where the law matters (section 9), it tells you what to check rather than claiming what the law says.

## 1. What needs protecting

| Asset | Why it matters | Main risk |
|---|---|---|
| Certificate and verification records | The whole value of the product is that they can be trusted | Forgery, tampering, fake issuers |
| Student personal data (name, email, resume, GitHub, college) | Personal data | Leak, scraping, unwanted recruiter access |
| Company submissions and project briefs | Business material | Leak to other students |
| Accounts and tokens | Control of everything above | Takeover |
| Admin powers | Can approve, revoke, suspend | Abuse or compromise |
| AI service and budget | Costs money, influences decisions | Abuse, injection, cost overrun |

## 2. Threats and controls

| ID | Threat | Controls |
|---|---|---|
| T1 | Fake company issues certificates to friends | Admin approval; domain-email check; one active company per domain; limit of 2 open projects until 3 evaluations; trust score; anomaly rules A1 to A4; public page shows "Approved company" |
| T2 | Forged or edited certificate | Certificates only created by one service inside a transaction; database triggers block edits and deletes; content hash lets you detect tampering; verification page reads live data, never a stored image |
| T3 | Guessing or enumerating verification IDs | QR links use a 128-bit random token; ID lookup is rate limited; not-found responses look and time the same; failed-lookup bursts raise an anomaly flag |
| T4 | Stale or cached "Verified" after revocation | `Cache-Control: no-store` on the public routes; no CDN caching of them; the UI never shows Verified without a fresh response |
| T5 | Account takeover (credential stuffing, weak passwords) | Argon2id hashing; minimum 10 characters checked against common passwords; login rate limit per IP and per account; email verification; short-lived access tokens; refresh token rotation and revocation on password change |
| T6 | Broken access control (a user opens another user's data) | Role check, then ownership check, then state check on every route; other users' records return 404; automated tests for every role and route (see 08-test-plan.md) |
| T7 | Injection into the database | Parameterised queries only; ORM for normal access; no string-built SQL anywhere, including AI-produced filters |
| T8 | Cross-site scripting (XSS) | Frontend escapes output by default; no raw HTML from users or AI; Content Security Policy; sanitise any rich text on the server |
| T9 | Cross-site request forgery | Access token in a header (not a cookie); the refresh cookie is SameSite=Lax and only accepted by the refresh route; CORS limited to the frontend origin |
| T10 | Malicious file upload (resume, submission) | Size limits; detect real file type, not the file name; store under random keys outside the web root; never execute uploads; download through authenticated or signed routes; optional malware scan |
| T11 | Prompt injection through resumes, repositories or chat | Rules in 06-ai-modules-specification.md section 4: data blocks, no tools, schema validation, no AI output sets any status or score, plain-text rendering |
| T12 | AI cost abuse | Per-user daily quota; input size limits; caching; monthly spend alert; kill switch via configuration |
| T13 | Admin abuse or compromise | Every admin action writes the append-only audit log with the actor; admin accounts created only by command line; strong password and, if time allows, a second factor; admins cannot edit or delete audit rows; destructive actions require a reason |
| T14 | Unwanted exposure of student data to recruiters | Profiles private by default; recruiters must be approved; recruiters see only public profiles; consent changes are logged; search results omit email |
| T15 | Plagiarism between students | Similarity detection; pre-review; reviewer judgement; appeals; revocation |
| T16 | Denial of service on the public page | Rate limit per IP; lightweight page; database indexes on `qr_token` and `verification_id`; hosting-level protection if available |
| T17 | Leaked secrets | Environment variables only; `.env` in `.gitignore`; secret scanning in CI; rotate any key that was ever committed |
| T19 | Admin removes a project unfairly, or a company is hurt by false reports | Removal needs a reason, writes the audit log, and the company sees the reason; reports only open a flag and never remove anything automatically; trust score penalty is logged |
| T20 | GitHub data is fake or belongs to someone else (a student links another person's username) | Labelled "self-linked, not verified"; GitHub data never appears on the verification page and never counts toward XP, badges or match experience; only public data is read; saved skills get source `self` |
| T21 | Server-side request abuse through the GitHub link feature | The server builds the URL itself from a validated username (letters, digits, hyphen, up to 39 characters); no user-supplied URL is fetched; fixed host `api.github.com`; timeout and size limits |
| T18 | Supply chain (malicious dependency) | Lockfiles; dependency audit in CI; review new dependencies; update regularly |

## 3. Authentication and sessions

- Passwords: Argon2id with library defaults at minimum. Never log or return a hash.
- Access token: JWT, 15 minutes, held in memory in the browser (not local storage). Contains user id, role and token id only.
- Refresh token: random value, stored hashed in `refresh_tokens`, delivered as an HttpOnly, Secure, SameSite=Lax cookie, 14 days, rotated on each use. Reuse of an old refresh token revokes the whole family.
- Password change or reset: revoke all refresh tokens.
- Email verification and password reset links: single use, expire in 1 hour (reset) and 24 hours (verification), stored hashed.
- Login errors never say whether the email exists.
- Lock out repeated failures progressively (for example, 5 attempts then a growing delay).

## 4. Authorization matrix

Y = allowed, O = own records only, P = only for projects of own company, A = approved accounts only, - = never.

| Resource and action | Student | Company | Recruiter | Admin | Public |
|---|---|---|---|---|---|
| View own profile | O | - | O | Y | - |
| Edit own profile | O | - | O | - | - |
| Browse open projects | Y | Y | Y | Y | - |
| Create or publish project | - | A, P | - | - | - |
| Apply to project | Y | - | - | - | - |
| See applicants | - | P | - | Y | - |
| Select or reject applicant | - | P | - | - | - |
| Post check-in | O | - | - | - | - |
| Review check-in | - | P | - | - | - |
| Submit work | O | - | - | - | - |
| See similarity report details | - | - | - | Y | - |
| See similarity label only | - | P | - | Y | - |
| Evaluate submission | - | P (reviewer) | - | - | - |
| File an appeal | O | - | - | - | - |
| Resolve an appeal | - | - | - | Y | - |
| Download certificate PDF | O | P | - | Y | - |
| Request revocation | - | P | - | - | - |
| Revoke certificate | - | - | - | Y | - |
| Search public students | - | - | A | Y | - |
| Open a student's portfolio | O | - | A (public only) | Y | - |
| Compare applicants | - | P | - | - | - |
| Add or tick tasks in a milestone | O (own application) | P (company tasks, before first selection) | - | - | - |
| Link GitHub and run analysis | O | - | - | - | - |
| Report a project | Y | Y | Y | - | - |
| Remove a project | - | - | - | Y | - |
| View platform statistics | - | - | - | Y | - |
| View audit log | - | - | - | Y | - |
| Approve companies or recruiters | - | - | - | Y | - |
| View verification page | Y | Y | Y | Y | Y |

Implement the matrix as data (a table in code) and test every cell.

## 5. Data protection in the application

- Validate all input on the server with strict schemas; reject unknown fields.
- Return explicit response models, never raw database rows.
- Encrypt in transit (HTTPS only, HSTS). Encrypt database and file storage at rest using the host's built-in option.
- Never put personal data in URLs, logs or error messages. Log request ID, user ID and route, not bodies.
- Security headers: Content-Security-Policy, X-Content-Type-Options, Referrer-Policy, frame protection.
- Backups: encrypted, tested by restoring once before the demo.
- Separate environments: development, demo and production use different databases and keys. Never copy real student data into development.

## 6. Admin safeguards

- Every approve, reject, suspend, revoke and appeal decision requires a reason and writes the audit log in the same transaction.
- The audit log is append-only at the database level.
- Two-person rule for revocation is recommended if more than one admin exists: one proposes, another confirms (optional for a college demo, but mention it in the report).
- Admin routes sit under `/admin` and require the admin role on every call, not only in the interface.

## 7. Privacy by design

| Principle | How the product follows it |
|---|---|
| Private by default | `is_public` is false until the student turns it on |
| Student controls their name | Full name or initials on the verification page |
| Minimum data | Recruiter search results exclude email; AI prompts include only what the feature needs |
| Transparency | A plain-language screen shows what is public, what recruiters can see and what the AI processes |
| Consent record | Consent changes write `consent_log` rows |
| Right to export | `POST /students/me/export` returns the student's data |
| Right to delete | Account deletion anonymises the account (02-database-schema.md section 9) |
| Retention | AI logs 90 days, lookups 30 days, tokens until expiry, audit log kept |

**Data inventory (what you store)**

| Data | Where | Who can see it |
|---|---|---|
| Email, password hash | `users` | The user (email), nobody (hash) |
| Name, headline, bio, college, graduation year, GitHub username | `student_profiles` | Student; recruiters if public; verification page shows name or initials |
| Resume file and parsed data | Object storage, `resume_parsed` | Student only |
| Skills and proficiency | `student_skills` | Student; recruiters if public |
| Applications, check-ins, submissions | Work tables | Student and the project's company |
| Evaluations | `evaluations` | Student and company; only `public_summary` is public |
| Similarity reports | `submissions.similarity_report` | Admin |
| AI logs | `ai_logs` | Admin (for audit); not shown to other users |

## 8. What must never appear on the public verification page

Email address, phone number, internal IDs, private feedback, rubric scores, AI output, similarity data, other applicants, the student's resume. The `v_public_verification` view contains only the allowed fields; the API reads that view and nothing else for public routes.

## 9. Legal and compliance items to check

This project stores personal data of students, and possibly of people under 18 if your college has such students. Before real users or real data:

1. **Data protection law.** Look up the current requirements of the data protection law that applies where your users live. For India, check the status and rules of the Digital Personal Data Protection Act, 2023 as they stand now; this document does not state them. Typical duties include a clear notice, consent, purpose limits, a way to withdraw consent, correction and erasure, and breach handling.
2. **Minors.** If anyone under 18 could register, check the rules for consent. The simplest approach for a college project is to require students to confirm they are 18 or older, or to run the pilot only with enrolled college students.
3. **Terms and notice.** Publish a short privacy notice and terms. They should state that certificates are platform records, not employment experience, and explain revocation.
4. **AI disclosure.** Tell users which features use AI, what data they send, and that AI output is a draft.
5. **Third-party providers.** If resumes or code are sent to an AI provider, check the provider's data handling terms and say so in your notice. Prefer settings that do not use your data for training.
6. **College policy.** Ask your college whether a student-data project needs approval.

For the report, it is enough to show that you identified these and what you did about each.

## 10. Incident response (one page)

1. **Detect:** error tracking, alerts on login failures, unusual lookup patterns, AI spend alerts.
2. **Contain:** disable the affected route or feature with a configuration flag; revoke affected tokens; rotate exposed keys.
3. **Assess:** what data, which users, since when (the audit log and request logs help).
4. **Fix and restore:** patch, redeploy, restore from backup if data was altered.
5. **Notify:** tell affected users and, where the law requires, the authority. Check the rules for timing.
6. **Learn:** write what happened and the change you made.

## 11. Pre-demo security checklist

- [ ] HTTPS everywhere; `COOKIE_SECURE=true`
- [ ] No secrets in the repository (run a secret scan)
- [ ] Default and seed passwords changed or seed data removed in the demo environment
- [ ] Every cell of the authorization matrix tested
- [ ] Rate limits working on login and public verification
- [ ] Revoked certificate shows Revoked immediately with no caching
- [ ] Upload limits and type checks tested with a wrong file type and an oversized file
- [ ] Injection test inputs run against every AI feature
- [ ] Database backup restored once successfully
- [ ] Privacy notice and terms pages exist and are linked from sign-up
