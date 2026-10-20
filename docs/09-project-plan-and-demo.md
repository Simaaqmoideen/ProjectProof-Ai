# ProjectProof AI: Project Plan and Demo Guide

Team size and deadline are not known yet, so this plan is written in phases with a share of the time for each, plus an example schedule for 12 weeks. Adjust the numbers; keep the order.

## 1. Principle

Build the complete loop first, thinly, then deepen it. At the end of every phase the application must run. If time runs out, you cut from the bottom of the list, never from the top, and you still have a working project.

## 2. Phases

| Phase | Share of time | Work | Done when |
|---|---|---|---|
| 0. Setup | 5% | Repository, Docker Compose, database from `schema.sql`, CI, seed script, skeleton frontend and backend, `AGENTS.md` and docs in place | `docker compose up` gives a running app with seed data |
| 1. Accounts and approval | 10% | Auth, roles, email verification, company registration, admin approval queue, audit log | A company registers and an admin approves it; the audit log shows it |
| 2. Projects and applications | 15% | Project creation with milestones and tasks, publish, browse, apply, select, deterministic match score and breakdown, recommendation score, applicant comparison | A student applies and a company selects, with match score visible |
| 3. Work and evaluation | 15% | Workspace, check-ins, task progress and personal sub-tasks, submission versions, evaluation, appeals, scheduler jobs | A project goes from selected to approved or rejected |
| 4. Proof (signature feature) | 15% | Certificate transaction, verification ID, QR token, public page, certificate PDF, revocation, XP, levels, badges | The happy-path and revocation scenarios pass end to end |
| 5. Dashboards, portfolio and admin tools | 10% | Student and company dashboards and stats, student portfolio page, GitHub link, recruiter search and portfolio view, admin statistics, project removal and reports, in-app and email notifications | Each role has a useful home screen; the recruiter loop and project removal scenarios pass |
| 6. AI layer and highlights | 17% | Shared AI service layer, then resume analysis, match explanation and ranking, brief generator, similarity or pre-review, skill gap, GitHub analysis, recruiter plain-text search | AI tests pass; evaluation numbers recorded |
| 7. Stretch | 3% | Mentor, anomaly rules, feedback drafter, whichever fits | Only if phases 1 to 6 are green |
| 8. Hardening and demo | 9% | Security checklist, accessibility pass, performance check, backup restore, rehearsals, report | Exit criteria in 08-test-plan.md met |

**Example for 12 weeks:** phase 0 week 1; phase 1 weeks 1 to 2; phase 2 weeks 3 to 4; phase 3 weeks 5 to 6; phase 4 weeks 6 to 8; phase 5 week 8; phase 6 weeks 8 to 10; phase 7 week 10; phase 8 weeks 11 to 12 (write the report from week 6 onward, not at the end).

If you have fewer than 12 weeks: do phases 0 to 5 and two AI highlights (resume analysis and match explanation), skip phase 7.

## 3. Scope cut order

When behind schedule, cut in this order and tell your guide what you cut and why:
1. All stretch items (PRD tier "Stretch")
2. AI repo analysis, then skill-gap AI and recruiter plain-text search (keep GitHub linking, the deterministic missing-skills list and filter-based search)
3. Pre-review (keep similarity), or the reverse, but keep one
4. Brief generator
5. Applicant comparison and student personal sub-tasks (keep company tasks)
6. Email notifications (keep in-app)
7. Appeals (keep revocation by admin)

The v2 items that stay even when cutting: student portfolio page, recruiter search with portfolio view, admin project removal, platform statistics, recommendation score. The Major specification names them, and they are mostly queries over data that already exists.

Never cut: approval of companies, the certificate transaction, the public verification page, revocation, the audit log, human evaluation, the labelling and logging of AI output.

## 4. Roles by team size

**One person.** Follow the phases in order; use the cut order early; keep AI to resume analysis plus match explanation.

**Two people.**
- Person A: backend, database, certificate transaction, security, scheduler
- Person B: frontend, design system, dashboards, public page, PDF, end-to-end tests
- Shared: AI service layer (A) and AI features (split), documents

**Three or four people.** Add: an AI and data owner (prompts, similarity engine, evaluation sets, calibration) and a quality and documentation owner (tests, seed data, report, demo, usability test). Rotate code review so every pull request is read by someone else.

## 5. Working agreements

