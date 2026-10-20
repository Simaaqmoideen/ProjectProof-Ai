# ProjectProof AI: College Report Pack

Use this to write the project report, prepare the presentation and get ready for the viva. Everything here is a starting draft: replace placeholders in square brackets with your own facts, and only claim results you actually measured.

## 1. Report structure

| Chapter | Contents | Source in this document set |
|---|---|---|
| Abstract | One page: problem, solution, method, result, limits | Section 2 below |
| 1. Introduction | Background, problem statement, objectives, scope, organization of the report | 01 (sections 1 to 4) |
| 2. Literature survey | Existing platform types, their gaps, what this project adds | Section 3 below |
| 3. Requirements | Users, functional and non-functional requirements, business rules | 01 (sections 3, 5 to 7) |
| 4. System design | Architecture, technology choices, data design, API design, security design | 03, 02, 04, 07 |
| 5. Workflows and AI design | Use cases, state machines, AI modules and safeguards | 05, 06 |
| 6. Implementation | What was built, with screenshots; key algorithms (certificate transaction, match score, similarity) | Your code; 03 section 5; 06 section 5 |
| 7. Testing and evaluation | Test cases, results, AI evaluation tables, security and accessibility checks | 08, 06 section 8 |
| 8. Results and discussion | Demo outcomes, measurements, what worked and what did not | Your measurements |
| 9. Limitations and ethics | Honest limits, privacy, bias, misuse | Section 5 below; 07 |
| 10. Conclusion and future scope | Summary and next steps | Section 6 below |
| References | Sources you actually used | Yours |
| Appendices | Schema, API list, test table, user manual, seed data description | 02, 04, 08 |

## 2. Abstract (draft to adapt)

> Students often list projects on their resumes that recruiters cannot verify, and recruiters lack a quick, trustworthy way to separate completed work from claims. ProjectProof AI is a web platform in which admin-approved companies publish real projects, students apply and complete them through milestone-based workspaces, and companies evaluate the work. Each approved completion produces a platform certificate with a unique verification ID and QR code that opens a publicly accessible page showing the record read live from the database, including a clear revoked state if a problem is later found. The system also assigns experience points through a fixed formula, awards levels and badges from verified completions only, and offers AI assistance: resume analysis, explainable project matching, project brief drafting, skill-gap guidance, GitHub profile analysis and [code similarity detection / submission pre-review]. Students keep a portfolio of verified projects that approved recruiters can search; XP and levels are secondary to that verified history. AI output is always labelled, logged and applied only after a person accepts it; AI never decides on selection, evaluation, certification or revocation. The platform was built with [stack] and evaluated with [number] automated tests and [number] AI test cases, with [key result, for example: the similarity engine detected X of Y planted copies]. A certificate proves completion on the platform, not employment, and the system states this wherever a record is shown. Limitations include [limits], and future work includes [items].

Keep the abstract to about 200 words in the final version.

## 3. Literature survey (how to do it)

Do not rely on claims you have not checked. For each category below, find two or three real examples, read their public documentation, and record what they actually offer. Cite what you read.

| Category | What to look for | The gap this project addresses |
|---|---|---|
| Portfolio and resume sites | Is the work verified by anyone other than the owner? | Records are self-declared |
| Certificate and course platforms | Do they certify project work done for a real organization, with human evaluation? | Often certify course completion, not delivered work |
| Virtual experience programs | Who evaluates; can a third party verify; is it open to any company? | Usually tied to one company and limited projects |
| Internship and freelance marketplaces | Is there a student-friendly, low-stakes path with verified proof and no payment? | Different purpose and entry barrier |
| Coding challenge and assessment platforms | Real company briefs or puzzle problems? Public verifiable record? | Test skills, rarely show delivered, evaluated work |
| Credential verification standards (digital badges, verifiable credentials) | How verification and revocation work | Source of design ideas for revocation and verification pages |

Write a comparison table with columns: platform, who verifies, public verification link, revocation, AI use, cost. Fill it only from what you confirmed. Summarise the gap in three sentences.

## 4. Diagrams to include

| Diagram | Where to get it |
|---|---|
| Entity relationship diagram | 02 section 2 (Mermaid; export as an image) |
| System architecture | 03 section 2 |
| Use case diagram | Draw from the actors in 05 section 1 and use cases UC-1 to UC-11 |
| Data flow diagrams, level 0 and 1 | Level 0: platform with users and external services (email, AI provider). Level 1: modules from 04 |
| State diagrams | 05 section 3 |
| End-to-end flow | 05 section 2 |
| Sequence diagram for certificate issue | Draw from 03 section 5 |
| Sequence diagram for public verification | Draw from 03 section 6 |
| Screens | Screenshots of your running application |

