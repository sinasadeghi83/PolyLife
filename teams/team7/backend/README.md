# team-7-backend

FastAPI backend for **PolyLife Team 7** — combines two microservices in one
container:

- **Chat with Coach** — real-time WebSocket chat (`/api/chat/...`)
- **Reserve Coach** — booking flow + 1–5 ratings (`/api/reserve/...`)

> **Status:** Sprint 1 skeleton, ticket **`SCRUM-4`** (Backend skeleton
> (FastAPI) + Dockerfile + compose). Skeleton only — no business endpoints
> yet. The `/healthz` probe and the SQLAlchemy/Alembic/Pydantic-settings
> plumbing are wired and tested.

---

## 1. Stack

| Layer | Choice |
|-------|--------|
| Runtime | Python 3.12 |
| Web framework | FastAPI (async) |
| ASGI server | Uvicorn (`[standard]`) |
| ORM / migrations | SQLAlchemy 2.x (async) + Alembic |
| DB driver | asyncpg → PostgreSQL 16 |
| Cache / pub-sub | redis-py (Sprint 2) |
| Settings | pydantic-settings, reads `.env` |
| Tests | pytest + pytest-asyncio + httpx |
| Lint / format | ruff |
| Package manager | **uv** (`pyproject.toml` + `uv.lock`, no `requirements.txt`) |

---

## 2. Hard rules this service obeys

Carried over from [`../AGENTS.md`](../AGENTS.md) §4:

1. **Never decode JWTs.** The gateway authenticates and forwards
   `X-User-Id` / `X-User-Username`. The dependency in
   `app/core/security.py` trusts those headers — it does not import `jwt`
   or any token library.
2. **Never edit root `requirements.txt` / `Dockerfile` / `docker-compose.yml`
   / `settings.py`.** All dependencies live here in `pyproject.toml`.
3. **All env vars come from `.env`** (copied from `../.env.example` on
   first `run.sh` run). No hardcoded URLs or secrets in code.
4. **Commit message format:** `<gitmoji> [team7] <verb>: <description>`
   with a `SCRUM-NN` trailer — see `../.agents/07_git_workflow.md` §3.

---

## 3. Quick start

### 3.1 Local (with uv)

```bash
# from this directory
uv sync                       # installs into ./.venv from uv.lock
uv run pytest -q              # runs the smoke test (no DB required)
uv run uvicorn app.main:app --reload --port 8000
# → GET http://localhost:8000/healthz  →  {"status":"ok"}
```

Add or upgrade a dependency:

```bash
uv add <package>              # runtime
uv add --dev <package>        # dev-only
uv lock                       # regenerate uv.lock
uv sync                       # apply
```

### 3.2 Inside Docker

```bash
# from teams/team7 (the team root)
docker compose build backend
docker compose run --rm backend pytest -q      # smoke test in-container
docker compose up backend                      # serve on :8000 behind the gateway
```

The `Dockerfile` is a multi-stage uv build (`python:3.12-slim`) that runs
`uv sync --frozen` against the committed `uv.lock`, so local and
container installs stay in lockstep.

---

## 4. Environment variables

These are declared in `app/core/config.py` via `pydantic-settings`. All
values come from `.env` at the team root; defaults are dev-only.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | asyncpg DSN, e.g. `postgresql+asyncpg://team7_user:...@db:5432/team7` |
| `URL_REDIS` | redis URL, e.g. `redis://redis:6379/0` (added Sprint 2) |
| `CORE_BASE_URL` | Core auth base URL (for any future calls from us to Core) |
| `LOG_LEVEL` | log level; defaults to `INFO` |

> See [`../.env.example`](../.env.example) for the canonical list. Add new
> vars to both `.env.example` (committed) and `.env` (git-ignored) on
> first run.

---

## 5. Folder layout

