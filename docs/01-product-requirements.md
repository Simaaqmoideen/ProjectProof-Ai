# ProjectProof AI: Product Requirements Document (PRD)

Status: draft v0.2. This is the source of truth for what the product must do. Other documents implement it.

v0.2 adds the items that the Major project section requires and v0.1 had missed or left as stretch. They are marked **(v2)** in the Tier column. `11-traceability-and-changes.md` lists every change.

## 1. Overview

ProjectProof AI is a platform where **companies post real projects**, **students complete them**, and **recruiters verify the result** with a unique verification ID and QR code. A verification page shows the project, company, student, status, evaluation and demonstrated skills, read live from the database.

**The problem.** Students list projects on resumes that nobody can check, and recruiters have no fast way to tell real work from claims. Existing portfolio and certificate sites rely on self-declared information.

**The idea.** Tie every record to a company that was approved by an admin and to a human evaluation, then make the record checkable by anyone in seconds.

**Positioning.** XP, levels and badges are platform metrics that motivate students. They are not the proof. The proof is the **verified project history**: each project with its company, evaluation and verification ID. Recruiters see verified projects first, and XP second (see FR-REC-4 and BR-11).

**What a certificate is.** A platform verification record that a project was completed on ProjectProof AI. It is **not** formal employment experience, and every certificate and verification page says so.

## 2. Goals and non-goals

**Goals**
1. A complete, reliable loop: company posts project, student applies, company selects, student completes, company evaluates, certificate and verification page are issued.
2. Records that are hard to fake and easy to check, including revocation.
3. AI that helps people decide faster but never makes a decision on its own.
4. A system a small team can build, test and demo in one semester.

**Non-goals (version 1)**
- Payments, stipends or contracts between companies and students.
- Real-time chat between users (the AI mentor is separate).
- Native mobile apps (the web app must work well on a phone).
- Proving employability or replacing formal internships.
- Automated hiring decisions of any kind.

## 3. Users

| Role | Who | Main goals |
|---|---|---|
| Student | College student building experience | Find a fitting project, finish it, hold proof they can share |
| Company | Startup, local business or college placement cell | Post projects, pick candidates, evaluate work, issue proof |
| Recruiter | Hiring person at an organization | Find students by verified evidence, check records fast |
| Admin | Platform operator (faculty, project team) | Approve companies and recruiters, handle flags, appeals and revocations |
| Public visitor | Anyone with a QR code or ID | Confirm a record is genuine, with no account |

## 4. Scope tiers

Every requirement below carries a tier. Build in this order.

- **Core:** must ship. Together these form the complete loop.
- **AI highlight:** pick 3 or 4 to build well and demo.
- **Stretch:** only if time remains.

v2 promoted these from Stretch because the Major project section names them: GitHub integration, skill-gap analysis, applicant comparison, the recruiter module and platform statistics. Because the Core list is now longer, the cut order in `09-project-plan-and-demo.md` was updated.

## 5. Functional requirements

### 5.1 Accounts and access
| ID | Requirement | Tier |
|---|---|---|
| FR-AUTH-1 | Users register as student, company or recruiter with email and password | Core |
| FR-AUTH-2 | Email must be verified before the user can perform any action beyond viewing their own profile | Core |
| FR-AUTH-3 | Login, logout and silent token refresh | Core |
| FR-AUTH-4 | Password reset by emailed one-time link | Core |
| FR-AUTH-5 | Every route enforces role-based access; a user can only reach their own data | Core |
| FR-AUTH-6 | Admin accounts are created by seed script or command line, never by public sign-up | Core |

### 5.2 Company and recruiter approval
| ID | Requirement | Tier |
|---|---|---|
| FR-ORG-1 | A company registers with name, website, work email and a registration document | Core |
| FR-ORG-2 | A company stays `pending` until an admin approves it; pending companies cannot publish projects | Core |
| FR-ORG-3 | The admin queue shows automatic checks: work email domain matches website, document uploaded, no other active company on the same domain | Core |
| FR-ORG-4 | Each company has a trust score (0 to 100) shown to admins and to the company; see business rule BR-6 | Core |
| FR-ORG-5 | A new company may have at most 2 open projects until it has completed 3 evaluations | Core |
| FR-ORG-6 | A recruiter registers with organization and work email and cannot search until an admin approves | Core |
| FR-ORG-7 | Admins can suspend a company or recruiter. Suspending a company closes its open projects. Existing certificates stay valid unless separately revoked | Core |