## 5. Limitations, ethics and risks (write these honestly)

- **Platform scope.** A certificate proves a project was completed and approved on ProjectProof AI. It does not prove employability, skill beyond the project, or employment.
- **Trust depends on companies and admins.** Approval checks reduce fake issuers; they cannot eliminate them. Say what the checks are and what they miss.
- **Similarity detection** is not proof of cheating, compares only against submissions on the platform, and cannot detect AI-generated code.
- **AI limits.** Models can be wrong; the design therefore keeps humans in every decision and validates outputs. State your measured accuracy and your failures.
- **Bias and fairness.** Matching and ranking use skills and experience, which may favor students with more opportunities. Mention how the formulas are visible and adjustable, and that humans select.
- **Privacy.** Profiles are private by default, recruiters are approved, public pages show only agreed fields. Mention what you have not covered (for example a formal legal review).
- **Cold start.** The platform needs companies to be useful; your mitigation is college-sponsored projects.
- **Misuse.** A company could try to manipulate scores; trust score, anomaly rules, appeals and revocation exist for this reason.

## 6. Future scope (pick what you honestly would do next)

Team projects with contribution tracking; GitHub sign-in (OAuth) so a linked account is proven to belong to the student; integration with placement-cell tools; verifiable credential standards for portable certificates; richer anomaly detection using more data; multilingual interface; mobile application; employer feedback loop that improves difficulty calibration; accessibility audit by external users.

## 7. Presentation outline (10 minutes, 10 slides)

1. Problem: unverifiable project claims
2. Idea in one sentence and one picture (the flow diagram)
3. Users and what each gets
4. How verification works (certificate, ID, QR, live page, revocation)
5. Trust design: approval, audit log, appeals, AI boundaries
6. AI features and what they are not allowed to do
7. Architecture and stack
8. Live demo (use the script in 09 section 7)
9. Testing and results (your real numbers)
10. Limits, future scope, thank you

## 8. Viva preparation

Prepare a one-minute answer for each. Answers should use your real design and numbers.

**Concept and need**
1. What problem does this solve that portfolio sites do not?
2. Why would a company post a project here?
3. Why would a recruiter trust a certificate from this platform?
4. Is a ProjectProof certificate the same as internship experience? (No, and the platform says so.)

**Rewards and design choices**
4a. Who decides how much XP a project gives, and why can't a company type the number? (Formula from difficulty and duration; decision D-1 in 01.)
4b. Is XP the proof of experience? (No: the verified project history is; XP is a motivation metric.)
4c. How can an admin remove a bad project without harming students or valid certificates? (Rule in 05, UC-12.)

**Trust and security**
5. How do you stop a fake company issuing certificates to friends?
6. Can someone forge or edit a certificate? What happens if an admin edits the database directly?
7. How do you stop people guessing verification IDs?
8. What happens when a certificate is revoked, and how fast is that visible?
9. How do you protect against SQL injection, cross-site scripting and broken access control?
10. Who can see a student's data?

**AI**
11. Which parts use AI and which do not, and why?
12. How do you stop the AI making a decision or inventing facts?
13. What is prompt injection, and how did you test for it?
14. How did you measure the quality of your AI features?
15. How is the match score calculated and how did you choose the weights?
16. How does similarity detection work? What are its false positives?
17. What happens if the AI service is down?

**Engineering**
18. Why this tech stack, and what did you consider instead?
19. Why PostgreSQL? Which rules does the database enforce itself?
20. Walk through the certificate issue transaction. What if it fails halfway?
21. How did you test the system? What did the tests find?
22. What was the hardest bug?

**Ethics, limits, future**
23. Could this system be unfair to some students?
24. What are the limits of the project?
25. What would you build next?
26. How would you get the first real companies?
27. What does the law require when storing student data? (Answer with what you checked; say what you would confirm with a lawyer.)

## 9. Things examiners tend to value

- A working end-to-end demo more than a long feature list
- Honest measurements and honest limits
- Clear reasons for each decision
- Evidence that tests exist and found real problems
- Knowing your own code: every team member should be able to explain any module
