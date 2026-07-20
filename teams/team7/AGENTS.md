# AGENTS.md — Team 7 (Chat with Coach + Reserve Coach)

> **Audience:** AI coding agents (and humans) who will work in this folder.
> **Owners:** Sina Sadeghi (lead), Sina Negahban, Amirali Rahimi. Group 7.
>
> The detailed plan, decisions, and checklists live in
> [`.agents/`](./.agents/) — start with `.agents/README.md`, then read
> `00_team_overview.md` and `02_architecture_decisions.md` before touching
> code.

---

## 1. What this folder is

We are building **two microservices** for the PolyLife platform:

- **Chat with Coach** — real-time text chat between a user and a coach
  (WebSocket, presence, typing indicators, attachments).
- **Reserve Coach** — book a coaching session from a coach's published
  availability slots, plus a 1–5 rating system.

Both services share the same FastAPI backend container but live in separate
routers (`/api/chat/...` and `/api/reserve/...`).

## 2. Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | **FastAPI** (Python 3.12) | Non-Django, async, Pydantic validation, auto OpenAPI. |
| ORM | SQLAlchemy 2.x (async) + Alembic | Migrations, FK, JSONB. |
| DB | PostgreSQL 16 | Per-repo convention; env vars in `.env.example`. |
| Cache / pub-sub | Redis 7 | Chat fan-out across workers, rate limiting. |
| Transport (chat) | WebSocket | Real-time push required by P1. |
| Tests | pytest + httpx + pytest-asyncio | Standard for FastAPI. |
| Gateway | Nginx (template provided) | `auth_request` forward-auth to Core. |
| Package manager | **uv** | PEP 668-friendly, lockfile-pinned, ~10-100x faster than pip; single source of truth is `teams/team7/backend/pyproject.toml` + `uv.lock`. |

**Package manager rule:** this team uses **uv** for ALL Python
dependency work in `teams/team7/backend/`. Do not create
`requirements.txt`, do not run `pip install`, do not use `poetry` or
`pipenv`. If you need a new dep:

```bash
cd teams/team7/backend
uv add <package>          # runtime dep
uv add --dev <package>    # dev-only dep (pytest, ruff, etc.)
uv lock                   # regenerate uv.lock
uv sync                   # install into the local .venv
```

The Docker build (`teams/team7/backend/Dockerfile`) is a multi-stage
uv build and runs `uv sync --frozen` against the same lockfile, so
local and container installs stay in lockstep.

**Forbidden** by the PDF: editing the top-level `requirements.txt`,
`Dockerfile`, `docker-compose.yml`, or `settings.py`. All deps go into
`teams/team7/backend/pyproject.toml` (and the lockfile uv generates
beside it).

## 3. Folder layout (target after Sprint 1)

```
teams/team7/
├── AGENTS.md                <- you are here
├── README.md                <- user-facing run instructions
├── .agents/                 <- planning docs (do not delete)
├── backend/                 <- our FastAPI service (Sprint 1 ticket SCRUM-4)
│   ├── Dockerfile
│   ├── pyproject.toml       <- dep manifest (managed by `uv`)
│   ├── uv.lock              <- pinned dep graph (committed; reproducible builds)
│   ├── .python-version      <- 3.12 (consumed by uv)
│   ├── alembic.ini
│   └── app/
│       ├── main.py
│       ├── api/             ← chat + reserve routers
│       ├── core/            ← settings, db session, X-User-Id dep
│       ├── models/          ← SQLAlchemy
│       ├── schemas/         ← Pydantic
│       ├── services/        ← business logic
│       └── tests/
├── db/
│   ├── schema.dbml          ← ER diagram source (DBML)
│   ├── er-diagram.png
│   ├── er-diagram.pdf
│   ├── description.md       ← exported from .agents/03_database_design.md
│   └── init.sql             ← ≥ 2 sample rows per table
├── docker-compose.yml       ← already in repo; we uncomment backend+db, add redis
├── gateway.conf             ← already in repo; we add /api/chat/ws route
├── .env.example             ← already in repo; we add URL_REDIS
├── run.sh / run.ps1         ← already in repo, unchanged
```