### 5.3 Student profile
| ID | Requirement | Tier |
|---|---|---|
| FR-STU-1 | Profile with name, headline, bio, college, graduation year, GitHub username | Core |
| FR-STU-2 | Skills list with proficiency 1 to 5; each skill records its source (self, resume, verified project) | Core |
| FR-STU-3 | Resume upload (PDF, up to 5 MB) | Core |
| FR-STU-4 | AI resume analysis proposes skills, education, projects and certifications; the student accepts or edits each suggestion before anything is saved | AI highlight |
| FR-STU-5 | Public profile toggle, off by default. Only public profiles appear to recruiters | Core |
| FR-STU-6 | Student chooses whether the verification page shows their full name or initials | Core |
| FR-STU-7 | Dashboard: next action, active projects, XP, level, badges, recommended projects (FR-APP-10) | Core |
| FR-STU-8 | GitHub integration: the student links a GitHub username; the platform reads the public profile and public repositories through GitHub's public API (read-only, no password) and shows languages, repository count and recent activity. Labelled "self-linked, not verified" because linking by username does not prove ownership | Core (v2) |
| FR-STU-9 | Student can export their data and delete their account (see 07-security-and-privacy.md) | Core |
| FR-STU-10 | Student portfolio page: the student's verified project history, newest first, each with company, skills, public summary, completion date, XP and a link to its verification page. Revoked records stay listed with a Revoked label. The same page is what a recruiter sees when the profile is public | Core (v2) |
| FR-STU-11 | AI repo analysis: from the linked GitHub data the AI proposes skills and a short summary; the student accepts or edits each item before it is saved. Never shown on the verification page | AI highlight (v2) |

### 5.4 Projects
| ID | Requirement | Tier |
|---|---|---|
| FR-PRJ-1 | An approved company creates a project: title, description, category, difficulty, duration in days, required skills, number of students to select, application deadline | Core |
| FR-PRJ-2 | A project has 1 to 8 milestones, each with a title and a due day offset from the start date | Core |
| FR-PRJ-3 | Maximum XP is computed from difficulty and duration (BR-1). Companies cannot set it | Core |
| FR-PRJ-4 | Publishing moves a project from `draft` to `open`; only approved companies can publish | Core |
| FR-PRJ-5 | AI project brief generator turns a rough idea into a structured draft the company edits before publishing | AI highlight |
| FR-PRJ-6 | After any student is selected, the title, skills, difficulty, duration and milestones are locked | Core |
| FR-PRJ-7 | A company can close a project (no new applications) or cancel it (applicants are notified) | Core |
| FR-PRJ-8 | XP allocation: a company influences a project's XP only through difficulty and duration, and sees the resulting `xp_max` read-only. No one types an XP number. An admin can change the formula constants in configuration (decision D-1) | Core (v2) |

### 5.5 Applications and selection
| ID | Requirement | Tier |
|---|---|---|
| FR-APP-1 | A student applies once per open project, with an optional cover note | Core |
| FR-APP-2 | A student sees all of their applications and their statuses | Core |
| FR-APP-3 | A match score from 0 to 100 with a four-part breakdown is shown to the student and the company (BR-3) | AI highlight |
| FR-APP-4 | A company can filter and sort applicants by match score, skills, XP and verified projects | Core |
| FR-APP-5 | AI ranking adds a plain-language explanation per applicant, labelled as an AI draft | AI highlight |
| FR-APP-6 | A company compares 2 or 3 applicants side by side: skills, match breakdown, XP, verified projects, GitHub summary, cover note | Core (v2) |
| FR-APP-7 | Selecting an applicant moves the application to `in_progress`, sets start and due dates, and notifies the student. Unselected applicants are notified when the project closes | Core |
| FR-APP-8 | A student can withdraw before submitting; withdrawn work earns nothing | Core |
| FR-APP-9 | Skill-gap analysis for a target project: the missing skills come from the match score (deterministic); AI adds a suggested learning order and one learning resource type per skill, labelled as a draft | AI highlight (v2) |
| FR-APP-10 | Recommendation engine: the student's dashboard lists open projects ranked by a recommendation score (BR-10), each with a one-line reason such as "matches 4 of 5 skills" or "stretch: 2 skills to learn". Projects the student already applied to, and projects when the student already has 3 active ones, are not recommended | Core (v2) |

