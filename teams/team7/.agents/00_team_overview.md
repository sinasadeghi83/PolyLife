# Team Overview

> Source-of-truth document for everything in `ai_docs/`. If anything in the
> other files contradicts this document, this one wins.

---

## 1. Course

- **Course:** Software Engineering 1 (مهندسی نرم افزار ۱) — Dr. Zakeri, Spring 1405
- **University:** Amirkabir University of Technology (Tehran Polytechnic)
- **Project:** PolyLife — a diet & physical-fitness web platform built on a microservice architecture

## 2. Team

| Role | Name | Email |
|------|------|-------|
| Member | Sina Sadeghi (team lead) | `sina.sadeghi83@gmail.com` (confirmed 2026-07-15) |
| Member | Sina Negahban | `sina.seyyed.2004@gmail.com` (confirmed 2026-07-15) |
| Member | Amirali Rahimi | `amiralirahimi823@gmail.com` (confirmed 2026-07-15) |

| **Group ID:** **7** (confirmed by Sina on 2026-07-15)
>
> **Student numbers:** _TBD — fill in once confirmed.

## 3. Chosen Microservices

| # | Microservice | Persian name | Category |
|---|--------------|--------------|----------|
| 1 | **Chat with Coach** | چت با مربی | Group 2 (Messaging) |
| 2 | **Reserve Coach** | رزرو مربی | Group 2 (Booking) |

Both services sit in the **Coach** domain — they share an `Appointment` concept and both need to display a coach profile, so they are tightly coupled from a data-flow standpoint but live in separate Docker containers per the architecture rules.

## 4. Tooling accounts (confirmed 2026-07-15)

| Tool | Value | Notes |
|------|-------|-------|
| Group ID | **7** | Course-assigned |
| Atlassian Jira site | **`sinasadeghi83.atlassian.net`** | Sina S. is site owner/admin (TAs confirmed 2026-07-15 that each team runs its own site) |
| Git fork (origin) | **`git@github.com:sinasadeghi83/PolyLife.git`** | Sina S.'s personal fork; never push to upstream `github.com/PolyLife2026/PolyLife` |
| GitHub account for Sina S. | `sinasadeghi83` | Add teammates (Sina N., Amirali) as **collaborators** on the fork |
| Local clone path | `/home/grandmaster/Documents/SE1/PolyLife/` | Sina S.'s working copy (2026-07-19). Other teammates clone to their own machines. |

## 5. Phase Status

| Phase | Title | Status |
|-------|-------|--------|
| P1 | Requirements + SRS | Submitted |
| P2 | UML diagrams + wireframes | Submitted |
| **P3** | **Microservice architecture & integration** | **In progress (this phase)** |
| P4+ | TBA by course staff | — |

## 6. P3 Submission Rules (from P3_SE1.pdf)

- **Format:** `P3_7_StudNum1_StudNum2_StudNum3` (Group ID = 7)
- **Upload by:** 28 Tir 1405, 23:59 (≈ July 19, 2026)
- **Evaluation:** Oral — every member must master the whole deliverable
- **Help channel:** TA's Bale ID; `@poor3a` on Bale/Telegram for technical blockers

## 7. Working Agreements

- We work in Persian and English; deliverables and code are in **English**.
- All architecture-level decisions are recorded here before they are coded.
- Every code commit references a Jira ticket id (see `04_jira_setup.md`).