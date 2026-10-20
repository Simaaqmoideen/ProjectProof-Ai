# ProjectProof AI: Traceability and Change Log (version 2)

This file answers two questions: "Is every item of the Major project section covered?" and "What changed from version 1?" Source: the document *ProjectProof Minor and Major Project Specification*, section 2 (Major project) and the Minor vs Major table in section 3.

## 1. What changed in version 2

| # | Change | Where |
|---|---|---|
| 1 | Student portfolio page of verified projects (FR-STU-10) | 01, 02 (`v_student_portfolio`), 04, 05 UC-13, 08 |
| 2 | GitHub integration promoted to Core (FR-STU-8); AI repo analysis added (FR-STU-11) | 01, 02, 03, 04, 05, 06 section 6.9, 07 (T20, T21), 08 |
| 3 | Tasks inside milestones: company tasks (FR-WRK-7) and student sub-tasks (FR-WRK-8) | 01, 02 (`tasks`, `task_progress`), 04, 05 section 3.3a, 08 |
| 4 | Admin removal of inappropriate projects (FR-ADM-8) and project reports (FR-ADM-9) | 01, 02 (`removed` status), 04, 05 UC-12, 07, 08 |
| 5 | Student comparison for companies promoted to Core (FR-APP-6) | 01, 04, 08 |
| 6 | Skill-gap analysis promoted to AI highlight (FR-APP-9) | 01, 04, 06 section 6.8, 08 |
| 7 | Recommendation engine (FR-APP-10, BR-10) | 01, 04, 06 section 5.1a, 08 |
| 8 | Recruiter module promoted to Core (FR-REC-1, 2, 4); plain-text search is an AI highlight (FR-REC-3) | 01, 04, 08, 09 |
| 9 | Platform statistics for admins promoted to Core (FR-ANA-3) | 01, 02 (`v_platform_stats`), 04, 08 |
| 10 | XP allocation decision D-1 written down (FR-PRJ-8) | 01 BR-1, 00-README |
| 11 | Positioning: verified history over XP (BR-11, FR-REC-4) | 01 sections 1 and 7, 10 |
| 12 | Plan, cut order and demo script updated for the longer Core list | 09 |
| 13 | Test plan grew from 82 to 107 cases | 08 |

Database changes in `schema.sql`: project status `removed` with `removed_by`, `removed_at`, `removal_reason` and two check constraints; tables `tasks` and `task_progress` with a trigger; `applications.status_reason`; `student_profiles.github_summary` and `github_analyzed_at`; views `v_student_portfolio` and `v_platform_stats`. The schema was loaded into PostgreSQL 16 and 28 integrity cases passed (02, section 6).

## 2. Major project section: coverage

Legend: **Yes** means a numbered requirement exists. **Changed** means it was missing or stretch in v1. **Different** means the design deliberately differs from the source.

### Advanced student module

| Source item | Requirement | Status |
|---|---|---|
| Advanced profile | FR-STU-1, FR-STU-5, FR-STU-6 | Yes |
| Resume upload | FR-STU-3, FR-STU-4 | Yes |
| GitHub integration | FR-STU-8, FR-STU-11 | Changed |
| Portfolio | FR-STU-10 | Changed |
| Project history | FR-STU-10, FR-APP-2 | Changed |
| Skill proficiency | FR-STU-2 | Yes |
| Experience analytics | FR-ANA-1 | Yes |
| Achievement badges | FR-RWD-3, BR-5 | Yes |
| Experience levels | FR-RWD-2, BR-4 | Yes |
| Digital certificates | FR-CRT-1, FR-CRT-2 | Yes |
| QR verification | FR-CRT-3 | Yes |
| Project recommendations | FR-APP-10, FR-STU-7 | Changed |
| Skill-gap analysis | FR-APP-9 | Changed |
| Application tracking | FR-APP-2 | Yes |
| Project workspace | FR-WRK-1 to FR-WRK-4 | Yes |
| Task management | FR-WRK-7, FR-WRK-8 | Changed |
| Progress tracking | FR-WRK-1 to FR-WRK-4, FR-WRK-7 | Yes |

### Advanced company module