### 5.6 Workspace
| ID | Requirement | Tier |
|---|---|---|
| FR-WRK-1 | A selected student sees the milestone list with due dates computed from the start date | Core |
| FR-WRK-2 | The student posts a check-in per milestone with a note and an optional evidence link | Core |
| FR-WRK-3 | The company marks each check-in `accepted` or `needs_work` | Core |
| FR-WRK-4 | Overdue milestones are flagged and both sides are notified | Core |
| FR-WRK-5 | AI mentor gives hints without writing the solution; usage is logged and visible to the company | Stretch |
| FR-WRK-6 | Team projects with per-member contribution tracking | Stretch (not supported by the version 1 schema) |
| FR-WRK-7 | Tasks inside milestones: when creating a project the company may add 0 to 10 tasks under each milestone (title, optional description). A selected student marks each task `todo`, `in_progress` or `done`; the company sees task progress per milestone. Company tasks are locked after the first student is selected | Core (v2) |
| FR-WRK-8 | Task creation by the student: a selected student may add personal sub-tasks under any milestone of their own application. These are private to that application, visible to the company as the student's own, and never required for completion | Core (v2) |

### 5.7 Submission and evaluation
| ID | Requirement | Tier |
|---|---|---|
| FR-EVL-1 | The student submits a repository URL and/or a file. Up to 3 versions per application | Core |
| FR-EVL-2 | A similarity check runs on every submission, stores a report, and opens an admin flag when the score is high (see 06-ai-modules-specification.md) | AI highlight |
| FR-EVL-3 | AI pre-review compares the submission with the project's task checklist and shows met, not met or unclear per item | AI highlight |
| FR-EVL-4 | A company reviewer records rubric scores, an overall score from 0 to 100, written feedback, a short public summary, and a decision: `approved`, `changes_requested` or `rejected` | Core |
| FR-EVL-5 | AI feedback drafter turns the reviewer's notes into structured feedback; the reviewer edits and sends | Stretch |
| FR-EVL-6 | On `changes_requested`, the student may resubmit a new version before the project's due date plus 3 days | Core |
| FR-EVL-7 | A student can appeal a decision within 7 days. An admin upholds or overturns it | Core |

### 5.8 Certificates and verification
| ID | Requirement | Tier |
|---|---|---|
| FR-CRT-1 | When an evaluation is `approved`, one transaction completes the application, creates the certificate with a verification ID, QR token and content hash, and records XP | Core |
| FR-CRT-2 | The student can download a certificate PDF showing name, project, company, duration, skills, verification ID, QR code and the disclaimer | Core |
| FR-CRT-3 | A public page, reachable by QR token or by verification ID, shows the record read live from the database, including a clear Revoked state | Core |
| FR-CRT-4 | A company can request revocation with a reason; only an admin can revoke | Core |
| FR-CRT-5 | Revoking a certificate reverses its XP and recalculates the student's badges | Core |
| FR-CRT-6 | Lookups on the public page are rate limited per IP address | Core |

### 5.9 Rewards
| ID | Requirement | Tier |
|---|---|---|
| FR-RWD-1 | XP is calculated on the server by formula (BR-1); no endpoint accepts an XP value from a client | Core |
| FR-RWD-2 | Levels come from XP thresholds (BR-4) | Core |
| FR-RWD-3 | Badges are awarded from verified completions only (BR-5) | Core |
| FR-RWD-4 | Resume-to-project rewriter produces resume bullets from a verified record | Stretch |
| FR-RWD-5 | Mock interview bot based on the student's verified projects | Stretch |

