# Jira Setup & Project Management Workflow

This document captures the **exact** Jira setup we agreed to follow for Phase 3
and how we'll use it during sprints. It is derived directly from P3_SE1.pdf
§بخش اول.

> One source of truth for issues. If a task isn't in Jira, it isn't real work.

---

## 1. Account & project setup

> **Decision (2026-07-15, confirmed by Sina S. with TAs):** We **create our own
> Atlassian Cloud Free site**, not the one at `rosenazeri83.atlassian.net`.
> The TAs told Sina S. directly that each team gets its own site.

### 1.1 Site ownership & email
- **Site owner / admin:** Sina Sadeghi (team lead). He is the only one who
  registered the domain — this avoids license / billing surprises.
- **Subdomain:** ✅ **`sinasadeghi83.atlassian.net`** (claimed 2026-07-15).
- **Billing / signup email:** **`sina.sadeghi83@gmail.com`** (Sina S.'s
  personal Gmail; tied to the Cloud Free billing).
- During signup, skip onboarding questions with `Skip`. We will **not** invite
  the TAs or scrum master to *this* site during creation — invites happen
  after the project is up (see §1.3).

### 1.2 Per-member accounts on the new site
Once the site exists at `sinasadeghi83.atlassian.net`, each of the three
members creates their **own free Atlassian account** on it:

| Member | Email to sign up with |
|--------|----------------------|
| Sina Sadeghi (admin) | `sina.sadeghi83@gmail.com` |
| Sina Negahban | `sina.seyyed.2004@gmail.com` |
| Amirali Rahimi | `amiralirahimi823@gmail.com` |

> Atlassian Cloud Free allows up to 10 users, which is more than enough for
> our 3-person team + scrum master.

### 1.3 Project
After admin signup:
1. From the project home, click **Create Project**.
2. **Type:** Scrum → **Use Template**.
3. **Management:** **Team-managed** (not Company-managed).
4. **Project name:** `PolyLife — Team 7`.
5. **Project key:** auto-generated, e.g. `PL7` or `TEAM7`. We use this key as
   a prefix on every issue id (e.g. `PL7-12`).

### 1.4 Members to invite
Sina Sadeghi (admin) opens the project → **Invite People** and adds:
1. Sina Negahban — `sina.seyyed.2004@gmail.com`
2. Amirali Rahimi — `amiralirahimi823@gmail.com`
3. **Scrum master** — email supplied by the TAs; invite the moment we
   receive it.

Each invitee receives a confirmation email → clicks the link → lands inside
the project. No shared logins.

### 1.4 Board columns
We add a **`Testing`** column to the default `To Do / In Progress / Done`
flow, so the workflow reads:
`To Do → In Progress → Testing → Done`

A card only moves to **Done** after (a) code merged and (b) tests are green.

## 2. Issue taxonomy

| Issue Type | When we use it |
|------------|----------------|
| **Story** | A user-visible capability (e.g. "User can book a coach"). |
| **Task** | A unit of technical work (e.g. "Add Alembic migration for `coach_rating`"). |
| **Bug** | Anything broken after it was working. |

Stories come from P1/P2; tasks are split out from stories. **Every Story is
the parent of 2–5 Tasks.** Bugs are filed as they appear.

### 2.1 Naming convention

```
PL7-12  [chat] implement POST /chat/threads
PL7-13  [reserve] add Alembic migration for coach_availability
PL7-14  [infra] wire team-up script
PL7-15  [bug] 500 on /chat/ws when thread_id missing
```

- Brackets indicate which microservice / area the issue belongs to.
- Subject starts with a verb in imperative form.

### 2.2 Mandatory fields
- **Assignee** — never empty. A task with no owner is invisible.
- **Sprint** — every issue sits in exactly one sprint.
- **Story Points** — Fibonacci (1, 2, 3, 5, 8, 13). Tasks > 8 must be split.
- **Labels** — `chat`, `reserve`, `infra`, `docs`, `bug`.

## 3. Sprints

We have **≈ 2 weeks** until 28 Tir 1405. We plan two sprints of ~1 week each:

| Sprint | Window | Goal |
|--------|--------|------|
| Sprint 1 | Days 1–7 | Infra up (Docker + Gateway + auth) + DB schema + at least one happy-path API per service |
| Sprint 2 | Days 8–14 | Remaining APIs + WebSocket chat + CI job + end-to-end smoke + buffer for fixes |

> The PDF explicitly warns against leaving work to the last few days. **Push
> daily** so we never fall behind silently.

## 4. Daily workflow

1. **Standup** (15 min, async in Jira comments OK if everyone is busy):
   - What I did yesterday (link the PR).
   - What I'll do today (move ticket to In Progress).
   - Any blocker? → raise in the channel.
2. Update Jira as you go: status changes, comments, time logged.
3. End of session: push your branch. PDF requires this.

## 5. Definition of Done

A ticket can move to **Done** only when **all** are true:

- [ ] Code merged to `development` (PR approved by at least one teammate).
- [ ] CI is green for our team job.
- [ ] Code reviewed (see `08_git_workflow.md`).
- [ ] Docs updated if API or schema changed.
- [ ] Demonstrable (a screenshot, curl, or test).

## 6. Scrum-master meeting

Per PDF §برگزاری جلسات با اسکرام مستر (P1 reference): each meeting produces a
written report with three sections. We'll save these under `meetings/` in the
forked repo:

```
meetings/
  2026-07-16-sprint1-kickoff.md
  2026-07-19-mid-sprint1.md
  2026-07-23-sprint2-planning.md
  ...
```

Template (in Persian, since the TA expects Persian notes):

```markdown
# جلسه Scrum — <تاریخ>

## ۱. پیشرفت تیم
- انجام‌شده:
- در حال انجام:
- برای انجام:

## ۲. مشکلات و موانع
- مانع ۱ → راه‌حل پیشنهادی
- مانع ۲ → راه‌حل پیشنهادی

## ۳. برنامه جلسه بعدی
- هدف ۱
- هدف ۲
```

## 7. Reporting back to Jira

- Each issue must carry the **actual time** the member spent.
- Each PR links to the Jira ticket via the commit message (e.g.
  `PL7-12 #comment [chat] implement POST /chat/threads`).
- Velocity per sprint is recomputed at the end so we know if we're on track.