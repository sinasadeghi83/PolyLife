# Agent Progress Tracking Guide

> **Purpose:** keep project status truthful, reproducible, and easy for a teammate or
> scrum master to verify.
>
> **Core rule:** an agent must report evidence, not assumptions. A local file,
> a passing unit test, or a Jira checkbox alone does not prove that a feature is
> delivered.

---

## 1. The progress evidence chain

Track every piece of work through this chain:

```text
Jira ticket
  ↓
Working branch
  ↓
Focused commit(s)
  ↓
GitHub pull request
  ↓
Review + automated checks
  ↓
Merged code
  ↓
Integration / smoke test
  ↓
Jira ticket marked Done
```

Use the systems for their intended purpose:

| Evidence | System | What it proves |
|---|---|---|
| Scope, owner, sprint, priority | Jira (`SCRUM`) | The work is planned and assigned. |
| Current implementation | Git branch and commits | Someone has made reproducible changes. |
| Review and delivery | GitHub PR in the fork | The change was reviewed and merged, or is awaiting review. |
| Code quality | pytest, Ruff, Docker, CI | The stated automated checks passed. |
| System behavior | Gateway and end-to-end smoke tests | The feature works in the integrated PolyLife environment. |
| Team progress and blockers | Scrum meeting report | The team discussed status and next actions. |
| Submission readiness | `08_implementation_checklist.md` | Course requirements are complete. |

If two sources disagree, report the disagreement explicitly and do not silently
mark the work as complete.

---

## 2. Required status meanings

Use the Jira workflow consistently:

```text
To Do → In Progress → Testing → Done
```

### `To Do`

The ticket is accepted or planned, but implementation has not started.
There should be no claim that the feature is available.

### `In Progress`

An owner is actively working on the ticket. At minimum, record:

- The ticket key, for example `SCRUM-8`.
- The working branch.
- The current implementation scope.
- Any blocker and its owner.

A ticket must not stay `In Progress` indefinitely without a recent update.

### `Testing`

The implementation is complete enough for review and verification. At minimum,
there must be:

- A pushed branch and GitHub PR.
- A test plan in the PR or Jira comment.
- Automated checks run locally or by CI.
- Any known failures clearly recorded.

`Testing` does not mean that all tests passed; it means that verification is
actively taking place. A failed check must remain visible.

### `Done`

Use `Done` only when all applicable conditions are true:

- The implementation is merged into the selected fork branch.
- At least one teammate has reviewed and approved the PR.
- Required automated checks are green.
- Required documentation is updated.
- The feature has been demonstrated locally or through the integration smoke test.
- Jira contains links or concise evidence for the PR and verification.

If any condition is missing, keep the ticket in `Testing` or `In Progress` and
state what remains.

---

## 3. Start-of-task procedure

Before changing code, an agent must:

1. Read the relevant planning documents:
   - `00_team_overview.md`
   - `02_architecture_decisions.md`
   - `03_database_design.md` when the schema is affected
   - `04_api_endpoints.md` when an API is affected
   - `06_task_assignment.md` for ownership and sprint scope
   - `07_git_workflow.md` for branch and PR rules
2. Identify the Jira ticket. Use an existing `SCRUM-N` ticket whenever possible.
3. Confirm the ticket's assignee, sprint, acceptance criteria, and dependencies.
4. If no ticket matches the requested work, stop before implementation and ask
   the user or team lead whether a new ticket should be created.
5. Check the repository state:

   ```bash
   git status --short --branch
   git log --oneline --decorate -10
   git remote -v
   ```

6. Confirm the intended base branch before creating a branch. Feature work should
   use the team's agreed integration branch; documentation says `development` is
   the normal integration target, while PRs inside the fork may also target
   `main` when explicitly chosen. Never open a PR to `upstream`.
7. Create or switch to a ticket-specific branch, for example:

   ```bash
   git checkout -b feature/team-7-chat-threads
   ```

8. Move the Jira ticket to `In Progress` only when implementation has actually
   begun.