### 5.10 Recruiter module
| ID | Requirement | Tier |
|---|---|---|
| FR-REC-1 | An approved recruiter filters public students by skills, minimum XP, minimum verified projects and verification status | Core (v2) |
| FR-REC-2 | A recruiter opens a student's portfolio (FR-STU-10), each project linked to its verification page | Core (v2) |
| FR-REC-3 | Plain-text search is translated into filters the recruiter can see and edit | AI highlight (v2) |
| FR-REC-4 | Recruiter results are sorted by number of verified projects first and XP second, and each result shows verified project count before XP | Core (v2) |

### 5.11 Admin
| ID | Requirement | Tier |
|---|---|---|
| FR-ADM-1 | Approval queues for companies and recruiters, with automatic check results | Core |
| FR-ADM-2 | Flag queue for similarity, anomaly and manual flags | Core |
| FR-ADM-3 | Appeals queue | Core |
| FR-ADM-4 | Revocation tool with required reason category | Core |
| FR-ADM-5 | Read-only audit log with filters by actor, action and entity | Core |
| FR-ADM-6 | Suspend and reactivate any user | Core |
| FR-ADM-7 | Anomaly detection rules (see 06-ai-modules-specification.md) | Stretch |
| FR-ADM-8 | An admin can remove an inappropriate project. A reason is required. The project becomes `removed` and disappears from browse and search. Applicants in `applied` are rejected and those `in_progress` are withdrawn, both with a stored reason and no penalty to the student, and all are notified. Existing certificates from the project stay valid unless separately revoked. The action is audited and lowers the company's trust score (BR-6) | Core (v2) |
| FR-ADM-9 | A student, recruiter or company can report a project; the report opens a manual flag in the admin queue | Core (v2) |

### 5.12 Notifications, analytics, AI rules
| ID | Requirement | Tier |
|---|---|---|
| FR-NTF-1 | In-app notifications for: application received, selected, rejected, milestone due or overdue, submission received, evaluation done, appeal outcome, certificate issued or revoked | Core |
| FR-NTF-2 | The same events are emailed for selection, evaluation, certificate and revocation | Core |
| FR-ANA-1 | Student statistics: XP, projects, verified projects, completion rate, applications, accepted and completed projects | Core |
| FR-ANA-2 | Company statistics: projects posted, students selected, projects completed, active projects, pending reviews | Core |
| FR-ANA-3 | Platform statistics for admins: active students, approved companies and recruiters, open and removed projects, active and completed applications, certificates issued and revoked, open flags and appeals, verification lookups in 30 days | Core (v2) |
| FR-AI-1 | Every AI output is labelled "AI draft", carries a confidence level, is logged, and is applied only after a person accepts it | Core |
| FR-AI-2 | Each user has a daily AI usage limit | Core |
| FR-AI-3 | If the AI service fails, the feature shows a clear message and the manual path still works | Core |
| FR-AI-4 | AI output never appears on the public verification page | Core |

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Public verification page responds in under 1 second at the 95th percentile on the demo deployment |
| NFR-2 | The application works on screens from 360 px wide, and the verification page is usable one-handed on a phone |
| NFR-3 | Target WCAG 2.1 AA: keyboard operable, visible focus, contrast, text alternatives, status never conveyed by color alone |
| NFR-4 | All state-changing actions by admins and companies write an audit log entry |
| NFR-5 | Nightly database backup; documented restore steps |
| NFR-6 | Secrets only in environment variables; no secrets in the repository |
| NFR-7 | Automated tests for all business rules in section 7 (see 08-test-plan.md) |
| NFR-8 | Structured logs with a request ID on every request |
| NFR-9 | English only in version 1; all user-facing text kept in one place so translation is possible later |
| NFR-10 | Modern evergreen browsers (latest two versions of Chrome, Edge, Firefox, Safari) |

## 7. Business rules

**BR-1: XP.** `XP = round(min(cap, base_per_day × duration_days × difficulty_multiplier × evaluation_multiplier))`
- base per day: 6; cap: 200 per project
- difficulty multiplier: beginner 1.0, intermediate 1.5, advanced 2.0
- **Decision D-1 (v2): XP is formula-only.** The Major specification speaks of a company allocating XP. This design keeps companies from typing XP, because a company that can set XP can hand out any amount to friends. A company still decides the XP indirectly by choosing difficulty and duration. If your guide insists on company-set XP, the safe alternative is: the company picks a value from 50% to 100% of the computed `xp_max`, never above it, and the choice is audited. Change this in FR-PRJ-8 and BR-1 together
- evaluation multiplier from the overall score: 60 to 74 is 1.0, 75 to 89 is 1.1, 90 to 100 is 1.2. A score below 60 cannot be `approved`
- The project card shows `xp_max`, computed with multiplier 1.2. Example: intermediate, 14 days: 6 × 14 × 1.5 × 1.2 = 151.2, shown as 151
- These numbers are starting values; keep them in one configuration file

