# Database Design — Chat with Coach + Reserve Coach

This document covers Section B of P3_SE1.pdf: ER diagram, table docs, and
sample data. The diagrams are described here in DBML so they can be rendered
to PNG/SVG with `dbml2sql` + `dbml-renderer` and edited as plain text.

> Once a final diagram is agreed, export it to PNG/PDF and commit it under
> `teams/team7/db/er-diagram.png`. Also keep the `.dbml` source under
> `teams/team7/db/schema.dbml`.

---

## 1. Naming & convention rules (from PDF §بخش دوم)

- snake_case, English, descriptive.
- Every table has:
  - `id BIGSERIAL PRIMARY KEY`
  - `created_at TIMESTAMP NOT NULL DEFAULT NOW()`
  - `updated_at TIMESTAMP DEFAULT NULL`
  - `is_deleted BOOLEAN NOT NULL DEFAULT FALSE`
- FK constraints where relationships exist.
- Indexes on columns used in `WHERE`/`ORDER BY` frequently.

## 2. High-level entities

Both microservices revolve around **users** (we only know them by id from the
`X-User-Id` header — we do **not** store a full user record; that belongs to
the Core service) and **coaches** (a coach is just a user flagged as coach).

| Entity | Service | Why it exists |
|--------|---------|---------------|
| `coach_profile` | Both | Extended info about a coach (bio, specialties, hourly rate). |
| `coach_availability` | Reserve Coach | Slots a coach offers for booking. |
| `appointment` | Reserve Coach | A confirmed booking of a coach by a user. |
| `chat_thread` | Chat with Coach | A 1-to-1 chat between a user and a coach. |
| `chat_message` | Chat with Coach | A single message in a thread (text + optional attachment). |
| `message_attachment` | Chat with Coach | File/image attached to a message. |
| `coach_rating` | Both | A user rating (1–5) + comment on a coach. |

> Coaches are NOT duplicated. `coach_profile.user_id` matches a `X-User-Id`.

## 3. ER diagram (DBML source — paste into `schema.dbml`)

```dbml
// =====================================================
//  PolyLife team — Chat with Coach + Reserve Coach DB
//  Engine: PostgreSQL 16
// =====================================================

Table coach_profile {
  id bigserial [pk]
  user_id bigint [unique, not null, note: 'matches X-User-Id from Core']
  bio text
  specialties jsonb [note: 'array of strings, e.g. ["yoga","strength"]']
  hourly_rate numeric(10,2) [not null]
  years_experience smallint
  is_online boolean [not null, default: false, note: 'used by chat service']
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    user_id [unique]
    is_online [note: 'used to find online coaches for chat']
  }
}

Table coach_availability {
  id bigserial [pk]
  coach_user_id bigint [not null, ref: > coach_profile.user_id]
  start_at timestamp [not null]
  end_at timestamp [not null]
  status varchar(16) [not null, default: `'open'`, note: 'open | booked | blocked']
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    (coach_user_id, start_at)
    status
  }
}

Table appointment {
  id bigserial [pk]
  coach_user_id bigint [not null, ref: > coach_profile.user_id]
  user_id bigint [not null, note: 'from X-User-Id']
  availability_id bigint [unique, not null, ref: - coach_availability.id]
  status varchar(16) [not null, default: `'confirmed'`, note: 'pending | confirmed | cancelled | completed | no_show']
  notes text
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    user_id
    coach_user_id
    status
  }
}

Table chat_thread {
  id bigserial [pk]
  user_id bigint [not null, note: 'X-User-Id of the regular user']
  coach_user_id bigint [not null, ref: > coach_profile.user_id]
  last_message_at timestamp
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    (user_id, coach_user_id) [unique]
    coach_user_id
    last_message_at
  }
}

Table chat_message {
  id bigserial [pk]
  thread_id bigint [not null, ref: > chat_thread.id]
  sender_user_id bigint [not null, note: 'either party in the thread']
  body text [not null]
  sent_at timestamp [not null, default: `NOW()`]
  read_at timestamp
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    thread_id
    (thread_id, sent_at)
    sender_user_id
  }
}

Table message_attachment {
  id bigserial [pk]
  message_id bigint [not null, ref: > chat_message.id]
  file_url text [not null, note: 'stored in object storage or local volume']
  mime_type varchar(64) [not null]
  size_bytes integer [not null]
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    message_id
  }
}

Table coach_rating {
  id bigserial [pk]
  coach_user_id bigint [not null, ref: > coach_profile.user_id]
  user_id bigint [not null, note: 'X-User-Id of the rater']
  rating smallint [not null, note: '1..5']
  comment text
  created_at timestamp [not null, default: `NOW()`]
  updated_at timestamp
  is_deleted boolean [not null, default: false]

  Indexes {
    (coach_user_id, user_id) [unique, note: 'one rating per (coach, user)']
    coach_user_id
  }
}
```