Do not create a second ticket, branch, or competing implementation merely because
one source is temporarily unavailable. Record the uncertainty and ask for
clarification.

---

## 4. Jira access and credentials

Jira is the source of truth for planned work, but agents must follow the Jira
credential boundary in `AGENTS.md` and `05_jira_setup.md`.

Before any Jira API call:

```bash
[ -n "$ATLASSIAN_API_KEY" ] || {
  echo "FATAL: ATLASSIAN_API_KEY not set"
  exit 1
}
```

Then run the documented identity probe from `AGENTS.md` §7.1. Never print the
key, put it in a repository file, or paste it into a report.

If `ATLASSIAN_API_KEY` is absent:

- Do not attempt to create, edit, transition, or comment on Jira issues through
  the API.
- Treat the existing Jira tickets as the source of truth.
- Continue with local code work only when the user has already authorized it and
  the ticket scope is unambiguous.
- Tell the user exactly which Jira update must be made manually.

A Jira API success response is not sufficient evidence for a status change when
verification is possible. Re-read the issue and confirm its status, assignee,
summary, and relevant links after a mutation.

---

## 5. During implementation

Keep the work traceable and small:

- Keep one logical ticket per branch unless the team explicitly approves a
  dependency branch.
- Make focused commits using the required format:

  ```text
  <gitmoji> [team7] <verb>: <description>

  SCRUM-<number>
  ```

- Include tests and documentation in the same change when behavior, schema, or
  configuration changes.
- Push at the end of every working session and after fixing a bug.
- Do not commit `.env`, tokens, passwords, generated secrets, or unrelated files.
- Do not use `git push -f`.
- Keep Jira current: add a short comment for meaningful progress, decisions, or
  blockers rather than relying on private agent context.

At each session end, run:

```bash
git status --short --branch
git diff --stat
git log --oneline --decorate -5
git push origin HEAD
```

If the push fails, report the failure and the unpushed commit explicitly. Never
claim that work is shared until the remote branch or PR has been verified.

---

## 6. Verification levels

Use precise language in reports. These levels are not interchangeable:

| Level | Meaning | Example wording |
|---|---|---|
| Local | Files exist only in the current checkout. | "Implemented locally; not pushed." |
| Committed | A Git commit contains the change. | "Committed as `<sha>`; no PR yet." |
| Pushed | The commit is available on `origin`. | "Branch pushed; remote ref verified." |
| In review | A GitHub PR exists and is awaiting review/checks. | "PR #N open; CI pending." |
| Merged | The PR was merged into the selected fork branch. | "PR #N merged into `development`." |
| Tested | Named checks completed with recorded output. | "`uv run pytest -q`: 12 passed." |
| Integrated | The feature passed through the actual gateway/core path. | "Authenticated gateway smoke test passed." |
| Done | All applicable acceptance evidence is complete and Jira agrees. | "SCRUM-N is ready for Done." |

Never say "done" when the actual state is only local, committed, pushed, or
unit-tested.

---

## 7. Required test evidence

Run only the checks applicable to the ticket, but name every check that was run
and every check that was skipped.

### Team 7 backend checks