**BR-2: Certificate integrity.** One certificate per application. Fields are immutable except revocation. A revoked certificate is never reinstated; a new evaluation issues a new one. Enforced in the database (see schema triggers).

**BR-3: Match score.** `match = 0.5 × skills + 0.2 × difficulty_fit + 0.2 × experience + 0.1 × availability`, each part 0 to 100. Part definitions are in 06-ai-modules-specification.md. Weights live in configuration.

**BR-4: Levels.** 1 Starter 0 XP, 2 Contributor 200, 3 Builder 400, 4 Practitioner 600, 5 Specialist 900, 6 Expert 1300. Stored in the `levels` table.

**BR-5: Badges.** First project: 1 verified completion. Fast learner: 3. Developer: 5 in the development category. Consistent contributor: completions from 3 different companies. Project champion: 10. Only certificates with status `issued` count.

**BR-6: Company trust score.** Starts at 50 when approved. Plus 5 for each evaluation completed within 5 days (max +30), minus 10 for each evaluation overturned on appeal, minus 20 for each certificate revoked for company error or fraud, plus 10 once the company has 5 completed projects. Minus 15 for each project an admin removes as inappropriate (v2). Clamped to 0 to 100. Below 30, new project publishing needs admin approval.

**BR-7: Appeals.** Allowed within 7 days of an evaluation. One open appeal per evaluation. An admin decides; the decision and note are logged.

**BR-8: Visibility.** Student profiles are private by default. Recruiters see only public profiles. A verification page is visible to anyone with the link, so it shows only what the student agreed to show.

**BR-9: AI boundary.** AI may draft, rank, flag and explain. It may not approve, reject, select, revoke, issue or award anything.

**BR-10: Recommendation score (v2).** `recommend = match score + 10 if the project is in a category the student has completed + 5 if the student lacks 1 or 2 required skills (a good stretch)`, capped at 100. Only `open` projects the student has not applied to are candidates. Computed by code, never by the LLM. The reason text is built from the score parts. Weights live in configuration.

**BR-11: Verified history over XP (v2).** Wherever people are ranked or shown side by side (recruiter results, applicant lists), the verified project count is shown and sorted before XP. XP never appears on the public verification page.

## 8. Success measures (for the demo and report)

- The full loop runs end to end without manual database edits.
- A revoked certificate shows Revoked immediately on the public page.
- Similarity detection catches the planted copies in the test set (see 08-test-plan.md).
- Match scores agree with a hand-labelled set at the rate you report.
- A new person can understand the verification page in under 10 seconds (informal test with 5 people).

## 9. Assumptions and open questions

Assumptions: a small team, one semester, a single deployment, English only, a college admin acting as platform admin.

Open questions to settle before building:
1. Team size and deadline. This decides how many AI highlights to build.
2. Hosting budget and where the demo will run (laptop, cloud, college server).
3. Which LLM provider and what monthly spend limit.
4. Whether the placement cell will act as the first company ("college-sponsored projects").
5. Legal review: data protection duties for storing student data (check the current requirements; this document does not cover them).
6. Whether recruiters need approval by domain only or by manual review.
7. Decision D-1: formula-only XP (recommended) or company-chosen XP within a limit (see BR-1).

## 10. Glossary

| Term | Meaning |
|---|---|
| Verification ID | Human-readable ID such as `EXP-2026-AB12-9821` |
| QR token | Long random string used in the QR link; harder to guess than the verification ID |
| Certificate | Platform verification record of a completed, approved project |
| Evaluation | A company reviewer's scored decision on a submission |
| Flag | An item sent to admins for review: similarity, anomaly or manual |
| AI draft | Any AI-produced suggestion; never final until a person accepts it |
| XP | Experience points awarded only from verified completions |