| Source item | Requirement | Status |
|---|---|---|
| Company verification | FR-ORG-1 to FR-ORG-5 | Yes |
| Company profile | FR-ORG-1; `PUT /companies/me` | Yes |
| Project creation | FR-PRJ-1, FR-PRJ-2 | Yes |
| Required skill selection | FR-PRJ-1 | Yes |
| Difficulty level | FR-PRJ-1 | Yes |
| XP allocation | FR-PRJ-3, FR-PRJ-8, BR-1 | Different (decision D-1) |
| Application management | FR-APP-4, FR-APP-7 | Yes |
| Candidate filtering | FR-APP-4 | Yes |
| Student comparison | FR-APP-6 | Changed |
| Project assignment | FR-APP-7 | Yes |
| Task creation | FR-WRK-7 | Changed |
| Progress monitoring | FR-WRK-3, FR-WRK-7 | Yes |
| Submission review, evaluation | FR-EVL-1 to FR-EVL-4 | Yes |
| Experience verification | FR-EVL-4, FR-CRT-1 | Yes |
| Certificate generation | FR-CRT-1, FR-CRT-2 | Yes |

### Example project, AI, verification, analytics, achievements, certificate, recruiter

| Source item | Requirement | Status |
|---|---|---|
| Example project (E-Commerce API, 14 days, intermediate) | Used throughout as the sample record | Yes. The formula gives a maximum of 151 XP; the source's 150 is treated as an approximate figure |
| Applicants and selected counts | FR-ANA-2 | Yes |
| AI project matching with percentages | FR-APP-3, BR-3 | Yes |
| AI skill-gap analysis | FR-APP-9 | Changed |
| AI resume analysis | FR-STU-4 | Yes |
| Verification ID and QR code, verification page | FR-CRT-1, FR-CRT-3 | Yes |
| Student analytics | FR-ANA-1 | Yes |
| Company analytics | FR-ANA-2 | Yes |
| Five achievements | BR-5, FR-RWD-3 | Yes |
| Certificate contents and disclaimer | FR-CRT-2 | Yes |
| Recruiter search by skills, minimum XP, number of projects, verification status | FR-REC-1 | Changed |
| Open a student's project portfolio | FR-REC-2 | Changed |

### Minor vs Major comparison table (Major column)

| Source row | Requirement | Status |
|---|---|---|
| Student, company registration, admin | FR-AUTH-1 to 6, FR-ORG-1 to 7 | Yes |
| Company projects, applications, submission, evaluation | FR-PRJ, FR-APP, FR-EVL | Yes |
| Advanced XP | FR-RWD-1, BR-1 | Yes |
| Advanced portfolio | FR-STU-10 | Changed |
| Certificates, QR verification | FR-CRT | Yes |
| Notifications (advanced) | FR-NTF-1, FR-NTF-2 | Yes |
| Analytics (advanced) | FR-ANA-1, 2, 3 | Yes |
| Achievement system | FR-RWD-3 | Yes |
| Recruiter module | FR-REC-1 to 4 | Changed |
| Fraud and dispute system | FR-EVL-2, FR-EVL-7, FR-ADM-2 to 4, BR-7 | Yes |
| Recommendation engine | FR-APP-10 | Changed |

### Minor-project items that the Major version inherits

| Source item | Requirement | Status |
|---|---|---|
| Admin: manage students, companies, projects | FR-ADM-1, FR-ADM-6, FR-ADM-8 | Yes (projects: changed) |
| Admin: remove inappropriate projects | FR-ADM-8, FR-ADM-9 | Changed |
| Admin: view platform statistics | FR-ANA-3 | Changed |
| Company: set deadline and XP reward | FR-PRJ-1, FR-PRJ-8 | Yes, with D-1 |
| Basic fixed XP (50, 100, 200) | Replaced by BR-1 | Different. The Major version uses a formula; the fixed values are the Minor project's |

### Positioning (source section 6)

XP is a platform metric; the verified history is the important record. Covered by the Positioning paragraph in `01` section 1, BR-11, FR-REC-4, and the viva questions 4a to 4c in `10`.

## 3. Decisions you must confirm

| ID | Decision | Recommended | Alternative |
|---|---|---|---|
| D-1 | Who sets XP | Formula only, from difficulty and duration | Company picks 50% to 100% of the computed `xp_max`, audited, never above it |
| D-2 | GitHub link strength | Public API with a username, labelled not verified | GitHub sign-in (OAuth) to prove ownership; more work, needs a client secret |
| D-3 | Student sub-tasks | Allowed, private to the application, never block completion | Drop them and keep only company tasks |

The numbers added in v2 (10 and 5 points in BR-10, minus 15 trust points for a removed project, 10 tasks per milestone) are starting values I chose, like the rest of the configuration. Decide, record the reason, keep them in configuration.

## 4. What was verified

- `schema.sql` loaded into PostgreSQL 16, 28 integrity cases passed.
- Requirement IDs used in this file were checked against `01-product-requirements.md` by script.
- Not verified: the API, workflows and AI designs are specifications. There is no application code yet.
