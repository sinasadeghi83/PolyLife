# Phase 3 — Task Breakdown

This document maps **every concrete task** that P3_SE1.pdf expects, section by
section, and links each task to the deeper docs in this folder. If a task is
missing here, it was not required by the PDF.

> Source: `docs/P3_SE1.pdf` (12 pages, in Persian, deadline 28 Tir 1405).

---

## Section A — Jira / Project Management (PDF §بخش اول)

### A.1 Create Jira site + admin account
- Sina Sadeghi (team lead) registered a **new Atlassian Cloud Free site** at
  <https://www.atlassian.com/software/jira> on 2026-07-15.
- Subdomain: **`sinasadeghi83.atlassian.net`** (claimed by Sina S. with
  `sina.sadeghi83@gmail.com`).
- TAs confirmed on 2026-07-15 that each team creates its own site rather
  than using the shared `rosenazeri83.atlassian.net`. See `05_jira_setup.md`
  for the full decision rationale.
- Skip onboarding questions with `Skip`.

### A.2 Per-member accounts
- Each of the three members (Sina Sadeghi, Sina Negahban, Amirali Rahimi)
  creates their **own free Atlassian account** on the new subdomain using
  their personal email.
- Sina Sadeghi (admin) invites Sina Negahban and Amirali Rahimi via the
  project's `Invite People` button.

### A.3 Create a Scrum project
- Project type: **Scrum**, managed as **Team-managed**.
- Add the **scrum master** as a project member (the TA will give us an email).

### A.4 Invite team members
- Invite Sina Sadeghi, Sina Negahban, and Amirali Rahimi from the project
  home page (`Invite People`).

### A.4 Configure the board
- Default columns `To Do`, `In Progress`, `Done`. Add a **`Testing`** column
  before `Done` so manual QA has a visible home.

### A.5 Create Issues
- Sprint → Issue list → Create.
- Issue types we will use: **Story**, **Task**, **Bug**.
- Each Story from P2 is split into 2–5 Tasks. Every Task is **assigned** to one
  person. Workload is balanced.

### A.6 Stories ⇄ Tasks mapping
| Source | Stories | → Tasks |
|--------|---------|---------|
| P1 functional reqs | Coach-related reqs (chat + booking) | Sub-tasks per microservice |
| P2 use cases | UC-CHAT-*, UC-RES-* | Implementation tasks |
| P3 infra needs | infra, docker, gateway, auth | Infrastructure tasks |

> Details in `04_jira_setup.md`.

---

## Section B — Database Design (PDF §بخش دوم)

### B.1 Requirements the DB must satisfy
- Reflect only data the **Chat with Coach** and **Reserve Coach** services touch.
- Every table: `id` PK, `created_at`, `updated_at`, `is_deleted`.
- snake_case, English, descriptive names.
- Indexed on every column we filter/sort by frequently.
- FK between related tables.
- Extensible: adding a column later must not require restructuring.

### B.2 Deliverables
- **ER Diagram** — export to PNG/PDF/dbml.
- **Database description document** — table purpose, constraints, ≥ 2 sample rows per table.

> Details in `06_database_design.md`.

---

## Section C — Architecture & Implementation (PDF §بخش سوم)

### C.1 Global architecture
Request flow per PDF §۳:
```
Browser → Team Gateway (Nginx) → Core Service (auth) → Team Backend → Team DB
```
Our backend **never** decodes JWT itself. Gateway injects headers:
- `X-User-Id`
- `X-User-Username`

### C.2 Mandatory constraints (verified against the fork)
| Constraint | Where we put it | Actual value in repo |
|------------|------------------|----------------------|
| All services in Docker | `docker-compose.yml` per team | `teams/team7/docker-compose.yml` |
| Shared network `polylife_net` | Same compose file | declared `external: true, name: polylife_net` |
| "URL_BASE_CORE" env var | `.env` (from `.env.example`) | **`CORE_BASE_URL=http://core:8000`** |
| "URL_DATABASE" env var | `.env` (from `.env.example`) | **`DATABASE_URL=postgres://team7_user:…@db:5432/team7`** |
| Never edit top-level `requirements.txt` | Add team-local one in `teams/team7/backend/` | root `requirements.txt` untouched |
| Never edit root `settings.py` / `Dockerfile` / `docker-compose.yml` | — | Forbidden by PDF §۳.۳; we only touch `teams/team7/*` |
| Non-Django stack? **Must** talk to Core via gRPC or RabbitMQ | Our backend → Core: `auth_request` already does it at the gateway layer; no extra gRPC needed for our use cases | See `02_architecture_decisions.md` §2.4 |

### C.3 Gateway & routing
- Per-team **Nginx** gateway that uses the `auth_request` directive to
  forward-auth against `http://core:8000/api/verify`. The gateway extracts
  `X-User-Id` and `X-User-Username` from Core's response and forwards them
  to the backend (see actual `teams/team7/gateway.conf`).
- Nginx routes requests by path prefix to internal services (the template
  uses Docker's embedded DNS via `resolver 127.0.0.11`).
- Host port for team-7's gateway: **`9107`** (env var `TEAM_PORT=9107` in
  `teams/team7/.env.example`). The PDF's example used `9101` because that
  is team-1's default; ours is team-7.
- The template's gateway config already exists in `teams/team7/gateway.conf`
  and only needs extensions for our chat WebSocket route.

### C.4 Authentication
- All auth is in **Core** (Django).
- We only **trust** the `X-User-*` headers our gateway forwards.
- We do **not** store or decode JWT ourselves.

### C.5 UI/UX
- Brand palette & typography are provided in PDF page 8.
- Plain HTML/CSS is acceptable; a separate frontend = bonus.

### C.6 Helper scripts (already provided by the repo)
The repo ships working scripts under `scripts/bash/`:

- `scripts/bash/start-core.sh` — start core (`http://localhost:8000`).
- `scripts/bash/start-team.sh 7` — start only team-7.
- `scripts/bash/start-all-teams.sh` — start core + all 8 teams.
- `scripts/bash/stop-all.sh` — stop everything.

PowerShell mirrors exist in `scripts/windows/`. These satisfy the PDF's
`team-up` / `all-up` / `all-down` requirement; we do **not** need to write
new scripts.

### C.7 Git & delivery
- Fork `PolyLife` repo; **no PRs to upstream** (`PolyLife2026/PolyLife`).
- All PRs stay inside our fork (`origin` = `sinasadeghi83/PolyLife`).
  Allowed PR targets: **`main`**, **`development`**, or **`feature/*`**.
- Commit format: `[team7] verb: description`
- Every member commits individually, **incrementally** — no end-of-project dumps.
- Push at the end of each working session, and at least **24 h before deadline**.
- Add a CI job for our team to `.github/workflows/ci.yml` that builds our
  image and runs our tests.

### C.8 Final delivery
- Clean code, short functions, descriptive names.
- Meaningful commit history.
- Final archive uploaded as `P3_7_StudNum1_StudNum2_StudNum3.zip`.
- Working `docker-compose.yml` + working Gateway are **mandatory** for
  acceptance.

---

## Section D — Acceptance Criteria (recap from PDF §موارد تحویلی این بخش)

- [ ] Clean, well-named code.
- [ ] Meaningful commits (English, `[team7]` prefix).
- [ ] Final zip uploaded by 28 Tir 1405, 23:59.
- [ ] `docker-compose.yml` actually runs our service.
- [ ] Nginx gateway actually routes requests.
- [ ] All team members can verbally explain every part.
- [ ] All Jira tasks assigned, completed, and visible.

> Detailed checklist: `09_implementation_checklist.md`.