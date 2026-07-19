# Phase 3 — Microservice Architecture & Decisions

This document records the **decisions** we make about how our two services
(Chat with Coach + Reserve Coach) integrate with the rest of PolyLife. It is
the place to look up "why did we choose X?".

> Cross-references: phase breakdown in `01_phase3_breakdown.md`, DB in
> `06_database_design.md`, API in `07_api_endpoints.md`.

---

## 1. Global request flow (from PDF §۳)

The actual implementation (visible in `core/auth_views.py` + each team's
`gateway.conf`) uses Nginx **`auth_request` forward-auth**:

```
Browser
   │
   ▼
[ Team Gateway (Nginx) ] ──── our gateway
   │
   │   1. receives request with user's session cookie or Authorization header
   │   2. for every /api/ request, makes an internal subrequest:
   │        GET http://core:8000/api/verify
   │        (forwards the original Authorization / Cookie)
   │   3. Core's `/api/verify` returns:
   │        200 + X-User-Id, X-User-Username  → request is allowed
   │        401                                → redirect to login
   │   4. Nginx extracts X-User-* from the subrequest response and
   │      sets them on the upstream request to our backend
   ▼
[ Team Backend Service ] ──── US
   │
   ▼
[ Team Database ]
```

> **Important**: PDF says our backend must be reachable even when Core is
> down. In practice, the gateway will return 401 for every `/api/` request
> while Core is down, but the backend container itself still starts. This is
> the documented behaviour; we don't need to "fix" it.
>
> **Important (2):** Our backend **never** decodes JWT. The gateway's
> `auth_request_set` lines in `gateway.conf` literally copy Core's response
> headers into the proxied request. Trust those headers — that's what the
> PDF says, and the repo's `teams/team7/README.md` repeats it.

## 2. Tech-stack decisions

### 2.1 Backend language/framework
We are **free to choose any tech stack other than Django** for our backend, but
must talk to Core via **gRPC or RabbitMQ**.

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **FastAPI (Python)** | Fast iteration, async, Pydantic models, easy tests. We already know Python from coursework. | Needs careful async handling for the chat websockets. | **✓ chosen** |
| Django | Same stack as Core, easier integration | PDF discourages it; we'd compete with Core. | ✗ |
| Node.js + NestJS | Native WebSockets, large ecosystem | Adds a second runtime to maintain. | ✗ (deferred) |
| Go | Excellent concurrency | Steep learning curve in 2 weeks. | ✗ (deferred) |

### 2.2 Database
PDF allows the team DB to be any engine. We use:
- **PostgreSQL 16** in a container — relational, FK support, JSONB for
  flexible message metadata, mature migrations (Alembic).
- Redis (separate container) — pub/sub for chat notifications and rate-limiting.

### 2.3 Chat transport
Two viable transports:

| Transport | Tradeoff |
|-----------|----------|
| WebSocket (FastAPI `websockets`) | Real-time push, lower latency, holds a connection per user. |
| Server-Sent Events + REST send | Simpler, scales horizontally, but push latency is higher. |

