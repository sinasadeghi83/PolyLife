# Git Workflow

> Source: PDF §۸.۴ (قوانین کار با Git و تحویل پروژه). The PDF is strict on this
> section — read it twice.

---

## 1. Repository layout

- **Upstream:** `github.com/PolyLife2026/PolyLife` (read-only for us)
- **Origin:** `github.com/sinasadeghi83/PolyLife` — Sina Sadeghi's personal
  fork, claimed 2026-07-15. Clone URL: `git@github.com:sinasadeghi83/PolyLife.git`
- **Local:** clones origin, never pushes to upstream

### 1.1 One-time setup

```bash
# 1. Sina S. has already forked via the GitHub UI: PolyLife2026/PolyLife → sinasadeghi83/PolyLife
git clone git@github.com:sinasadeghi83/PolyLife.git
cd PolyLife

# 2. Add upstream so we can pull the latest from the main repo
git remote add upstream git@github.com:PolyLife2026/PolyLife.git

# 3. Always pull from upstream before starting new work
git pull upstream main

# 4. Add teammates (Sina Negahban, Amirali Rahimi) as **collaborators** on the
#    fork via the GitHub repo settings page (Settings → Collaborators).
```

## 2. Branching model

**No PRs to `upstream`** (`PolyLife2026/PolyLife`). All PRs live inside our
fork (`origin` = `sinasadeghi83/PolyLife`).

Inside the fork, PRs may target any of these branches:

- `main`            ← stable, the "blessed" tip of the fork
- `development`     ← integration branch, cut from `main`
- `feature/*`       ← short-lived per-ticket branches

```
main              ← stable tip; PRs may land here inside the fork
└── development   ← integration branch
    ├── feature/team-7-chat-threads
    ├── feature/team-7-reserve-availability
    ├── feature/team-7-nginx-gateway
    └── bugfix/team-7-double-booking
```

### 2.1 Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/team-7-<scope>-<short>` | `feature/team-7-chat-threads` |
| Bug fix | `bugfix/team-7-<short>` | `bugfix/team-7-double-booking` |
| Docs | `docs/team-7-<topic>` | `docs/team-7-readme` |

> Scope examples: `chat`, `reserve`, `infra`, `docs`, `ci`.

### 2.2 Lifecycle
1. Branch from `development`.
2. Push often (end of every working session — see PDF §زمان‌بندی Push کردن).
3. Open PR to `development` once code is ready.
4. After approval + green CI, merge.
5. Delete the branch.

## 3. Commit message format

```
[team7] <verb>: <short description>

<optional body, wrapped at 72 cols, explaining why>

SCRUM-<ticket-id>
```

### 3.1 Examples

```bash
# Good
git commit -m "[team7] add model: coach_profile"
git commit -m "[team7] fix: no more 502 when restarting backend"
git commit -m "[team7] refactor: separate auth.py from logic"

# Bad (PDF explicitly lists these)
git commit -m "works"
git commit -m "yesterday changes"
git commit -m "everything done"
```

### 3.2 Rules
- One logical unit per commit.
- Verb in **English imperative** (add, fix, refactor, test, docs).
- Never push `--force` (`-f`). The PDF bans it; merge conflicts must be
  resolved manually.

## 4. Pull-request workflow

### 4.1 Opening a PR
- Title: `[team7] <scope>: <summary>` (mirrors commit format).
- Description template:

```markdown
## What
- One-paragraph summary.

## Why
- Link to Jira ticket: SCRUM-XX

## How to test
- Step-by-step manual reproduction
- `curl` / `pytest` snippet

## Checklist
- [ ] Tests added/updated
- [ ] Docs updated (if behaviour changed)
- [ ] Jira ticket updated
```

### 4.2 Review
- At least **one teammate** reviews and approves.
- Reviewer checks: tests, naming, security, consistency with `ai_docs/`.
- Use GitHub inline comments; resolve before merge.

### 4.3 Merge
- **Merge** into `development`, `main`, or another `feature/*`
  branch — whichever is the chosen PR target.
- **Never open a PR against `upstream`** (`PolyLife2026/PolyLife`).
  All PRs stay inside our fork (`origin` = `sinasadeghi83/PolyLife`).

## 5. Push schedule (PDF §زمان‌بندی Push کردن)

| When | Action |
|------|--------|
| End of every working session | Push |
| 24 h before deadline | Last push done |
| After fixing a bug | Push the same day |

> The PDF is explicit: "in the last days of the deadline don't put it off."
> Daily pushes also reduce merge-conflict pain when other teams push to
> upstream.

## 6. Conflict handling

When `git pull` shows a conflict:

```bash
git fetch upstream
git rebase upstream/development
# resolve conflicts file by file
git add <resolved-files>
git rebase --continue
git push origin feature/team-7-...
```

> Never `git push -f` (banned). Never rebase `main` or `development`.

## 7. Handling changes from other teams in Core

The PDF warns: if another team changes `core/` and we haven't pulled, we'll
hit conflicts when pushing.

- Daily: `git pull upstream development` at the start of every session.
- After pull: run `./all-up` and make sure smoke tests still pass.
- If `core/` API contract changed (e.g. response shape), update our code
  immediately and notify in the team channel.

## 8. Final-delivery packaging (PDF §موارد تحویلی این بخش)

```bash
# from repo root
git archive --format=zip \
  --output=../P3_7_<S1>_<S2>_<S3>.zip \
  development
```

> Double-check the file name format before uploading:
> `P3_7_Studentnumber1_Studentnumber2_Studentnumber3`.

## 9. Things that are explicitly forbidden

- ❌ Opening a PR against `upstream` (`PolyLife2026/PolyLife`).
- ❌ `git push -f`.
- ❌ Squashing multiple logical changes into one "everything done" commit.
- ❌ Editing the root `requirements.txt` or the root `settings.py`.
- ❌ Committing `.env` (real secrets).

> Note: direct pushes / merges to `main` are fine **inside the fork**.
> Only `upstream` is off-limits.