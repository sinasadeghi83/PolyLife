# AI Docs — Index

This folder contains the planning documents our team uses to deliver Phase 3
of the Software Engineering 1 project at Amirkabir University of Technology.

> **Read `00_team_overview.md` first.** Every other doc links back to it as
> the source of truth for team members, chosen microservices, and the
> project context.

---

## Documents in this folder

| # | File | Purpose |
|---|------|---------|
| 00 | `00_team_overview.md` | Team info, services chosen, course context, P3 submission rules. |
| 01 | `01_phase3_breakdown.md` | Full task breakdown of P3_SE1.pdf, section by section. |
| 02 | `02_architecture_decisions.md` | Tech-stack, Docker layout, env vars, networking, helper scripts, CI. |
| 03 | `03_database_design.md` | ER diagram (DBML), table descriptions, sample data, migration plan. |
| 04 | `04_api_endpoints.md` | REST + WebSocket endpoints, error codes, versioning. |
| 05 | `05_jira_setup.md` | Jira workflow, sprints, definitions of done, meeting notes template. |
| 06 | `06_task_assignment.md` | Who does what — Sina Sadeghi, Sina Negahban, Amirali Rahimi. |
| 07 | `07_git_workflow.md` | Branching model, commit format, PR rules, push schedule. |
| 08 | `08_implementation_checklist.md` | Final acceptance checklist + smoke-test script. |
| 09 | `09_progress_tracking.md` | Agent workflow for evidence-based progress tracking across Jira, GitHub, tests, CI, and Scrum reports. |

---

## How an agent should use these docs

1. **Before starting any task**, open the relevant doc and re-read its
   "decisions" section — never invent a new approach silently.
2. **Cross-check** between docs. If `02_architecture_decisions.md` and
   `03_database_design.md` disagree on a column name, raise it before coding.
3. **Update the doc** in the same PR that changes the system. A doc that goes
   stale is worse than no doc.
4. **Don't write source code in this folder.** This folder is for plans,
   decisions, and checklists only. Code lives under `teams/team7/`.

---

## Document history

| Date | Author | Change |
|------|--------|--------|
| 2026-07-15 | Sina Sadeghi | Initial scaffold created from P3_SE1.pdf. |