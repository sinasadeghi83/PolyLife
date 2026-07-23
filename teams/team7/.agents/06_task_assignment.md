# Team 7 Task Assignment and Jira Snapshot

This document gives humans and automation agents one compact view of Team 7
ownership, sprint scope, and the last verified Jira state.

> Jira project: [`SE1 Team 7` (`SCRUM`)](https://sinasadeghi83.atlassian.net/jira/software/projects/SCRUM/boards/1)
>
> Live Jira is authoritative for issue summary, assignee, story points, and
> workflow status. This file is the repository snapshot used when Jira is not
> accessible. Architecture and API details remain authoritative in
> `02_architecture_decisions.md`, `03_database_design.md`, and
> `04_api_endpoints.md`.

## 1. Synchronization contract

<!-- jira-sync
project: SCRUM
site: https://sinasadeghi83.atlassian.net
jql: project = SCRUM ORDER BY key ASC
verified_at: 2026-07-23
verified_issue_count: 17
status_field: Jira status
sprint_source: labels (sprint-sprint1 or sprint-sprint2)
-->

Last live verification: **2026-07-23**, through Jira REST API v3. The query
returned **17 issues**. Jira's Sprint field is empty on these issues; sprint
membership is encoded by the `sprint-sprint1` and `sprint-sprint2` labels.

Rules for humans and agents:

1. Before starting work, re-read the live Jira issue when credentials and Jira
   are available. Do not infer current status from an unchecked box elsewhere.
2. If Jira and this file disagree, Jira wins for ticket metadata. Report the
   mismatch and update this snapshot in the same documentation change.
3. Do not change Jira merely to match this file without team approval. A change
   in owner, estimate, sprint, or scope is a planning decision.
4. Update `verified_at`, `verified_issue_count`, the affected ticket row, and
   the totals whenever this snapshot is refreshed.
5. Preserve exact issue keys. `SCRUM-3` does not exist; the helper-scripts task
   was dropped because the repository already supplies those scripts.
6. Workflow meanings and evidence requirements are defined in
   `09_progress_tracking.md`: `To Do → In Progress → Testing → Done`.
7. A Jira `Done` value records Jira's current state; it is not by itself proof
   of review, merge, CI, or integration. Verify delivery evidence separately.

## 2. Team and ownership

| ID | Member | Primary responsibility | Jira display name |
|---|---|---|---|
| `SS` | Sina Sadeghi | Backend lead; chat; shared backend foundations | `sina sadeghi` |
| `SN` | Sina Negahban | Reserve backend; database support; CI | `Seyyed Sina Negahban` |
| `AR` | Amirali Rahimi | Infrastructure; gateway; frontend; final docs | `amirali rahimi` |

The scrum master supervises the process and is not an implementation owner.
The ticket assignee owns implementation and status reporting; the workstream
lead owns interface decisions and review coordination.

### Workstream boundaries

| Workstream | Lead | Scope / interface |
|---|---|---|
| Chat with Coach | `SS` | Threads, messages, attachments, WebSocket presence/typing, Redis fan-out; `/api/chat/...` |
| Reserve Coach | `SN` | Coach availability, appointments, atomic booking, ratings; `/api/reserve/...` |
| Infra and frontend | `AR` | Team-local Docker/Compose, Nginx gateway, `.env.example`, HTML/JS frontend, run docs |
| Shared backend foundations | `SS` with `SN` support | FastAPI app, SQLAlchemy/Alembic, auth-header dependency, common tests |

Cross-cutting rules:

- At least one teammate reviews every PR before merge.
- The feature author writes applicable tests and updates affected docs.
- Every working session ends with a push; never use `git push -f`.
- Public behavior changes must update the matching `.agents/` document.
- If two people need the same file, the workstream lead coordinates the merge;
  the other contributor uses a focused PR and requests that lead's review.
- Escalate a blocker lasting more than 24 hours in the team channel.

## 3. Jira snapshot

Status symbols are visual aids only: `✅ Done`, `🔄 In Progress`, `🧪 Testing`,
`⬜ To Do`. The text in the Status column is the machine-readable value.

### Sprint 1 — infrastructure and first happy paths

Sprint goal: working infrastructure, database/auth foundations, and at least
one happy-path endpoint for each service.

| Key | Jira summary | Owner | Points | Status |
|---|---|---:|---:|---|
| `SCRUM-1` | Verify fork, add upstream remote, invite teammates as collaborators | `AR` | 1 | Done ✅ |
| `SCRUM-2` | Create Jira board with Testing column | `AR` | 1 | Done ✅ |
| `SCRUM-4` | Backend skeleton (FastAPI) + Dockerfile + compose | `SS` | 3 | Done ✅ |
| `SCRUM-5` | Postgres + Redis services in compose + update `.env.example` | `SS` | 2 | Done ✅ |
| `SCRUM-6` | DB schema (all tables) + Alembic migrations | `SS` | 5 | Done ✅ |
| `SCRUM-7` | `X-User-Id` dependency + smoke test | `SS` | 2 | Done ✅ |
| `SCRUM-8` | Chat: list/create threads | `SS` | 3 | To Do ⬜ |
| `SCRUM-9` | Reserve: list/create availability | `SN` | 3 | To Do ⬜ |
| `SCRUM-10` | Nginx gateway: extend with WebSocket route for `/api/chat/ws` | `AR` | 3 | To Do ⬜ |

Sprint 1 totals: **23 points** — **14 Done**, **9 To Do**, **0 In Progress**,
**0 Testing**. Completion by points: **60.9%**.

### Sprint 2 — complete features, CI, frontend, and final verification

| Key | Jira summary | Owner | Points | Status |
|---|---|---:|---:|---|
| `SCRUM-11` | Chat WebSocket + Redis pub/sub | `SS` | 8 | To Do ⬜ |
| `SCRUM-12` | Reserve atomic booking + double-book test | `SN` | 5 | To Do ⬜ |
| `SCRUM-13` | Ratings endpoint | `SN` | 3 | To Do ⬜ |
| `SCRUM-14` | Coach online status endpoint | `AR` | 2 | To Do ⬜ |
| `SCRUM-15` | Attachments upload | `AR` | 3 | To Do ⬜ |
| `SCRUM-16` | Frontend (HTML/JS) covering both flows | `AR` | 5 | To Do ⬜ |
| `SCRUM-17` | CI job for our team | `SN` | 2 | To Do ⬜ |
| `SCRUM-18` | README + final smoke tests | `AR` | 3 | To Do ⬜ |

Sprint 2 totals: **31 points** — **0 Done**, **31 To Do**, **0 In Progress**,
**0 Testing**.

### Project totals and allocation

| Owner | Sprint 1 | Sprint 2 | Total | Done | Remaining |
|---|---:|---:|---:|---:|---:|
| `SS` | 15 | 8 | 23 | 12 | 11 |
| `SN` | 3 | 10 | 13 | 0 | 13 |
| `AR` | 5 | 13 | 18 | 2 | 16 |
| **Team** | **23** | **31** | **54** | **14** | **40** |

Current project state: **6 of 17 tickets Done**; **14 of 54 points Done
(25.9%)**. All 11 remaining tickets are `To Do` in the verified snapshot.

## 4. Dependencies and recommended execution order

This is coordination guidance, not a replacement for each Jira issue's
acceptance criteria.

1. Foundations `SCRUM-4` through `SCRUM-7` precede feature routers. They are
   currently marked Done in Jira.
2. `SCRUM-8` establishes chat thread REST behavior before the WebSocket work in
   `SCRUM-11`.
3. `SCRUM-9` establishes availability behavior before atomic booking in
   `SCRUM-12`; ratings in `SCRUM-13` depend on completed appointment semantics.
4. `SCRUM-10` supplies the gateway WebSocket route needed to demonstrate
   `SCRUM-11` through the authenticated integration path.
5. `SCRUM-14` and `SCRUM-15` provide online-state and attachment capabilities
   consumed by the final frontend in `SCRUM-16`.
6. `SCRUM-17` must exercise the Team 7 test suite before final acceptance.
7. `SCRUM-18` is the final documentation and integrated smoke-test gate; it
   should close only after applicable feature tickets and CI are complete.

Safe parallel starting set from this snapshot: `SCRUM-8` (`SS`), `SCRUM-9`
(`SN`), and `SCRUM-10` (`AR`).

## 5. Agent handoff protocol

When an AI or human starts a ticket, record or report:

```text
Ticket: SCRUM-N
Owner: SS | SN | AR
Jira status: To Do | In Progress | Testing | Done
Branch: feature/team-7-<scope>-<short>
Scope: <one-sentence implementation boundary>
Dependencies: <ticket keys or none>
Evidence: <commit / PR / checks / integration result, or none yet>
Blocker: <blocker + owner, or none>
Next action: <one concrete action>
```

Required behavior:

- Confirm the Jira assignee, points, status, and acceptance criteria before
  implementation when Jira is reachable.
- Move a ticket to `In Progress` only when implementation actually starts.
- Use `Testing` when a pushed PR and a concrete test plan are ready for review.
- Use `Done` only after the evidence requirements in `09_progress_tracking.md`
  are satisfied; include PR and verification evidence in Jira.
- If Jira credentials are unavailable, do not mutate Jira. Use this verified
  snapshot, state that live status could not be checked, and list the exact
  manual Jira update required.
- Never treat private agent memory, a local branch, or a checkbox as delivery
  evidence.

## 6. Refresh checklist

To synchronize this file again:

- [ ] Authenticate with Jira without printing or persisting the API token.
- [ ] Query `project = SCRUM ORDER BY key ASC` for summary, status, assignee,
      labels, story points, and updated timestamp.
- [ ] Confirm the returned issue count and report missing or unexpected keys.
- [ ] Map assignees to `SS`, `SN`, or `AR`; do not guess unknown identities.
- [ ] Derive sprint from `sprint-sprint1` / `sprint-sprint2` labels until Jira's
      Sprint field is populated.
- [ ] Update changed rows, synchronization metadata, point totals, ticket totals,
      and the safe parallel starting set.
- [ ] Recalculate totals independently and inspect the Git diff.
- [ ] If metadata changed intentionally in Jira, update related planning docs
      when they contain the same ownership or workflow claim.