From `teams/team7/backend/`:

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
```

When Docker behavior is affected:

```bash
docker build -t team-7-backend .
docker run --rm team-7-backend pytest -q
```

When gateway, authentication, database, Redis, or endpoint integration is
affected, run the relevant commands in `08_implementation_checklist.md` §G and
record the result. A unit test that bypasses Nginx and Core does not prove that
forward authentication or routing works.

### Reporting failures

A failed check is useful progress when reported accurately. Include:

- Exact command.
- Exit status.
- Short failure summary.
- File or ticket responsible, if known.
- Next action and owner.

For example:

```text
Verification: FAIL
Command: uv run ruff check .
Result: exit 1; import-ordering error in alembic/env.py.
Next action: fix imports, rerun Ruff, then update PR and Jira SCRUM-4.
```

Do not hide failures by marking a check as skipped, saying "tests seem fine," or
reporting only a passing subset.

---

## 8. Pull request and merge evidence

Before opening a PR, confirm:

- The title includes the Team 7 scope.
- The description links the Jira ticket.
- The changed files are within the ticket scope.
- Tests and manual verification steps are listed.
- Documentation is updated when public behavior or architecture changes.
- The PR targets a branch inside `origin`, never `upstream`.

After opening a PR, verify its state through GitHub rather than assuming that a
push created it:

```bash
gh pr view <number> --repo sinasadeghi83/PolyLife
gh pr checks <number> --repo sinasadeghi83/PolyLife
```

If `gh` is unavailable, use the GitHub web interface or the repository's
configured API workflow. Record the PR URL or number in Jira.

Before saying a PR is deliverable, confirm:

- At least one teammate approved it.
- Required checks are green, not merely completed.
- Review comments are resolved or explicitly accepted.
- The PR was merged into the intended fork branch.

---

## 9. Scrum meeting and weekly reporting

Store meeting reports under:

```text
teams/team7/meetings/
```

Each report must state:

- Completed work with ticket keys and evidence.
- Work currently in progress with owner and branch/PR.
- Planned next work.
- Blockers, age of blocker, and next action.
- Any mismatch between Jira, GitHub, and the local checkout.

At least once per week, compare the Jira board with GitHub and the repository:

1. List all non-Done Jira tickets.
2. Find the branch or PR for each active ticket.
3. Check the latest CI result and local verification evidence.
4. Identify tickets with no recent update or no owner.
5. Move or annotate tickets that no longer match reality.
6. Recalculate sprint progress from verified tickets, not from commit count.

Useful Jira filters:

```jql
project = SCRUM AND statusCategory != Done ORDER BY updated ASC
project = SCRUM AND assignee is EMPTY
project = SCRUM AND statusCategory != Done AND updated <= -2d
project = SCRUM AND status changed to Done DURING (-7d, now)
```

A commit count is not a progress metric: generated files, refactors, and partial
implementations can produce many commits without completing a ticket.

---

## 10. Agent progress report template

Every coding task should end with a report in this format:

```markdown
## Progress report — SCRUM-<N>

### Scope
- Ticket:
- Owner:
- Branch:
- Base / target branch:

### Implementation
- Completed:
- Not completed:
- Files or public behavior changed:

### Evidence
- Commit(s):
- Remote branch:
- PR:
- Review:
- CI:

### Verification
- `uv run pytest -q`: PASS/FAIL/SKIPPED — <result>
- `uv run ruff check .`: PASS/FAIL/SKIPPED — <result>
- Docker build/test: PASS/FAIL/SKIPPED — <result>
- Gateway/integration smoke: PASS/FAIL/SKIPPED — <result>

### Blockers and risks
- Blocker:
- Owner:
- Next action:

### Jira action
- Current Jira status:
- Evidence/comment added:
- Manual Jira update required: yes/no

### Next step
- One concrete next action:
```

Use `SKIPPED` only with a reason. Use `FAIL` when the command ran and failed.
Do not replace either with vague language such as "not checked."

---

## 11. Sprint completion gate

Before declaring a sprint complete:

- [ ] Every sprint ticket has an owner and current Jira status.
- [ ] Every active ticket has a branch or an explicit blocker.
- [ ] Every completed ticket has a merged PR or an approved documented exception.
- [ ] Required tests, lint, Docker, and integration checks have evidence.
- [ ] API, schema, architecture, and README documents match the implementation.
- [ ] Scrum meeting notes are committed under `meetings/`.
- [ ] No untracked implementation files or secrets remain.
- [ ] `git status` is clean on the integration branch.
- [ ] The team has run the applicable sections of `08_implementation_checklist.md`.
- [ ] Jira reflects reality: no ticket is marked Done without its evidence.

The final submission must also pass the last-24-hour sanity sweep in
`08_implementation_checklist.md` §H.
