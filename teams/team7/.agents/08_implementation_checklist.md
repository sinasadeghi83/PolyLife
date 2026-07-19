# Implementation Checklist — what "done" looks like

> Recap of every PDF requirement for Phase 3 with a checkbox you can mark off
> before uploading. Treat this as the grading rubric.

---

## A. Jira / Process (§بخش اول)

- [ ] Jira account created on TA's site.
- [ ] Scrum project created (team-managed).
- [ ] All three teammates invited.
- [ ] Scrum master invited.
- [ ] Board has columns: `To Do → In Progress → Testing → Done`.
- [ ] Every Story has been split into 2–5 Tasks.
- [ ] Every Task has an assignee.
- [ ] Workload distributed (not one person doing everything).
- [ ] Meeting notes saved in `meetings/`.

## B. Database design (§بخش دوم)

- [ ] Tables cover every field used by Chat with Coach + Reserve Coach.
- [ ] Every table has `id`, `created_at`, `updated_at`, `is_deleted`.
- [ ] snake_case, English, descriptive names.
- [ ] FK constraints between related tables.
- [ ] Indexes on frequently filtered/sorted columns.
- [ ] ER diagram committed in PNG + PDF + DBML.
- [ ] Description document with ≥ 2 sample rows per table committed.
- [ ] Schema is extensible (adding a column won't break anything).

## C. Architecture & integration (§بخش سوم)

- [ ] Our backend runs in Docker.
- [ ] Our services attached to network `polylife_net`.
- [ ] `URL_BASE_CORE` env var wired.
- [ ] `URL_DATABASE` env var wired.
- [ ] `.env` is git-ignored; `.env.example` committed.
- [ ] Top-level `requirements.txt` and `settings.py` are untouched.
- [ ] Team-local `requirements.txt` + our own `Dockerfile` exist.
- [ ] Nginx gateway exists; routes `/api/*` to our backend.
- [ ] Gateway routes the WebSocket path `/api/chat/ws` correctly.
- [ ] Backend reads `X-User-Id` / `X-User-Username` and never decodes JWT.
- [ ] All API endpoints listed in `04_api_endpoints.md` are implemented.
- [ ] WebSocket chat works end-to-end (text + presence + typing).
- [ ] Helper scripts work: `./team-up`, `./all-up`, `./all-down`.
- [ ] Core tests pass (`python manage.py test core`).
- [ ] Our team tests pass (`pytest`).
- [ ] Both backend + frontend images build (`docker build` exits 0).

## D. Code quality (§کدنویسی تمیز)

- [ ] Clear, descriptive names for variables and functions.
- [ ] Functions are short and single-purpose.
- [ ] No dead code, no commented-out blocks.
- [ ] Linter passes (`ruff`/`flake8`).
- [ ] Type hints on public functions (Python).
- [ ] Consistent formatting (Black / Prettier).
- [ ] No hard-coded secrets.

## E. Git & CI (§۸.۴ and §تست و CI)

- [ ] Repo forked; PRs target `development` or `feature`, never `main`.
- [ ] Commits follow `[team7] verb: description` format.
- [ ] No "everything done" or "yesterday changes" commits.
- [ ] Every member committed independently throughout the project.
- [ ] Final push happened ≥ 24 h before deadline.
- [ ] No `git push -f` anywhere in history.
- [ ] Daily `git pull upstream development` was done.
- [ ] CI workflow builds our image (`.github/workflows/ci.yml` updated).
- [ ] CI workflow runs our pytest suite, all green.

## F. Submission package (§موارد تحویلی)

- [ ] Final zip named `P3_7_StudNum1_StudNum2_StudNum3.zip`.
- [ ] Zip contains: source code, ER diagram, description doc, meeting notes.
- [ ] Uploaded by 28 Tir 1405, 23:59.
- [ ] All three teammates can verbally explain every part of the deliverable.

## G. Smoke-test script (run before submission)

```bash
# clean state
scripts/bash/stop-all.sh

# bring up everything
scripts/bash/start-core.sh
sleep 30                                              # wait for core to migrate
scripts/bash/start-all-teams.sh                       # all 8 teams, including us

# 1. health check on our gateway (placeholder HTML is OK before backend is up)
curl -fsS http://localhost:9107/ | head -1

# 2. log in via core to get a JWT
curl -fsS -X POST http://localhost:8000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"user1","password":"user1pass"}' | tee login.json
TOKEN=$(jq -r .token login.json)

# 3. authenticated request through our gateway (uses X-User-* headers from core)
curl -fsS -H "Authorization: Bearer $TOKEN" \
  http://localhost:9107/api/coaches

# 4. run pytest
docker exec team-7-backend pytest -q
```

Every command above must exit `0`.

## H. Last-24h sanity sweep

- [ ] All Jira tickets marked Done or explicitly moved to a follow-up.
- [ ] No uncommitted changes (`git status` is clean).
- [ ] No untracked secrets.
- [ ] All branches merged or deleted.
- [ ] Final zip uploaded and the upload confirmation link saved in chat.