- `main` is always deployable. Work happens on short branches; every change goes through a pull request with at least one review and passing CI.
- Small commits with clear messages. One feature per pull request.
- A feature is done only when: code merged, tests written and passing, documents updated if behaviour changed, and a demo of it shown to the team.
- Weekly 30-minute review: what works, what is blocked, what to cut.
- Keep a running decisions log in the repository (date, decision, reason).
- Never commit secrets. Rotate any that slip.

## 6. Risks

| Risk | Likelihood | Impact | What to do |
|---|---|---|---|
| Scope too large | High | High | Phases, cut order, weekly review |
| AI provider changes or has an outage on demo day | Medium | Medium | Provider behind one interface; manual path always works; prepare cached example outputs for the demo |
| Certificate or verification bug late in the project | Medium | High | Build it in phase 4, test it heavily, run database tests in CI |
| PDF generation fails in the deployed image | Medium | Medium | Test PDF in Docker in phase 0 |
| Free hosting sleeps or is slow | Medium | Medium | Warm up before the demo; keep a local fallback |
| Demo data looks fake | Medium | Medium | Seed realistic, varied data; include one revoked record |
| Team member unavailable | Medium | Medium | Pair on critical parts; documents in the repository |
| Privacy or legal question raised in the viva | Medium | Medium | Prepare the section 9 answers in 07-security-and-privacy.md |
| Over-claiming what a certificate means | Medium | High | Disclaimer on every certificate and page; same wording in the report |
| Cold start (no companies) | High | Medium | Seed data and a "college-sponsored projects" mode run by the placement cell |

## 7. Five-minute demo script

Prepare accounts in advance: admin, company (approved), a second company (pending), student, recruiter. Keep all on separate browser profiles or windows.

| Time | Action | What to say in one sentence |
|---|---|---|
| 0:00 | Landing page and the problem | "Resumes list projects nobody can check; this platform makes them verifiable." |
| 0:30 | Admin queue: approve the pending company, point out the automatic checks | "Anyone can register as a company, so an admin approves each one." |
| 1:00 | Company creates a project with the AI brief generator, edits, publishes; point at read-only XP | "AI drafts, the company decides, and XP comes from a formula, not a number the company types." |
| 1:45 | Student dashboard: project list with match breakdown; apply | "The match score is a formula the student can inspect; AI only explains it." |
| 2:15 | Company applicants: ranked list with reasons; select the student | "The AI ranking is labelled as a draft; the company makes the selection." |
| 2:40 | Student workspace: check in on a milestone; submit (use a pre-filled submission) | "Progress is visible during the work, not only at the end." |
| 3:00 | Company review page: similarity result and pre-review; approve | "The reviewer sees evidence, then decides." |
| 3:30 | Student sees the certificate and XP and badge; open the PDF; scan the QR with a phone | "One transaction creates the certificate, the XP and the audit record." |
| 4:00 | Verification page on the phone: point at status, ID, timeline, disclaimer | "This reads live data, so it can't be a stale screenshot." |
| 4:20 | Admin revokes the certificate; refresh the phone page: Revoked | "If something is wrong, the record changes everywhere immediately." |
| 4:40 | Optional: recruiter search, sorted by verified projects; open a portfolio | "Recruiters see verified projects first; XP is secondary." |
| 4:50 | Close: limits and next steps | "A certificate proves completion on this platform, not employability." |

**Rehearse at least three times** on the real demo environment. Time it. Decide in advance which step you skip if you run over (usually the recruiter search).

## 8. Demo environment checklist

- [ ] Deployed or running locally with a charged laptop and a backup power plan
- [ ] Seed data loaded; passwords written on a card, not on screen
- [ ] AI keys set and tested that morning; cached example outputs ready if the provider fails
- [ ] Phone with the QR scanner tested; a printed QR as a backup
- [ ] Browser zoom and window sizes set; notifications silenced
- [ ] A 90-second screen recording of the whole flow as a last-resort fallback
- [ ] Reports, diagrams and test results ready to show if asked

## 9. Questions to settle with your guide early

1. Is the team allowed to use hosted AI services, and is there a budget?
2. Does the project need a specific document format or template?
3. Does the college need to approve a project that stores student data?
4. Is there a limit on team size or on third-party tools?
5. Will the placement cell or a faculty member act as the first approved company for the demo?