```
backend/
├── Dockerfile              multi-stage uv build (slim base)
├── pyproject.toml          deps + tool config (pytest, ruff)
├── uv.lock                 pinned dep graph (committed)
├── .python-version         3.12
├── .gitignore              ignores .venv, .pytest_cache, __pycache__
├── .dockerignore           keeps the build context small
├── alembic.ini             migration config (sqlalchemy.url read from env.py)
├── alembic/
│   ├── env.py              async env, reads settings.DATABASE_URL
│   ├── script.py.mako      migration template
│   └── versions/.gitkeep   placeholder
└── app/
    ├── __init__.py
    ├── main.py             FastAPI factory + GET /healthz
    ├── core/
    │   ├── __init__.py
    │   ├── config.py       Settings (pydantic-settings)
    │   ├── db.py           async engine + session factory + get_db()
    │   └── security.py     X-User-Id / X-User-Username deps
    ├── api/                (empty — wired in SCRUM-8 / SCRUM-9)
    ├── models/             (empty — wired in SCRUM-6)
    ├── schemas/            (empty — wired in SCRUM-8 / SCRUM-9)
    ├── services/           (empty — wired in Sprint 2)
    └── tests/
        ├── __init__.py
        ├── conftest.py     httpx AsyncClient fixture (no DB)
        └── test_health.py  GET /healthz → 200 + {"status":"ok"}
```

---

## 6. Smoke test (mandatory before requesting review)

```bash
# 1. lint
docker run --rm -v "$PWD":/app -w /app \
  ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  sh -c "uv sync --frozen --quiet && uv run ruff check ."

# 2. tests
docker build -t team-7-backend .
docker run --rm team-7-backend pytest -q

# 3. live health check (after `docker compose up backend`)
curl -fsS http://localhost:9107/healthz   # via the team-7 gateway
# expect: {"status":"ok"}
```

Both steps 1 and 2 must exit `0`. Step 3 is checked during the integration
smoke in [`../.agents/08_implementation_checklist.md`](../.agents/08_implementation_checklist.md) §G.

---

## 7. What is *not* in this service yet

Explicitly out of scope for `SCRUM-4`; covered by later tickets:

| Ticket | Adds |
|--------|------|
| `SCRUM-5`  | `postgres` + `redis` services in compose; `URL_REDIS` in `.env.example` |
| `SCRUM-6`  | All SQLAlchemy models + Alembic migration content |
| `SCRUM-7`  | Wider integration tests of the `X-User-Id` dependency |
| `SCRUM-8`  | `chat_thread` / `chat_message` / `chat_attachment` routers |
| `SCRUM-9`  | `coach_*` / `appointment` / `coach_rating` routers |
| `SCRUM-10` | Nginx gateway extension for `/api/chat/ws` WebSocket upgrade |
| `SCRUM-11` | Chat WebSocket endpoint + Redis pub/sub |
| `SCRUM-12` | Atomic booking + double-booking test |
| `SCRUM-17` | CI job that builds this image and runs `pytest -q` |

> Do not implement any of the above in the SCRUM-4 PR. Keep the PR diff
> strictly inside this `backend/` folder (see delegation plan
> `.hermes/plans/scrum-4-delegation.md`).

---

## 8. References

- Team rules — [`../AGENTS.md`](../AGENTS.md)
- Architecture decisions — [`../.agents/02_architecture_decisions.md`](../.agents/02_architecture_decisions.md)
- API contracts (forthcoming) — [`../.agents/04_api_endpoints.md`](../.agents/04_api_endpoints.md)
- DB schema (forthcoming) — [`../.agents/03_database_design.md`](../.agents/03_database_design.md)
- Sprint-1 backlog — [`../.agents/06_task_assignment.md`](../.agents/06_task_assignment.md) §4
- Acceptance / smoke — [`../.agents/08_implementation_checklist.md`](../.agents/08_implementation_checklist.md)
- Jira ticket — `SCRUM-4` in the `SE1 Team 7` (key `SCRUM`) project on
  <https://sinasadeghi83.atlassian.net>