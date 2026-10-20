# ProjectProof AI: Test Plan

The goal is simple: the full loop works, the proof records cannot be faked or silently changed, and AI features behave safely. Test cases carry IDs so the report can link each requirement to evidence.

## 1. Approach

| Level | What it covers | Tools | When |
|---|---|---|---|
| Database tests | The rules in `schema.sql` (certificate triggers, append-only tables, constraints) | pytest against a real PostgreSQL container | Every pull request |
| Unit tests | XP formula, match score parts, similarity algorithm, state transitions, ID generation | pytest, Vitest | Every pull request |
| API tests | Each route, each role, each state | pytest with the FastAPI test client | Every pull request |
| End-to-end tests | The whole loop in a browser | Playwright | Before each milestone and before the demo |
| AI evaluation | Quality, validity and injection resistance of AI features | Scripts over fixed test sets (see 06, section 8) | After each prompt change |
| Security tests | Authorization matrix, uploads, rate limits | pytest, manual checks | Before the demo |
| Accessibility checks | Keyboard, contrast, screen reader basics | axe checks in Playwright, manual pass | Before the demo |
| Usability test | Can a stranger read the verification page in 10 seconds | 5 people, informal | Once |

Rules: use a real PostgreSQL in tests (not SQLite), because the schema relies on triggers and partial indexes. Never call a real AI provider in automated tests; use a fake `LLMClient` that returns fixed JSON, and keep a small separate set of live AI evaluations you run by hand.

## 2. Test data

The seed script creates: 1 admin; companies "Nova Labs" (approved), "Keystone Soft" (approved), "BrightWave Tech" (pending, free email); 5 students with different skills; 6 open projects across difficulties and categories; 3 completed projects with certificates, one of them revoked; 2 similarity test pairs; 1 company with unusual patterns for anomaly tests.

## 3. Test cases

Priority: P1 must pass before any demo, P2 should pass, P3 nice to have.

### 3.1 Accounts and access
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-AUTH-01 | Register student, company, recruiter | Accounts created unverified | FR-AUTH-1 | P1 |
| T-AUTH-02 | Act before verifying email | `403` | FR-AUTH-2 | P1 |
| T-AUTH-03 | Wrong password five times | Rate limited; message does not reveal whether the email exists | FR-AUTH-3 | P1 |
| T-AUTH-04 | Expired access token with valid refresh cookie | New access token issued; old refresh token rotated | FR-AUTH-3 | P2 |
| T-AUTH-05 | Reuse of a rotated refresh token | Token family revoked | FR-AUTH-3 | P2 |
| T-AUTH-06 | Public sign-up with `role=admin` | Rejected | FR-AUTH-6 | P1 |
| T-AUTH-07 | Every cell of the authorization matrix (generated test) | Matches 07-security-and-privacy.md section 4 | FR-AUTH-5 | P1 |
| T-AUTH-08 | Student requests another student's application | `404` | FR-AUTH-5 | P1 |

### 3.2 Company and recruiter approval
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-ORG-01 | Pending company tries to publish | `403` | FR-ORG-2 | P1 |
| T-ORG-02 | Admin approves; action written to audit log | Status approved; audit row with actor | FR-ORG-2, NFR-4 | P1 |
| T-ORG-03 | Second company registers with an active company's domain | Rejected | FR-ORG-3 | P1 |
| T-ORG-04 | Email domain mismatch | Check shows mismatch in admin queue | FR-ORG-3 | P2 |
| T-ORG-05 | New company publishes a third project | Blocked with explanation | FR-ORG-5 | P2 |
| T-ORG-06 | Unapproved recruiter searches | `403` | FR-ORG-6 | P1 |
| T-ORG-07 | Suspend company | Open projects close; existing certificates stay valid | FR-ORG-7 | P2 |

### 3.3 Projects, applications, workspace
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-PRJ-01 | Create project with a client-supplied `xp_max` | Rejected | FR-PRJ-3 | P1 |
| T-PRJ-02 | XP max for intermediate, 14 days | 151 | BR-1 | P1 |
| T-PRJ-03 | Edit locked field after selection | `409` | FR-PRJ-6 | P1 |
| T-APP-01 | Apply twice to the same project | Second rejected | FR-APP-1 | P1 |
| T-APP-02 | Apply to a closed project | Rejected | FR-APP-1 | P1 |
| T-APP-03 | Select more students than `max_selected` (two reviewers at once) | Limit holds | FR-APP-7 | P1 |
| T-APP-04 | Student already has 3 active projects applies | Blocked with explanation | 05 section 3.3 | P2 |
| T-APP-05 | Match score parts (skills, difficulty, experience, availability) for fixed fixtures | Exact expected numbers | BR-3 | P1 |
| T-WRK-01 | Due dates equal start date plus offset | Correct | FR-WRK-1 | P1 |
| T-WRK-02 | Student checks in on another student's application | `404` | FR-WRK-2 | P1 |
| T-WRK-03 | Overdue job notifies both sides once | Single notification each | FR-WRK-4 | P2 |

