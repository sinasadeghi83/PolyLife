# PolyLife Team 7 — Chat with Coach and Reserve Coach

Team 7 owns two PolyLife capabilities:

- **Chat with Coach** — authenticated conversations between users and coaches,
  with messages, attachments, presence, typing events, and WebSocket delivery.
- **Reserve Coach** — coach profiles and availability, appointment booking, and
  coach ratings.

Both capabilities share one asynchronous FastAPI backend and one Team 7
PostgreSQL database. The service runs behind the shared PolyLife authentication
flow; clients enter through the Team 7 Nginx gateway on
`http://localhost:9107`.

## Current implementation status

The repository currently contains the Sprint 1 foundations:

- FastAPI application and Uvicorn runtime
- SQLAlchemy async models and Alembic migrations for the Team 7 schema
- PostgreSQL and Redis service definitions
- Forwarded-identity dependency for `X-User-Id` and `X-User-Username`
- Public backend liveness endpoint: `GET /healthz`
- Auth dependency smoke endpoint: `GET /meta/auth-smoke`
- Unit tests for health, identity forwarding, models, and schema behavior

The chat and reservation business endpoints documented in
[`.agents/04_api_endpoints.md`](.agents/04_api_endpoints.md) are the target API
contract and are implemented incrementally through the remaining Jira tickets.
Do not assume a documented endpoint exists until its ticket is complete and the
route appears in the generated OpenAPI document.

Live ticket ownership and status are tracked in Jira and mirrored in
[`.agents/06_task_assignment.md`](.agents/06_task_assignment.md).

## Architecture

```text
Browser / API client
        |
        | cookie or Authorization header
        v
Team 7 gateway — Nginx (:9107)
        |
        | auth_request
        +----------------------> PolyLife Core (:8000)
        |                         GET /api/verify
        |                         returns X-User-Id and X-User-Username
        |
        | forwarded identity headers
        v
Team 7 backend — FastAPI (:8000 inside Docker)
        |
        +-----------> PostgreSQL 16
        |
        +-----------> Redis 7
```

Authentication is owned by PolyLife Core. The Team 7 backend **does not decode
JWTs**. Nginx asks Core to verify the original cookie or authorization header,
then forwards the authenticated identity to FastAPI as `X-User-Id` and
`X-User-Username`.

## Technology stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x async |
| Migrations | Alembic |
| Database | PostgreSQL 16 |
| Cache and pub/sub | Redis 7 |
| Validation and settings | Pydantic 2 + pydantic-settings |
| Tests | pytest, pytest-asyncio, HTTPX |
| Linting | Ruff |
| Package management | uv with `pyproject.toml` and `uv.lock` |
| Gateway | Nginx forward-auth through PolyLife Core |

## Repository layout

```text
teams/team7/
├── README.md                 this guide
├── AGENTS.md                 mandatory Team 7 engineering rules
├── .agents/                  architecture, schema, API, Jira, and QA docs
├── .env.example              canonical development configuration
├── docker-compose.yml        gateway, backend, PostgreSQL, and Redis
├── gateway.conf              Nginx forward-auth and proxy configuration
├── run.sh / run.ps1          Team 7 startup wrappers
├── backend/
│   ├── Dockerfile            Python 3.12 multi-stage uv image
│   ├── pyproject.toml        dependencies and tool configuration
│   ├── uv.lock               pinned dependency graph
│   ├── alembic.ini
│   ├── alembic/              migration environment and revisions
│   └── app/
│       ├── main.py           FastAPI application factory
│       ├── api/              HTTP and WebSocket routers
│       ├── core/             settings, DB session, authentication context
│       ├── models/           SQLAlchemy models
│       ├── schemas/          Pydantic request/response schemas
│       ├── services/         business logic
│       └── tests/            automated tests
└── db/                       schema artifacts and seed data
```

## Prerequisites

Install:

- Git
- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker with Docker Compose v2

For the integrated gateway flow, PolyLife Core must be running and the shared
Docker network `polylife_net` must exist. Start Core from the repository root:

```bash
scripts/bash/start-core.sh
```

On Windows PowerShell:

```powershell
scripts\windows\start-core.ps1
```

## Backend development with uv

The most reliable way to develop and test the backend independently is through
uv.

```bash
cd teams/team7/backend
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Check the public liveness endpoint:

```bash
curl -fsS http://localhost:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

The auth smoke route expects identity headers normally supplied by Nginx after
Core authentication. For backend-only development, they can be provided
explicitly:

```bash
curl -fsS http://localhost:8000/meta/auth-smoke \
  -H 'X-User-Id: 42' \
  -H 'X-User-Username: demo-user'
```

Expected response:

```json
{"data":{"id":42,"username":"demo-user"}}
```

Missing identity headers or a non-integer `X-User-Id` produce HTTP 401.
Explicit headers are only a local testing technique; production clients must
not be trusted to choose these values. The gateway overwrites them with the
identity returned by Core.

### Dependency management

All Team 7 Python dependencies belong in `backend/pyproject.toml` and
`backend/uv.lock`:

```bash
cd teams/team7/backend
uv add package-name
uv add --dev development-package
```

Do not create a Team 7 `requirements.txt`, use `pip install`, or edit the
repository-level dependency files.

## Running the Docker stack

From `teams/team7/`, create local configuration once:

```bash
cp .env.example .env
```

Review `.env` before starting. It is ignored by Git and must never be committed.
Then run one of the wrappers:

```bash
./run.sh
```

```powershell
.\run.ps1
```

The wrappers execute `docker compose up --build`. The intended services are:

