# AGENTS.md — SE1 (Software Engineering 1) course project

> **Course:** Software Engineering 1 (مهندسی نرم افزار ۱) — Dr. Zakeri, Spring 1405
> **University:** Amirkabir University of Technology (Tehran Polytechnic) —
> Faculty of Computer Engineering
> **Project name:** **PolyLife** — a diet & physical-fitness web platform on a
> microservice architecture
> **Team 7 (our team):** Sina Sadeghi (lead), Sina Negahban, Amirali Rahimi
> **Chosen microservices:** Chat with Coach + Reserve Coach

This repository is the **monorepo for the whole course** — eight student teams
each build one microservice behind a shared Django "core". **You almost
certainly want to read [`teams/team7/AGENTS.md`](teams/team7/AGENTS.md)
instead of this file.** The rest of this document is general orientation.

## 0. Course deliverables (what you have to submit)

| Phase | Title | Status (team 7) |
|-------|-------|-----------------|
| P1 | Requirements + SRS | Submitted |
| P2 | UML diagrams + wireframes | Submitted |
| **P3** | **Microservice architecture & integration** | **In progress (this phase)** |
| P4+ | TBA by course staff | — |

Phase-3 brief: `docs/P3_SE1.pdf` (12 pages, Persian). Deadline: **28 Tir 1405
(≈ 19 Jul 2026) at 23:59**. Evaluated **orally** — every team member must
master the whole deliverable.

The detailed Phase-3 plan for our team lives in
[`teams/team7/.agents/`](teams/team7/.agents/) — start with
`README.md` there, then `00_team_overview.md`, then
`02_architecture_decisions.md`.

## 1. What this repo is

PolyLife is a microservice-architecture platform for diet and physical
fitness. It contains:

- `core/` — Django service shared by all teams: auth, JWT, the
  `/api/verify` forward-auth endpoint. **Do not modify** unless the TA
  explicitly tells you to.
- `frontend/` — React landing page served by core. **Do not modify.**
- `teams/teamN/` — eight team folders, one per group. **You only own
  one.** For us, that's `teams/team7/`.

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
- **Never push to `main`.** PRs target `feature/<name>` or
  `development` (when it exists).
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
| 1 | `teams/team1/` | _fill in_ | 9101 |
| 2 | `teams/team2/` | _fill in_ | 9102 |
| 3 | `teams/team3/` | _fill in_ | 9103 |
| 4 | `teams/team4/` | _fill in_ | 9104 |
| 5 | `teams/team5/` | _fill in_ | 9105 |
| 6 | `teams/team6/` | _fill in_ | 9106 |
| **7** | **`teams/team7/`** | **`teams/team7/AGENTS.md`** | **9107** |
| 8 | `teams/team8/` | _fill in_ | 9108 |

## 5. Where to find what

| Question | File |
|----------|------|
| How do I run the project? | `README.md` (root) and `teams/GETTING_STARTED.md` |
| What does the auth flow look like? | `core/auth_views.py` + any team's `gateway.conf` |
| How do I demo the API? | `docs/API_TESTING.md` |
| What is our team building? | `teams/team7/AGENTS.md` → `.agents/00_team_overview.md` |
| What is the database schema? | `teams/team7/.agents/03_database_design.md` |
| What is the API contract? | `teams/team7/.agents/04_api_endpoints.md` |
| Why did we pick FastAPI? | `teams/team7/.agents/02_architecture_decisions.md` |

## 6. AI-assistant protocol

- **Before coding**, read the team's `AGENTS.md` and the relevant
  `.agents/02_architecture_decisions.md` section. Don't invent new
  approaches silently.
- **When you change something**, update the matching doc in the same
  commit. Stale docs are worse than no docs.
- **When you make a decision**, add it to
  `.agents/02_architecture_decisions.md` §8 "Open architectural
  questions" (or resolve it there if it was open).
- **Never commit secrets.** `.env` is git-ignored; `.env.example` is
  committed and contains dev-only placeholders.