## 4. Hard rules (read first, then code)

1. **Never decode JWTs.** Trust the `X-User-Id` and `X-User-Username`
   headers that the gateway forwards. See
   `.agents/02_architecture_decisions.md` §1 for the exact flow.
2. **Never touch the top-level `requirements.txt`, `Dockerfile`,
   `docker-compose.yml`, or `settings.py`.** PDF §۳.۳ forbids it.
3. **All env vars come from `.env`** (auto-copied from `.env.example` on
   first run by `run.sh`). Don't hardcode URLs or secrets.
4. **All DB tables have** `id`, `created_at`, `updated_at`, `is_deleted`
   columns. snake_case, English, descriptive names. Indexed on filtered
   columns. FK between related tables.
5. **Commit message format:** `<gitmoji> [team7] <verb>: <description>` —
   see `.agents/07_git_workflow.md` §3.
6. **Branch names:** `feature/team-7-<scope>-<short>`,
   `bugfix/team-7-<short>`, `docs/team-7-<topic>`. PRs target
   `feature` or `development` only (not `main`).
7. **Never `git push -f`.** The PDF bans it; merge conflicts must be
   resolved manually.

## 5. Running locally

```bash
# 0. Add upstream once per clone (only if your clone doesn't have it)
git remote add upstream git@github.com:PolyLife2026/PolyLife.git

# 1. Always pull upstream before starting
git pull upstream main

# 2. Start the core (must be up before any team)
scripts/bash/start-core.sh

# 3. Start this team
scripts/bash/start-team.sh 7

# 4. Open http://localhost:9107  (you should see the gateway placeholder)
```

For shell-style live logs of our backend:
```bash
cd teams/team7
docker compose logs -f backend
```

For an interactive shell in our backend container:
```bash
docker compose exec backend bash
```

## 6. How an agent should use this repo

1. **Read first:**
   - `.agents/00_team_overview.md` (who we are, what we're building)
   - `.agents/02_architecture_decisions.md` (the "why" behind every choice)
   - `.agents/03_database_design.md` (the schema)
   - `.agents/04_api_endpoints.md` (the contracts)
2. **Pick a Jira ticket** (key prefix `SCRUM`, e.g. `SCRUM-7`). If none
   matches your task, **create one** in the
   `sinasadeghi83.atlassian.net` project.
3. **Create a branch** from `main`:
   `git checkout -b feature/team-7-<scope>-<short>`
4. **Make focused commits** with the gitmoji + `[team7]` format.
5. **Push daily** (PDF §زمان‌بندی Push کردن) and **at least 24 h before
   the deadline**. End every working session with a push.
6. **Open a PR to `feature` or `development`**, never to `main`.
7. **Before requesting review**, run the smoke test in
   `.agents/08_implementation_checklist.md` §G and paste the output.

## 7. Jira wiring (status as of 2026-07-19)

> **Status:** Jira site exists at `sinasadeghi83.atlassian.net` (Sina S.
> is site owner/admin). The Scrum project **`SE1 Team 7` (key `SCRUM`)** was
> created on 2026-07-19 via the Atlassian REST API. It is **next-gen /
> team-managed** (style verified via `GET /rest/api/3/project/SCRUM`).
>
> The **17 sprint tickets** (SCRUM-1, 2, 4–10 from Sprint 1 + SCRUM-11–18
> from Sprint 2) were created on 2026-07-19 via the Atlassian REST API.
> All are in the `Sprint 1` or `Sprint 2` column (To Do) with the right
> assignees and labels. Current explicit ownership changes include
> `SCRUM-4` and `SCRUM-5` assigned to Sina Sadeghi, and `SCRUM-14` assigned
> to Amirali Rahimi. The Summary prefix on every Jira issue matches its
> actual issue key.
>
> **Note on key numbering:** The intended ticket sequence had no
> SCRUM-3 because the helper-scripts ticket was dropped. The Jira internal
> counter assigned keys sequentially as tickets were created, so the actual
> project keys are SCRUM-1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
> 16, 17, 18.
> Each ticket's **summary** uses its actual Jira key (e.g. Jira key
> `SCRUM-4` has summary `[SCRUM-4] Backend skeleton (FastAPI) + Dockerfile +
> compose`).
>
**Recovered from an earlier mistake:** an intermediate project
`PolyLife — Team 7` with key `PL7` was briefly created and then deleted
because the user clarified to use the pre-existing `SE1 Team 7` (key
`SCRUM`) space. All ticket references in these docs now use `SCRUM`.