### 3.4 Submission and evaluation
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-EVL-01 | Fourth submission version | Rejected | FR-EVL-1 | P2 |
| T-EVL-02 | Oversized file; wrong file type with a `.pdf` name | Rejected with `413` or `400` | FR-EVL-1 | P1 |
| T-EVL-03 | Approve with overall score 55 | `409` | FR-EVL-4 | P1 |
| T-EVL-04 | Reviewer from another company evaluates | `404` | FR-EVL-4 | P1 |
| T-EVL-05 | Changes requested, student resubmits within window | Back to submitted | FR-EVL-6 | P1 |
| T-EVL-06 | Resubmission after the window | Application failed by scheduler | FR-EVL-6 | P2 |
| T-EVL-07 | Appeal on day 6, appeal on day 8 | First accepted, second rejected | BR-7 | P1 |
| T-EVL-08 | Second open appeal on the same evaluation | Rejected | BR-7 | P2 |

### 3.5 Certificates and verification (the most important group)
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-CRT-01 | Approve evaluation | One transaction: application completed, certificate, XP event, badges, audit, notifications | FR-CRT-1 | P1 |
| T-CRT-02 | Approve twice (double click, retry with same key) | One certificate only | FR-CRT-1 | P1 |
| T-CRT-03 | Force a failure after XP insert | Whole transaction rolls back; no partial records | FR-CRT-1 | P1 |
| T-CRT-04 | Verification ID format and uniqueness over 10,000 generated IDs | All match the pattern; collisions handled | 02 section 8 | P1 |
| T-CRT-05 | QR token length and randomness | At least 128 bits; not derivable from the ID | 02 section 8 | P1 |
| T-CRT-06 | Public page by QR token | Correct live data; header `Cache-Control: no-store` | FR-CRT-3 | P1 |
| T-CRT-07 | Public page after revocation | Shows Revoked immediately; reason category only | FR-CRT-3 | P1 |
| T-CRT-08 | Public page for unknown token and unknown ID | Same response shape and similar timing | FR-CRT-3, T3 | P1 |
| T-CRT-09 | Public response contents | No email, private feedback, rubric, AI output or internal IDs | 07 section 8 | P1 |
| T-CRT-10 | Student with initials preference | Page shows initials | FR-STU-6 | P2 |
| T-CRT-11 | Direct database edit of `xp_awarded`, delete, un-revoke | All rejected by triggers | BR-2 | P1 |
| T-CRT-12 | Company requests revocation | Opens a flag; certificate unchanged | FR-CRT-4 | P1 |
| T-CRT-13 | Non-admin calls revoke | `403` | FR-CRT-4 | P1 |
| T-CRT-14 | Admin revokes | Negative XP event; badges recalculated; audit; notifications | FR-CRT-5 | P1 |
| T-CRT-15 | 40 lookups in a minute from one address | Rate limited after the limit | FR-CRT-6 | P1 |
| T-CRT-16 | PDF contains name, project, company, duration, skills, ID, QR, disclaimer; QR scans to the right page | Correct | FR-CRT-2 | P1 |
| T-CRT-17 | Content hash recomputed from current data | Matches stored hash | 02 section 8 | P2 |

### 3.6 Rewards
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-RWD-01 | XP for scores 59 (cannot approve), 60, 75, 90 | 1.0, 1.0, 1.1, 1.2 multipliers; cap applied | BR-1 | P1 |
| T-RWD-02 | Any client attempt to send XP | Ignored or rejected | FR-RWD-1 | P1 |
| T-RWD-03 | 420 XP | Level 3, 180 XP to level 4 | BR-4 | P1 |
| T-RWD-04 | Badge thresholds at 1, 3, 5 development, 3 companies, 10 | Awarded exactly at the threshold | BR-5 | P1 |
| T-RWD-05 | Revocation drops a student below a badge threshold | Badge removed | FR-CRT-5 | P1 |

