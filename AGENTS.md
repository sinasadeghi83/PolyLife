# AGENTS.md — SE1 (Software Engineering 1) course project

> **Course:** Software Engineering 1 (مهندسی نرم افزار ۱) — Dr. Zakeri, Spring 1405
> **University:** Amirkabir University of Technology (Tehran Polytechnic) —
> Faculty of Computer Engineering
> **Project name:** **PolyLife** — a diet & physical-fitness web platform on a
> microservice architecture

This repository is the **monorepo for the whole course** — eight student teams
each build one microservice behind a shared Django "core". If you are
working on a specific team's service, **read that team's `AGENTS.md`
inside `teams/teamN/` first** — it documents the local stack, sprint
backlog, and hard rules for that team. The rest of this document is
general, course-wide orientation.

## 0. Course deliverables (what you have to submit)

| Phase | Title |
|-------|-------|
| P1 | Requirements + SRS |
| P2 | UML diagrams + wireframes |
| **P3** | **Microservice architecture & integration** |
| P4+ | TBA by course staff |

Phase-3 brief: `docs/P3_SE1.pdf` (12 pages, Persian). Deadline: **28 Tir 1405
(≈ 19 Jul 2026) at 23:59**. Evaluated **orally** — every team member must
master the whole deliverable.

## 1. What this repo is

PolyLife is a microservice-architecture platform for diet and physical
fitness. It contains:

- `core/` — Django service shared by all teams: auth, JWT, the
  `/api/verify` forward-auth endpoint. **Do not modify** unless the TA
  explicitly tells you to.
- `frontend/` — React landing page served by core. **Do not modify.**
- `teams/teamN/` — eight team folders, one per group. **You only own
  one.** Open the `AGENTS.md` inside your team folder to find out
  which microservices you've been assigned.

Each team folder is a small workspace that boots a per-team gateway
(Nginx) on `localhost:910N`, talks to core for auth, and runs its own
backend + database.

## 2. Repo-wide rules

- **Read `teams/GETTING_STARTED.md`** before anything else. It documents
  the helper scripts and the dev workflow.
- **Read your team's `AGENTS.md`** (e.g. `teams/team7/AGENTS.md`). It
  documents the local architecture decisions, sprint backlogs, and
  hard rules.
- **Never edit** the top-level `requirements.txt`, `Dockerfile`,
  `docker-compose.yml`, `polylife/settings.py`. PDF §۳.۳ forbids it. Add
  dependencies in your team's `requirements.txt` instead.
- **No PRs to `upstream`** (`github.com/PolyLife2026/PolyLife`). All pull
  requests stay inside our fork (`origin` = `sinasadeghi83/PolyLife`).
  Inside the fork, PRs may target `main`, `development`, or
  `feature/<name>` — pick the branch that fits the change.
- **Never `git push -f`.**
- **Commits** use the format `<gitmoji> [teamX] verb: description` —
  see your team's `.agents/07_git_workflow.md` for examples.

## 3. Helper scripts

| You want to… | Run |
|--------------|-----|
| Start the core only | `scripts/bash/start-core.sh` |
| Start one team | `scripts/bash/start-team.sh N` |
| Start everything | `scripts/bash/start-core.sh` then `scripts/bash/start-all-teams.sh` |
| Stop everything | `scripts/bash/stop-all.sh` |

PowerShell mirrors in `scripts/windows/`.

## 4. Per-team entry points

| Team | Folder | Owner docs | Gateway port |
|------|--------|------------|--------------|
| 1 | `teams/team1/` | _each team writes its own_ | 9101 |
| 2 | `teams/team2/` | _each team writes its own_ | 9102 |
| 3 | `teams/team3/` | _each team writes its own_ | 9103 |
| 4 | `teams/team4/` | _each team writes its own_ | 9104 |
| 5 | `teams/team5/` | _each team writes its own_ | 9105 |
| 6 | `teams/team6/` | _each team writes its own_ | 9106 |
| 7 | `teams/team7/` | _each team writes its own_ | 9107 |
| 8 | `teams/team8/` | _each team writes its own_ | 9108 |

## 5. Where to find what (general questions)

| Question | File |
|----------|------|
| How do I run the project? | `README.md` (root) and `teams/GETTING_STARTED.md` |
| What does the auth flow look like? | `core/auth_views.py` + any team's `gateway.conf` |
| How do I demo the API? | `docs/API_TESTING.md` |
| What is *my* team building, and what stack are we using? | `teams/<your-team>/AGENTS.md` |
| What is *my* team's database schema? | `teams/<your-team>/.agents/03_database_design.md` (if it exists) |
| What is *my* team's API contract? | `teams/<your-team>/.agents/04_api_endpoints.md` (if it exists) |

## 6. AI-assistant protocol

- **Before coding**, read the relevant team's `AGENTS.md` and
  `.agents/02_architecture_decisions.md`. Don't invent new approaches
  silently.
- **When you change something**, update the matching doc in the same
  commit. Stale docs are worse than no docs.
- **When you make a decision**, record it in your team's
  `.agents/02_architecture_decisions.md` §"Open architectural questions"
  (or resolve it there if it was open).
- **Never commit secrets.** `.env` is git-ignored; `.env.example` is
  committed and contains dev-only placeholders.
- **Course-wide secrets** (e.g. the Atlassian API token for one team's
  Jira site) must be documented in the **team's own** `AGENTS.md`, not
  here, so the contract is owned by the people whose env it lives in.