| Service | Purpose | Network exposure |
|---|---|---|
| `gateway` | Nginx entry point and Core forward-auth | Host port `9107` |
| `backend` | Team 7 FastAPI application | Internal port `8000` |
| `db` | PostgreSQL 16 | Private Team 7 network |
| `redis` | Pub/sub and rate-limit state | Private Team 7 network |

Useful lifecycle commands:

```bash
docker compose config
docker compose ps
docker compose logs -f backend
docker compose down
docker compose down -v   # destructive: also removes Team 7 database data
```

### Current Compose caveat

At the time of this README update, `docker-compose.yml` configures the backend
build context as the Team 7 root, while the actual Dockerfile is
`backend/Dockerfile`. If `docker compose up --build` reports that
`teams/team7/Dockerfile` is missing, use the uv workflow above until the Compose
build context is corrected by its infrastructure ticket. Do not copy or move
the backend Dockerfile as an undocumented workaround.

## Configuration

`.env.example` is the committed template; `.env` is the local runtime file.

| Variable | Purpose | Development default |
|---|---|---|
| `TEAM_PORT` | Host port for the Team 7 gateway | `9107` |
| `CORE_BASE_URL` | Core service used by gateway authentication | `http://core:8000` |
| `POSTGRES_DB` | Team 7 database name | `team7` |
| `POSTGRES_USER` | Team 7 database user | `team7_user` |
| `POSTGRES_PASSWORD` | Development database password | dev-only value |
| `DATABASE_URL` | Backend SQLAlchemy database URL | PostgreSQL service `db:5432` |
| `URL_REDIS` | Redis URL for pub/sub and rate limiting | `redis://redis:6379/0` |
| `LOG_LEVEL` | Backend log level | `info` |
| `DJANGO_SECRET_KEY` | Legacy template variable; not used by FastAPI | dev-only value |

The application converts bare `postgres://` and `postgresql://` database URLs
to SQLAlchemy's `postgresql+asyncpg://` form internally. Never commit real
passwords, tokens, or a populated `.env` file.

## API access

### Implemented backend routes

| Method | Backend path | Authentication | Purpose |
|---|---|---|---|
| `GET` | `/healthz` | Public | Process liveness |
| `GET` | `/meta/auth-smoke` | Forwarded identity headers | Echo verified identity |

FastAPI also exposes OpenAPI and Swagger directly from the backend at
`/openapi.json` and `/docs`. Gateway paths may differ as routing evolves; check
`gateway.conf` and the live OpenAPI document rather than guessing.

### Planned public API families

- `/api/chat/...` — threads, messages, attachments, presence, and WebSocket chat
- `/api/reserve/...` — coaches, availability, appointments, and ratings

The complete target contract, permissions, response envelopes, and error codes
are documented in [`.agents/04_api_endpoints.md`](.agents/04_api_endpoints.md).

## Database migrations

Alembic reads `DATABASE_URL` through the same application settings as FastAPI.
With a reachable PostgreSQL instance:

```bash
cd teams/team7/backend
uv run alembic upgrade head
uv run alembic current
```

Create a migration only after updating the SQLAlchemy models and the database
design documentation:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
```

Review generated migrations before running them. Schema changes must remain
consistent with [`.agents/03_database_design.md`](.agents/03_database_design.md)
and `db/schema.dbml`.

## Testing and quality checks

Before requesting review, run from `teams/team7/backend/`:

```bash
uv sync --frozen
uv run ruff check .
uv run pytest -q
```

When a change affects Docker, PostgreSQL, Redis, Nginx, authentication, or an
end-to-end route, also run the relevant integrated checks in
[`.agents/08_implementation_checklist.md`](.agents/08_implementation_checklist.md).
Report each command as PASS, FAIL, or SKIPPED with a reason. A passing unit test
does not prove that gateway authentication or container networking works.

## Contribution workflow

Before changing Team 7 code:

1. Read [`AGENTS.md`](AGENTS.md).
2. Read the relevant architecture, database, and API documents in `.agents/`.
3. Confirm the Jira ticket, owner, scope, dependencies, and current status in
   [`.agents/06_task_assignment.md`](.agents/06_task_assignment.md) and Jira.
4. Create a focused branch such as
   `feature/team-7-chat-threads` or `docs/team-7-readme`.
5. Add tests and update the matching documentation with behavioral changes.
6. Push the branch and open a PR inside the `sinasadeghi83/PolyLife` fork.
7. Obtain at least one teammate approval before merge.

Important repository rules:

- Never decode JWTs in Team 7 code.
- Never commit secrets or `.env`.
- Never use `git push -f`.
- Never open a Team 7 PR against `PolyLife2026/PolyLife` upstream.
- Do not edit the repository-level `requirements.txt`, `Dockerfile`,
  `docker-compose.yml`, or `polylife/settings.py`.
- Use the required commit format documented in
  [`.agents/07_git_workflow.md`](.agents/07_git_workflow.md).

## Team and project links

| Member | Responsibility |
|---|---|
| Sina Sadeghi | Backend lead and Chat with Coach |
| Sina Negahban | Reserve Coach backend and database support |
| Amirali Rahimi | Infrastructure and frontend |

Project documentation:

- [Team engineering rules](AGENTS.md)
- [Documentation index](.agents/README.md)
- [Architecture decisions](.agents/02_architecture_decisions.md)
- [Database design](.agents/03_database_design.md)
- [API contract](.agents/04_api_endpoints.md)
- [Task ownership and Jira snapshot](.agents/06_task_assignment.md)
- [Git workflow](.agents/07_git_workflow.md)
- [Implementation checklist](.agents/08_implementation_checklist.md)
- [Progress evidence guide](.agents/09_progress_tracking.md)
- [Jira board](https://sinasadeghi83.atlassian.net/jira/software/projects/SCRUM/boards/1)