**Decision:** **WebSocket** for chat (P1 explicitly says "when a new message
arrives, notify the user"), REST for everything else.

### 2.4 Inter-service communication with Core
- We will use **REST** where we only need to call Core from our backend (rare —
  we mostly receive auth context, we don't query Core).
- If we ever need to push events to other teams (e.g. notify social-feed when a
  reservation completes), we'll publish to a **RabbitMQ** exchange whose
  topology will live in `infra/rabbitmq/`.

### 2.5 Frontend
Plain Django templates are an option. To get the **bonus points** the PDF
mentions for a separate frontend, we'll build a minimal HTML/JS page that hits
our API. Keeps things simple, no React build pipeline.

## 3. Docker layout

### 3.1 What the repo already gives us

Looking at the actual fork (`github.com/sinasadeghi83/PolyLife`), the team-7
folder is a **Django app skeleton** plus a working Nginx gateway:

```
teams/team7/                     (already exists in the fork)
├── apps.py
├── models.py                     ← Django ORM skeleton (we will replace)
├── views.py                      ← empty placeholder
├── urls.py                       ← empty placeholder
├── admin.py
├── tests.py
├── migrations/                   ← Django migrations folder
├── Dockerfile                    ← builds the Django app on port 8000
├── docker-compose.yml            ← only gateway active; backend + db commented out
├── gateway.conf                  ← working Nginx forward-auth config
├── .env.example                  ← canonical env vars (see §4)
└── run.sh / run.ps1              ← per-team start helpers
```

> Because we chose a **non-Django** stack (FastAPI), we will **replace** the
> Django skeleton files (`models.py`, `views.py`, `urls.py`, `admin.py`,
> `tests.py`, `migrations/`) with our own FastAPI app. The folder layout
> (`teams/team7/backend/` etc.) below is our **target** layout — when we
> start implementing, the old Django files go away.

### 3.2 Target layout (what we'll build)

```
teams/team7/
├── backend/                       ← our FastAPI service
│   ├── Dockerfile                ← installs only OUR deps
│   ├── requirements.txt          ← team-local, NOT the root one
│   ├── pyproject.toml            ← tooling config
│   ├── alembic.ini               ← DB migrations
│   └── app/
│       ├── main.py               ← FastAPI app factory
│       ├── api/                  ← routers (chat, reserve)
│       ├── core/                 ← settings, db, auth helpers
│       ├── models/               ← SQLAlchemy ORM
│       ├── schemas/              ← Pydantic
│       ├── services/             ← business logic
│       └── tests/
├── gateway/
│   └── nginx.conf                ← extends the template (see §1)
├── db/
│   └── init.sql                  ← seed data for dev
└── docker-compose.yml            ← backend + postgres + redis + nginx
```

> We **never** touch the top-level `requirements.txt`, root `Dockerfile`,
> root `docker-compose.yml`, or root `settings.py` (PDF §۳.۳: changing the
> global DB engine is forbidden).
> Anything we need goes into `teams/team7/backend/requirements.txt` and our
> own `Dockerfile`.

## 4. Environment variables (`.env` → copied from `example.env`)

The repo's `teams/team7/.env.example` defines the canonical set. We extend,
not replace, this file (we never remove existing keys; we may add new ones
like `URL_REDIS`).

| Variable | Purpose | Example (from `.env.example`) |
|----------|---------|-------------------------------|
| `TEAM_PORT` | Host port the team-7 gateway listens on | `9107` |
| `CORE_BASE_URL` | Where Core lives inside `polylife_net` (used by the Nginx gateway for forward-auth) | `http://core:8000` |
| `POSTGRES_DB` | DB name | `team7` |
| `POSTGRES_USER` | DB user | `team7_user` |
| `POSTGRES_PASSWORD` | DB password (dev-only) | `team7pass` |
| `DATABASE_URL` | Full connection string the backend reads | `postgres://team7_user:team7pass@db:5432/team7` |
| `DJANGO_SECRET_KEY` | Kept from the Django template; harmless for FastAPI | `dev-only-team7-secret-change-me` |
| `URL_REDIS` | **New — we add this** when we wire Redis pub/sub for chat | `redis://redis:6379/0` |
| `LOG_LEVEL` | **New** — log level | `info` |

> **Naming corrections** (vs the very first draft of this doc):
> - The PDF calls it `URL_BASE_CORE` but the actual repo variable is `CORE_BASE_URL`. We follow the repo.
> - The PDF calls it `URL_DATABASE` but the actual repo variable is `DATABASE_URL`. We follow the repo.

`.env` is **git-ignored**. `.env.example` is committed. The `run.sh` /
`start-team.sh` script copies `.env.example` → `.env` the first time.

## 5. Networking

- All our containers attach to the shared network **`polylife_net`** (created
  by Core's `docker-compose.yml`; our `docker-compose.yml` declares it as
  `external: true` with `name: polylife_net`).
- Inside that network we can reach `core:8000`, `db:5432` by name.
- **Host port for team 7's gateway: `9107`** (see `.env.example`:
  `TEAM_PORT=9107`). The PDF's example used `9101` because that's team-1's
  default; we follow the actual repo, not the example.
- The PDF says our backend must be reachable even when Core is down — in
  practice, the Nginx `auth_request` will reject every protected request
  with `401` until Core is back, but the gateway itself and our backend
  will still start (per the template's resolver-based proxy_pass).

## 6. Helper scripts (PDF §۶.۳)

The repo already provides working scripts under `scripts/bash/`. We use them
**as-is** — no need to write new ones. We may add team-specific aliases if
we want, but the canonical entry points are:

| PDF requirement | Existing script | What it does |
|-----------------|-----------------|--------------|
| `team-up` | `scripts/bash/start-team.sh 7` | Bring up **only team 7** (gateway + your backend + db). Auto-creates `.env` from `.env.example` on first run. |
| `all-up` | `scripts/bash/start-core.sh` then `scripts/bash/start-all-teams.sh` | Bring up the core **and** all 8 teams (ports 9101..9108). |
| `all-down` | `scripts/bash/stop-all.sh` | Tear down every container (volumes preserved). |

> Bash scripts are mirrors of the PowerShell scripts in `scripts/windows/`.
> The PDF is satisfied either way — same behaviour, different OS shell.

## 7. CI (PDF §تست و CI)

`.github/workflows/ci.yml` already runs:
- `python manage.py test core` (Core tests)
- Builds the full project image.

We **must** add a separate job that:
1. Builds our `teams/team7/backend` image.
2. Runs our pytest suite inside it.

Pseudo-code:

```yaml
jobs:
  team-7-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build team-7 backend
        run: docker build -t team-7-backend teams/team7/backend
      - name: Run team-7 tests
        run: |
          docker run --rm team-7-backend pytest -q
```

A green tick here is **mandatory** for acceptance.

## 8. Open architectural questions

| Question | Owner | Decision deadline |
|----------|-------|-------------------|
| Do we need a queue for offline-message delivery? | Sina N. | Before Sprint 2 |
| Do we use Redis Streams or RabbitMQ for events? | Sina S. | Before Sprint 1 review |
| How do we surface coach availability across both services? | Amirali | Before Sprint 2 |

> Add new questions here when they come up; resolve them in writing, not in DMs.