### 3.7 Recruiter and admin
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-REC-01 | Search returns private profiles | Never | BR-8 | P1 |
| T-REC-02 | Student turns public off | Disappears from search at once | FR-STU-5 | P1 |
| T-REC-03 | Plain-text query returns unknown filter fields or SQL | Rejected by validation | FR-REC-3 | P1 |
| T-ADM-01 | Audit log update or delete via SQL | Rejected | FR-ADM-5 | P1 |
| T-ADM-02 | High similarity opens a flag; company sees "review pending" only | Correct | FR-EVL-2 | P1 |
| T-ADM-03 | Appeal overturned reopens the submission | Correct | FR-EVL-7 | P2 |

### 3.7a Version 2 additions (portfolio, tasks, GitHub, recommendations, removal, comparison, statistics)
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-STU-01 | Portfolio lists issued and revoked certificates newest first; revoked one is labelled Revoked | Correct | FR-STU-10 | P1 |
| T-STU-02 | Recruiter opens the portfolio of a private profile | `404` | FR-STU-10, BR-8 | P1 |
| T-STU-03 | Link a valid GitHub username (fake GitHub client) | Summary shown with "self-linked, not verified" | FR-STU-8 | P2 |
| T-STU-04 | Link a username with a slash, a space or 40 characters | Rejected by validation; no request leaves the server | FR-STU-8, T21 | P1 |
| T-STU-05 | GitHub API times out or is rate limited | Clear message; rest of profile works | FR-STU-8 | P2 |
| T-STU-06 | GitHub data affects XP, badges or match experience | Never | FR-STU-8, T20 | P1 |
| T-WRK-04 | Company adds 11 tasks to one milestone | Rejected | FR-WRK-7 | P2 |
| T-WRK-05 | Company edits tasks after first selection | `409` | FR-WRK-7 | P1 |
| T-WRK-06 | Student marks a company task done, then back to in progress | Both accepted; completion time set and cleared | FR-WRK-7 | P2 |
| T-WRK-07 | Student adds a personal sub-task; another student tries to tick it | Created; the other student gets `404` | FR-WRK-8 | P1 |
| T-WRK-08 | Student deletes a company task | `409` | FR-WRK-8 | P2 |
| T-WRK-09 | Submit work with unfinished tasks | Allowed (tasks never block) | FR-WRK-7 | P2 |
| T-APP-06 | Compare 2 and 3 applicants; compare 1 or 4; compare applicants of another company's project | Works; rejected; `404` | FR-APP-6 | P2 |
| T-APP-07 | Recommendation score for fixed fixtures (category bonus, stretch bonus, cap at 100) | Exact expected numbers and reason text | BR-10 | P1 |
| T-APP-08 | Recommendations exclude applied projects, removed projects, and everything when the student has 3 active | Correct | FR-APP-10 | P1 |
| T-REC-04 | Recruiter results order: 3 verified and 100 XP before 2 verified and 500 XP | Verified count first | FR-REC-4, BR-11 | P1 |
| T-ADM-04 | Admin removes a project without a reason | `400` | FR-ADM-8 | P1 |
| T-ADM-05 | Admin removes a project that has one applied and one in-progress application | Applied becomes rejected, in-progress becomes withdrawn, both with reason `project_removed`; no XP; notifications created; audit row; trust score minus 15 | FR-ADM-8 | P1 |
| T-ADM-06 | Remove a project that already produced a certificate | Certificate stays issued and verifiable | FR-ADM-8 | P1 |
| T-ADM-07 | Non-admin calls the removal route | `403` | FR-ADM-8 | P1 |
| T-ADM-08 | A student reports a project | Manual flag opens; project stays visible | FR-ADM-9 | P2 |
| T-ADM-09 | Admin statistics match counts computed by hand on the seed data | Equal | FR-ANA-3 | P2 |
| T-AI-V2-01 | Skill-gap model returns a skill that was not in the supplied missing list | Dropped before display | FR-APP-9 | P1 |
| T-AI-V2-02 | GitHub analysis proposes a skill without evidence from the input | Dropped | FR-STU-11 | P1 |
| T-AI-V2-03 | Repository description contains an instruction to change the output | Output unaffected | FR-STU-11, T11 | P1 |

