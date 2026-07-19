# Task Assignment — who does what

This document allocates the Phase 3 work between the three of us. The
assignment is **a starting point**; we renegotiate weekly in the scrum-master
meeting based on velocity.

> Cross-references:
> - Jira workflow → `05_jira_setup.md`
> - Architecture → `02_architecture_decisions.md`
> - DB → `03_database_design.md`
> - API → `04_api_endpoints.md`

---

## 1. Team members

| Initials | Name | Backend / Frontend / Infra |
|----------|------|----------------------------|
| **SS** | Sina Sadeghi | Backend lead |
| **SN** | Sina Negahban | Backend + DB |
| **AR** | Amirali Rahimi | Infra + Frontend |

> Scrum master (assigned by TA) supervises; they're not a doer on this team.

## 2. Workstreams

We split the work into **three parallel workstreams** with **clear interfaces**
so we can work independently without blocking each other. The interfaces are
in `02_architecture_decisions.md` (routes) and `03_database_design.md` (schema).

### 2.1 Workstream A — Backend / Chat with Coach
**Owner:** Sina Sadeghi (lead), Sina Negahban (DB-side support)

Concrete deliverables:
- [ ] FastAPI project skeleton + settings + db session factory.
- [ ] SQLAlchemy models for `chat_thread`, `chat_message`, `message_attachment`.
- [ ] Alembic migrations for chat tables.
- [ ] REST routers: threads, messages, attachments (see `04_api_endpoints.md` §1.1).
- [ ] WebSocket endpoint `/chat/ws` with presence + typing events.
- [ ] Redis pub/sub for cross-worker WebSocket fan-out.
- [ ] Pytest suite (unit + integration).
- [ ] `X-User-Id` middleware/dependency.

### 2.2 Workstream B — Backend / Reserve Coach
**Owner:** Sina Negahban (lead), Sina Sadeghi (review)

Concrete deliverables:
- [ ] SQLAlchemy models for `coach_profile`, `coach_availability`,
      `appointment`, `coach_rating`.
- [ ] Alembic migrations for booking tables.
- [ ] REST routers: coaches, availability, appointments, ratings
      (see `04_api_endpoints.md` §2).
- [ ] Atomic booking flow (slot → booked; no double-booking).
- [ ] Pytest suite, including the concurrency test for double-booking.
- [ ] `X-User-Id` middleware/dependency (shared with Workstream A).

### 2.3 Workstream C — Infra & Frontend
**Owner:** Amirali Rahimi

Concrete deliverables (revised after inspecting the actual fork):

- [ ] `teams/team7/backend/Dockerfile` — installs only team-local deps (FastAPI + SQLAlchemy + asyncpg + alembic + redis + pytest).
- [ ] `teams/team7/backend/requirements.txt` — pinned versions.
- [ ] `teams/team7/docker-compose.yml` — uncomment `backend` + `db`, add `redis`; ensure the gateway stays on `polylife_net` as `external: true`.
- [ ] `teams/team7/gateway/nginx.conf` — extend the existing forward-auth template with WebSocket upgrade headers for `/api/chat/ws`.
- [ ] `teams/team7/.env.example` — add `URL_REDIS` (already documents `CORE_BASE_URL`, `DATABASE_URL`).
- [ ] CI job added to `.github/workflows/ci.yml` (build + test).
- [ ] Minimal HTML/JS frontend (bonus) — coach list, booking, chat window.
- [ ] README updates: how to run, env vars, architecture overview.

> **No need to write `team-up`/`all-up`/`all-down` scripts** — the repo
> already provides `scripts/bash/start-team.sh`, `scripts/bash/start-all-teams.sh`,
> `scripts/bash/stop-all.sh`, etc. We use them as-is.

## 3. Cross-cutting responsibilities

These are shared by everyone; no one is the sole owner.

| Area | Everyone |
|------|----------|
| Code review | At least **one teammate** approves every PR before merge. |
| Jira hygiene | Every member updates their tickets daily. |
| Push frequency | Every session ends with a push (PDF §زمان‌بندی Push کردن). |
| Documentation | Whoever changes code also updates `ai_docs/` if the change affects public behaviour. |
| Tests | Whoever writes a feature writes its tests (TDD preferred). |

## 4. Sprint 1 priorities (load-balanced)

Sprint 1 must finish with **infra working** and **at least one happy-path
endpoint per service**. Story-point estimates in parens.

| # | Title | Owner | Points |
|---|-------|-------|--------|
| SCRUM-1 | Verify fork, add `upstream` remote, invite teammates as collaborators | AR | 1 |
| SCRUM-2 | Create Jira board with Testing column | AR | 1 |
| SCRUM-4 | Backend skeleton (FastAPI) + Dockerfile + compose | SS | 3 |
| SCRUM-5 | Postgres + Redis services in compose + update `.env.example` | SS | 2 |
| SCRUM-6 | DB schema (all tables) + Alembic migrations | SS | 5 |
| SCRUM-7 | `X-User-Id` dependency + smoke test | SS | 2 |
| SCRUM-8 | Chat: list/create threads | SS | 3 |
| SCRUM-9 | Reserve: list/create availability | SN | 3 |
| SCRUM-10 | Nginx gateway: extend with WebSocket route for `/api/chat/ws` | AR | 3 |

> The helper-scripts ticket is **dropped** — `scripts/bash/*.sh` already exist
> and the PDF's `team-up`/`all-up`/`all-down` map directly to them. See
> `02_architecture_decisions.md` §6.

**Total: 23 points** (Sprint 1; helper-scripts ticket removed).

## 5. Sprint 2 priorities (preview)

| # | Title | Owner | Points |
|---|-------|-------|--------|
| SCRUM-11 | Chat WebSocket + Redis pub/sub | SS | 8 |
| SCRUM-12 | Reserve atomic booking + double-book test | SN | 5 |
| SCRUM-13 | Ratings endpoint | SN | 3 |
| SCRUM-14 | Coach online status endpoint | AR | 2 |
| SCRUM-15 | Attachments upload | AR | 3 |
| SCRUM-16 | Frontend (HTML/JS) covering both flows | AR | 5 |
| SCRUM-17 | CI job for our team | SN | 2 |
| SCRUM-18 | README + final smoke tests | AR | 3 |

## 6. Conflict resolution

If two members need to touch the same file simultaneously:
1. Whoever owns the workstream owns the file.
2. The other member opens a PR and asks the owner to review.
3. If conflict is repeated, raise it at the next scrum-master meeting.

If a member is blocked for >24 hours, escalate in the team channel.

## 7. Loading the team over time

| Week | Sina S. | Sina N. | Amirali |
|------|---------|---------|---------|
| Sprint 1 (heavy infra) | 70 % chat backend, 30 % cross-cutting | 70 % reserve backend, 30 % cross-cutting | 100 % infra |
| Sprint 2 (heavy features) | 60 % chat, 40 % review | 60 % reserve, 40 % review | 40 % infra/frontend, 60 % frontend |

> Sprint 2 puts more weight on application code; we balance it so no one
> person owns the whole vertical.