## 4. Table-by-table description (matches PDF template)

### 4.1 `coach_profile`
- **Purpose:** Store coach-specific data not present in Core's user table.
- **Notes:** `user_id` is the foreign key to Core (we don't enforce it as a FK
  because Core lives in another database).

### 4.2 `coach_availability`
- **Purpose:** Time slots a coach offers for booking.
- **Constraints:** `end_at > start_at` (enforced in app layer + DB CHECK).
- **Sample rows:**
  | id | coach_user_id | start_at | end_at | status |
  |----|---------------|----------|--------|--------|
  | 1 | 101 | 2026-08-01 09:00 | 2026-08-01 10:00 | open |
  | 2 | 101 | 2026-08-01 10:00 | 2026-08-01 11:00 | booked |

### 4.3 `appointment`
- **Purpose:** A confirmed booking tying a user to a slot.
- **Constraints:** `availability_id` is unique → each slot can be booked at most once.
- **Sample rows:**
  | id | coach_user_id | user_id | availability_id | status |
  |----|---------------|---------|-----------------|--------|
  | 1 | 101 | 42 | 2 | confirmed |

### 4.4 `chat_thread`
- **Purpose:** Conversation between a user and a coach. Unique per pair.
- **Sample rows:**
  | id | user_id | coach_user_id | last_message_at |
  |----|---------|---------------|-----------------|
  | 1 | 42 | 101 | 2026-08-01 09:15 |

### 4.5 `chat_message`
- **Purpose:** One message in a thread.
- **Sample rows:**
  | id | thread_id | sender_user_id | body | sent_at |
  |----|-----------|----------------|------|---------|
  | 1 | 1 | 42 | "Hi coach!" | 2026-08-01 09:10 |
  | 2 | 1 | 101 | "Hello! How can I help?" | 2026-08-01 09:12 |

### 4.6 `message_attachment`
- **Purpose:** Optional binary file attached to a message (image, PDF plan).
- **Sample rows:**
  | id | message_id | file_url | mime_type | size_bytes |
  |----|------------|----------|-----------|------------|
  | 1 | 2 | `s3://bucket/plan.pdf` | application/pdf | 245760 |

### 4.7 `coach_rating`
- **Purpose:** 1–5 rating + comment left by a user on a coach.
- **Constraints:** unique `(coach_user_id, user_id)`, `rating BETWEEN 1 AND 5`.
- **Sample rows:**
  | id | coach_user_id | user_id | rating | comment |
  |----|---------------|---------|--------|---------|
  | 1 | 101 | 42 | 5 | "Great session!" |

## 5. Relationships summary

| From | Cardinality | To | Notes |
|------|-------------|-----|-------|
| `coach_profile` (1) | — (N) | `coach_availability` | A coach has many slots |
| `coach_availability` (1) | — (1) | `appointment` | A slot is either open or booked |
| `chat_thread` (1) | — (N) | `chat_message` | A thread has many messages |
| `chat_message` (1) | — (N) | `message_attachment` | Optional attachments |
| `coach_profile` (1) | — (N) | `coach_rating` | A coach has many ratings |
| `user` (Core) | — (N) | `appointment`, `chat_thread`, `chat_message`, `coach_rating` | All reference users by id |

## 6. Extensibility notes

- New fields (e.g. `coach_profile.languages TEXT[]`) can be added without
  restructuring.
- New message types (e.g. voice notes) → add a `kind VARCHAR` column to
  `chat_message`.
- New booking states → extend the `appointment.status` enum via a CHECK
  constraint update; existing rows stay valid.

## 7. Migration plan

- Use **Alembic** (SQLAlchemy migration tool).
- One migration per logical change.
- `alembic upgrade head` runs automatically on container start in dev.
- In CI, we spin up a Postgres container, run migrations, then run pytest.

## 8. Final-deliverable checklist

- [ ] `teams/team7/db/schema.dbml` committed.
- [ ] `teams/team7/db/er-diagram.png` (exported, ≥ 1080p).
- [ ] `teams/team7/db/er-diagram.pdf` (one-page export).
- [ ] `teams/team7/db/description.md` (this document, exported).
- [ ] `teams/team7/db/init.sql` with at least **2 sample rows per table**.