### 3.8 AI behaviour (with a fake client)
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-AI-01 | AI returns invalid JSON twice | `422` with friendly message; manual path works | FR-AI-3 | P1 |
| T-AI-02 | Provider timeout | `503`; underlying action unaffected | FR-AI-3 | P1 |
| T-AI-03 | Daily quota exceeded | `429` | FR-AI-2 | P1 |
| T-AI-04 | Resume analysis returns a skill not in the resume | Item dropped | 06 section 6.1 | P1 |
| T-AI-05 | AI ranking sentence cites a fact not supplied | Replaced by template sentence | 06 section 6.3 | P1 |
| T-AI-06 | Pre-review cites a file that does not exist | Item becomes `unclear` | 06 section 6.4 | P1 |
| T-AI-07 | Any AI route saves to business tables before accept | Never | FR-AI-1 | P1 |
| T-AI-08 | AI text containing HTML or a markdown image | Rendered as plain text | 06 section 4 | P1 |
| T-AI-09 | Verification page response | Contains no AI field | FR-AI-4 | P1 |
| T-AI-10 | Ten injection inputs (resumes, README files, chat messages) | Output unaffected by the injected instruction | 06 section 4 | P1 |
| T-SIM-01 | Identical code; renamed variables; reordered functions; independent solutions | Detected at the thresholds in 06, section 5.2; independent solutions stay low | FR-EVL-2 | P1 |
| T-SIM-02 | Starter template files | Excluded from matching | FR-EVL-2 | P2 |

### 3.9 Non-functional
| ID | Case | Expected | Req | Pri |
|---|---|---|---|---|
| T-NFR-01 | 50 concurrent users on the public page | 95th percentile under 1 second | NFR-1 | P2 |
| T-NFR-02 | 360 px wide screen on every main page | No sideways scrolling; targets at least 44 px | NFR-2 | P1 |
| T-NFR-03 | Keyboard-only run through apply, review and verify | Possible; focus visible | NFR-3 | P1 |
| T-NFR-04 | axe scan of main pages | No serious violations | NFR-3 | P2 |
| T-NFR-05 | Status never conveyed by colour alone | Icon and text always present | NFR-3 | P1 |
| T-NFR-06 | Restore a backup into a new database | App works | NFR-5 | P1 |
| T-NFR-07 | Secret scan on the repository | None found | NFR-6 | P1 |
| T-NFR-08 | Every admin and company state change | Has an audit row | NFR-4 | P1 |

## 4. End-to-end scenarios (Playwright)

1. **Happy path.** Admin approves a company. Company publishes. Student applies. Company selects. Student checks in on every milestone and submits. Reviewer approves. Student sees the certificate. A logged-out browser opens the QR link and sees Verified.
2. **Revocation.** Continue from scenario 1: admin revokes. The same QR link shows Revoked on refresh. XP and badges drop.
3. **Changes requested.** Reviewer requests changes; student resubmits; reviewer approves.
4. **Appeal.** Reviewer rejects; student appeals; admin overturns; reviewer approves.
5. **Fake company.** A company with a free email address is flagged in the admin queue and cannot publish until approved.
6. **Similarity.** Two students submit near-identical code; the second triggers a flag; admin confirms and fails the application.
7. **Recruiter.** Approved recruiter searches, sees verified project counts first, opens a public portfolio, follows a verification link.
8. **Project removal (v2).** A student reports a project; admin removes it with a reason; the project disappears from browse; the applicant sees the notification; a certificate issued earlier from another project of the same company still verifies.
9. **Tasks and recommendations (v2).** A student sees recommended projects with reasons, applies, is selected, ticks company tasks and adds a personal sub-task; the company sees the progress.

## 5. Exit criteria

| Milestone | Must be true |
|---|---|
| Core complete | All P1 tests in sections 3.1 to 3.6, 3.7 and 3.7a (except the AI cases T-AI-V2-xx) pass; scenarios 1 to 3 pass |
| AI highlights complete | All P1 AI tests pass; evaluation numbers recorded for each built feature |
| Demo ready | Every P1 test passes; security checklist done; scenarios 1, 2, 5 rehearsed on the demo environment |

## 6. Defects

Track in the repository's issue tracker. Label by severity: **blocker** (data wrong, security hole, demo cannot run), **major** (feature broken), **minor** (cosmetic). No blocker may be open at a milestone. Each fixed defect gets a test that would have caught it.

## 7. Report evidence to collect

Test case table with pass or fail; screenshots of the two or three most important scenarios; AI evaluation tables from 06, section 8; performance numbers; the list of defects found and fixed; limits you did not test.
