# API Endpoints — Chat with Coach + Reserve Coach

> All endpoints live behind the team-7 gateway at
> **`http://localhost:9107/api/...`** (port comes from `TEAM_PORT` in
> `teams/team7/.env.example`).
>
> The gateway's `auth_request` block (see `teams/team7/gateway.conf`)
> forwards every request to `http://core:8000/api/verify`. If Core returns
> 200, Nginx copies the response's `X-User-Id` and `X-User-Username` headers
> onto the upstream request to our backend. If Core returns 401, the user
> is redirected to `http://localhost:8000/login`.
>
> Our backend **never** decodes JWTs; it only reads `X-User-Id` and
> `X-User-Username` from the request.
>
> Response envelope:
> - 200/201: `{"data": {...}}`
> - 4xx: `{"error": {"code": "STRING_CODE", "message": "human readable"}}`
> - 5xx: `{"error": {"code": "INTERNAL", "message": "...", "trace_id": "..."}}`

---

## 1. Chat with Coach

### 1.1 REST endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/chat/threads` | user | List the current user's chat threads (sorted by `last_message_at` desc). |
| `POST` | `/chat/threads` | user | Open or fetch a thread with `{coach_user_id}`. |
| `GET` | `/chat/threads/{thread_id}/messages` | user or coach in thread | Paginate messages (cursor-based, 50/page). |
| `POST` | `/chat/threads/{thread_id}/messages` | user or coach in thread | Send a text message. |
| `POST` | `/chat/threads/{thread_id}/messages/{message_id}/read` | recipient | Mark a message as read. |
| `POST` | `/chat/threads/{thread_id}/attachments` | user or coach in thread | Upload a file (multipart). |
| `GET` | `/chat/coaches/online` | user | List coaches currently marked `is_online = true`. |
| `PATCH` | `/chat/coaches/me/status` | coach | Toggle `is_online`. Body: `{"is_online": true}`. |

### 1.2 WebSocket endpoint

| Endpoint | Description |
|----------|-------------|
| `WS /chat/ws?thread_id={id}` | Bidirectional real-time channel for a thread. Authenticated the same way as REST: the gateway's `auth_request` calls Core's `/api/verify` with the original `Authorization: Bearer ...` header (or `Cookie` if the client used one), then forwards the resulting `X-User-Id` / `X-User-Username` to our backend. Events pushed: `message.created`, `message.read`, `typing.start`, `typing.stop`, `presence.update`. |

#### WS message envelope
```json
// client → server
{ "op": "send", "body": "Hello coach" }
{ "op": "typing", "is_typing": true }

// server → client
{ "event": "message.created", "data": { "id": 42, "thread_id": 1, ... } }
{ "event": "presence.update", "data": { "coach_user_id": 101, "is_online": true } }
```

### 1.3 Permission rules
- A user can only read/write threads where they are `user_id` or `coach_user_id`.
- A coach can only toggle their own `is_online` (verified by `X-User-Id`).

---

## 2. Reserve Coach

### 2.1 Coach profile

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/reserve/coaches` | user | List coaches. Query: `?specialty=yoga&min_rating=4`. |
| `GET` | `/reserve/coaches/{coach_user_id}` | user | Coach profile + aggregated rating. |
| `POST` | `/reserve/coaches/me` | coach | Create/update own profile. Body matches `coach_profile` columns. |
| `POST` | `/reserve/coaches/{coach_user_id}/ratings` | user | Leave a 1–5 rating (one per coach). |
| `GET` | `/reserve/coaches/{coach_user_id}/ratings` | user | List ratings for a coach. |

### 2.2 Availability

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/reserve/coaches/{coach_user_id}/availability` | user | List slots (`status='open'`). Query: `?from=2026-08-01&to=2026-08-31`. |
| `POST` | `/reserve/coaches/me/availability` | coach | Create one or more slots. Body: `{"slots":[{"start_at":..., "end_at":...}, ...]}`. |
| `PATCH` | `/reserve/availability/{id}` | coach (owner) | Update a slot or mark it `blocked`. |
| `DELETE` | `/reserve/availability/{id}` | coach (owner) | Soft-delete (sets `is_deleted=true`). |

### 2.3 Appointments

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/reserve/appointments` | user | Book a slot. Body: `{"availability_id": 2, "notes": "first session"}`. Atomically marks slot `booked`. |
| `GET` | `/reserve/appointments` | user or coach | List own appointments. Query: `?status=confirmed&from=...`. |
| `GET` | `/reserve/appointments/{id}` | participant | Get details. |
| `PATCH` | `/reserve/appointments/{id}` | participant | Update status (`cancelled`, `completed`, `no_show`). |

### 2.4 Permission rules
- A user can only book slots whose coach is `status='open'`.
- A coach can only modify their own availability/appointments.

---

## 3. Cross-service endpoints

Because both services live in the **same** backend container (one FastAPI
app, two routers), there is no HTTP between them; they call each other as
Python functions. If we later split them into separate containers, the same
routes stay under `/api/chat/...` and `/api/reserve/...` and the gateway's
existing `location /api/` block proxies both to the upstream `backend`.

## 4. Common error codes

| Code | HTTP | When |
|------|------|------|
| `UNAUTHENTICATED` | 401 | Missing/invalid `X-User-*` headers (gateway didn't authenticate). |
| `FORBIDDEN` | 403 | Authenticated but not allowed (e.g. reading another user's thread). |
| `NOT_FOUND` | 404 | Entity does not exist or is soft-deleted. |
| `CONFLICT` | 409 | Booking an already-booked slot, duplicate rating, etc. |
| `VALIDATION` | 422 | Pydantic validation failed. |
| `RATE_LIMIT` | 429 | Per-user rate-limit exceeded. |
| `INTERNAL` | 500 | Anything we did not anticipate. |

## 5. Versioning

We use **URL prefix versioning** for any breaking changes:
`/api/v2/...` if/when needed. Within Phase 3 we stay on v1.

## 6. OpenAPI

- The FastAPI app auto-generates `/api/openapi.json` and Swagger UI at
  `/api/docs`.
- We commit a snapshot of `openapi.json` in the repo for review (no manual
  OpenAPI authoring).