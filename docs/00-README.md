# ProjectProof AI: Documentation Set (version 2)

Version 2 adds the items the Major project section requires that version 1 missed or left as stretch: student portfolio, tasks inside milestones, admin project removal and reports, GitHub integration, skill-gap analysis, applicant comparison, recommendation engine, the recruiter module, platform statistics, and a clear XP decision. See `11-traceability-and-changes.md`.

Everything needed to design, build, test, demo and write up the project, except the visual design file (`DESIGN.md`), which you will add later.

## What is in this set

| File | What it is | Read it when |
|---|---|---|
| `00-README.md` | This index | First |
| `01-product-requirements.md` | Goals, users, scope tiers, every requirement with an ID, business rules, glossary | Before anything else; it is the source of truth |
| `02-database-schema.md` | Tables, relationships, rules, queries, identifiers, retention | Before writing any backend code |
| `schema.sql` | The runnable PostgreSQL schema (tested, see below) | When you create the database |
| `03-tech-stack-and-architecture.md` | Stack choices and reasons, architecture, folder layout, configuration, deployment, the certificate transaction | When you set up the repository |
| `04-api-specification.md` | Every endpoint, roles, errors, rate limits, examples | When you build routes or the frontend client |
| `05-workflows-and-state-machines.md` | Flows, allowed status changes, use cases, scheduled jobs, notifications | When you write business logic |
| `06-ai-modules-specification.md` | Which parts use AI, the shared AI layer, formulas, algorithms, output formats, safety, how to evaluate | Before any AI work |
| `07-security-and-privacy.md` | Threats and controls, permissions matrix, privacy design, legal items to check, incident response | While building, and before the demo |
| `08-test-plan.md` | Test levels, 107 numbered test cases mapped to requirements, end-to-end scenarios, exit criteria | While building, and before each milestone |
| `09-project-plan-and-demo.md` | Phases, cut order, roles, risks, five-minute demo script, demo checklist | At the start and before the demo |
| `10-college-report-pack.md` | Report structure, abstract draft, literature survey method, diagrams list, presentation outline, viva questions | When you write the report |
| `11-traceability-and-changes.md` | Every item of the Major project section mapped to requirement IDs and tests, the list of v2 changes, open decisions | When you answer "is everything covered?" and when you write the report |
| `AGENTS.md` | Rules and instructions for AI coding agents | Put it in the repository root |

## Suggested repository layout

```
projectproof/
  AGENTS.md              # from this set
  DESIGN.md              # add later
  schema.sql             # from this set (convert to migrations in backend/migrations)
  docs/                  # files 01 to 11 from this set
  backend/
  frontend/
```

`AGENTS.md` refers to `docs/01-…` through `docs/08-…`, `docs/11-…` and to `schema.sql`, so keep those locations.

## How to use it with a coding agent

1. Copy the files into the layout above.
2. Tell the agent: "Read AGENTS.md first, then build phase 0 from docs/09-project-plan-and-demo.md."
3. For each feature, give the agent the requirement ID (for example `FR-CRT-1`) and ask it to read the related documents before coding.
4. Ask it to write tests from `docs/08-test-plan.md` alongside each feature.
5. When `DESIGN.md` exists, add it to the repository root; `AGENTS.md` already tells the agent to follow it for every UI change.

## Reading order

Start with 01, then 09 (to see the plan), then 02 and 03 (to set up). Then follow the phases: 05 and 04 for business logic and routes, 06 when you reach AI, 07 and 08 throughout.

## What was verified and what was not

- **Verified:** `schema.sql` (version 2) was loaded into PostgreSQL 16 and 28 integrity cases were run (certificate rules, append-only tables, uniqueness, level calculation, public view, and the v2 additions: project removal rules, task progress rules, portfolio and platform statistics views). Results are in `02-database-schema.md` section 6. The Mermaid diagrams were written by hand and not rendered here.
- **Not verified:** nothing else has been run. There is no application code yet. The API, algorithms and AI designs are specifications, not tested software.

## Assumptions made (change them freely)

- Stack: React and TypeScript frontend, FastAPI backend, PostgreSQL, Docker. If you pick another stack, the requirements, schema, workflows, security and test documents still apply; adapt `03` and `04`.
- Numbers such as XP base (6 per day), XP cap (200), level thresholds, match weights, similarity thresholds, trust score points, limits (2 open projects, 7-day appeals, 3 submission versions) are **starting values I chose**. Examiners may ask why; decide, record the reason, and keep them in configuration.
- A single college-run deployment, English only, admin accounts created by command line.
- Recruiters are approved by an admin, which was not in the original idea but is needed because they can see student data.
- XP is formula-only (decision D-1 in `01`). The Major specification says companies allocate XP; this design lets them influence it only through difficulty and duration. `01` BR-1 gives the alternative if your guide wants company-set XP.

## Open decisions to make before building

1. Team size and deadline (decides how many AI features to build)
2. Which AI provider and what spending limit
3. Where the demo will run
4. Whether the placement cell acts as the first company
5. Whether your college needs a legal or ethics review for storing student data (see `07`, section 9)
6. Decision D-1: formula-only XP or company-chosen XP within a limit
7. With the v2 additions, the Core list is longer; confirm team size and deadline against the phases and cut order in `09`

## Not included

- `DESIGN.md` (you will choose the design later)
- Source code
- Legal advice. `07` lists what to check; it does not state what the law requires