> **Runtime requirement for further Jira automation:** the
> `ATLASSIAN_API_KEY` environment variable must be set in the agent's
> runtime. It is only available inside the **Hermes** environment
> (Sina S.'s AI-agent shell); it is **not** in the repo, in `.env`, or
> on any teammate's machine. Any agent that does not see this variable
> in its shell must **not** attempt to create or modify Jira issues
> — it should treat the 17 tickets in `SE1 Team 7` / `SCRUM` as the
> source of truth and have the user do new wiring manually at
> <https://sinasadeghi83.atlassian.net/jira/software/projects/SCRUM/boards/1>.

### 7.1 Pre-flight check (mandatory before any Jira API call)

```bash
# 1. Token is present and non-empty
[ -n "$ATLASSIAN_API_KEY" ] || { echo "FATAL: ATLASSIAN_API_KEY not set"; exit 1; }
echo "Token length: ${#ATLASSIAN_API_KEY} chars"   # expect 192 + "ATAT" prefix

# 2. Token is valid against the site
curl -fsS -u "sina.sadeghi83@gmail.com:${ATLASSIAN_API_KEY}" \
  "https://sinasadeghi83.atlassian.net/rest/api/3/myself" \
  -H "Accept: application/json" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d.get('displayName'))"
```

- If step 1 fails → **stop and tell the user** ("`ATLASSIAN_API_KEY` is
  not present in this environment; I cannot talk to Jira. If you want
  this wired automatically, set the token in the runtime's env.").
- If step 2 fails (401) → **stop and tell the user** ("Token is set but
  rejected; it may be expired or revoked. Generate a new one at
  <https://id.atlassian.com/manage-profile/security/api-tokens>.").

### 7.2 What "no env access" looks like in practice

- A teammate's laptop: no `ATLASSIAN_API_KEY` in their shell — the
  agent should treat the 17 existing tickets as the source of truth and
  ask the user to do any new wiring manually via the Jira web UI.
- GitHub Actions / CI: no `ATLASSIAN_API_KEY` in the runner env — the
  agent should **not** try to create or modify issues from CI; failures
  of this kind should be flagged to Sina S. for manual handling.
- A different AI agent's sandbox (e.g. some other Claude / GPT
  session): the variable is per-runtime, not per-repo, so the same
  `sinasadeghi83/PolyLife` checkout in a different sandbox will not
  see it. The agent should say so explicitly rather than silently
  failing.

### 7.3 Token rotation

- If a new token is generated, the old one stops working immediately
  (Atlassian API tokens are **not** reversible).
- The agent must **not** log, echo, or persist the token value anywhere
  — read it from the env, use it, forget it.
- Token regeneration URL:
  <https://id.atlassian.com/manage-profile/security/api-tokens>.

## 8. Open questions (resolve before coding the relevant ticket)

| # | Question | Owner | Blocking ticket |
|---|----------|-------|-----------------|
| 1 | Do we need a queue for offline-message delivery? | Sina N. | Sprint 2 chat backend |
| 2 | Do we use Redis Streams or RabbitMQ for events? | Sina S. | Sprint 2 chat backend |
| 3 | How do we surface coach availability across both services? | Amirali | Sprint 2 reserve backend |

> Add new questions here when they come up; resolve them in writing, not
> in DMs.

## 9. How an agent should update this file

- **When you make an architectural decision**, edit the relevant section
  in `.agents/02_architecture_decisions.md` and add a short note here
  pointing to it.
- **When you finish a sprint**, update the Jira status section above and
  the sprint backlogs in `.agents/06_task_assignment.md`.
- **When the stack changes** (e.g. we pick a different ORM), update §2
  here AND the corresponding section in
  `.agents/02_architecture_decisions.md`.
