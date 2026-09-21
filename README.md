# ResumeReviewerDV

An AI-powered resume screening tool. Admins define job profiles with weighted requirements. Users upload resumes and receive an alignment score with per-requirement verdicts, evidence quotes, and confidence ratings — all backed by Claude AI and deterministic scoring logic.

## Status

Backend is complete and production-hardened. Frontend is next.

---

## Features

### User
- Sign up / log in with JWT auth (access + refresh tokens)
- Browse active job profiles
- Upload a resume (PDF or DOCX, up to 10 MB)
- Receive an async scoring report: overall score, per-requirement verdict, evidence, rationale, confidence
- View submission history

### Admin
- Role-based access (admin routes enforced server-side)
- Create and edit job profiles with must-have and weighted requirements
- View all submissions ranked by score
- Adjust requirement weights and re-score

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (async Python) |
| Database | PostgreSQL + SQLAlchemy (async) + Alembic |
| Auth | JWT (access + refresh tokens), bcrypt, token revocation |
| Job Queue | ARQ (Redis-backed async worker) |
| AI | Anthropic Claude via structured output |
| Parsing | pdfplumber (PDF), python-docx (DOCX) |
| Config | Pydantic Settings |
| Deployment | Docker + docker-compose |

---

## How Scoring Works

Scoring is split into AI judgment and deterministic aggregation:

1. **Parse** the resume into plain text.
2. **Judge each requirement independently.** Claude returns a verdict (`met` / `partial` / `not_met`), a short evidence quote, and a rationale. Resume text is labelled as DATA to mitigate prompt injection.
3. **Derive confidence from code signals** — not from the model's self-report:
   - Agreement across 2 independent LLM runs
   - Whether the evidence quote is verifiable in the resume text (catches hallucinations)
4. **Aggregate deterministically.** Weighted sum of verdicts; must-have failures cap the score at 50.
5. **Async via job queue.** Scoring is offloaded to an ARQ worker so the API returns immediately with `status: pending`. The client polls `GET /submissions/{id}` until `status: completed`.

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL (or use Docker)
- Redis (or use Docker)

### 1. Clone and install dependencies

```bash
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.example .env
```

Edit `.env` and fill in:
- `DATABASE_URL` — your PostgreSQL connection string
- `JWT_SECRET_KEY` — generate with: `python -c "import secrets; print(secrets.token_hex(32))"`
- `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com)
- `REDIS_URL` — `redis://localhost:6379` if running Redis locally

### 3. Run database migrations

First time (tables already exist from `create_all`):
```bash
alembic stamp head
```

After schema changes:
```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

### 4. Start the API

```bash
uvicorn backend.main:app --reload
```

### 5. Start the worker (separate terminal)

```bash
python -m arq backend.worker.WorkerSettings
```

API docs available at `http://localhost:8000/docs`

---

## Docker Setup

### 1. Add Docker-specific vars to your `.env`

```env
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=resumereviewerdv
```

### 2. Build and start all services

```bash
docker-compose up --build
```

This starts four containers:
| Container | Role |
|---|---|
| `app` | FastAPI API on port 8000 |
| `worker` | ARQ job queue worker (AI scoring) |
| `db` | PostgreSQL 16 |
| `redis` | Redis 7 (job queue broker) |

### 3. Run migrations inside Docker

```bash
docker-compose exec app alembic upgrade head
```

### Useful commands

```bash
# View logs
docker-compose logs -f app
docker-compose logs -f worker

# Stop everything
docker-compose down

# Stop and wipe all data volumes
docker-compose down -v
```

---

## API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register (5/min rate limit) |
| POST | `/auth/login` | Login (10/min, lockout after 10 failures) |
| POST | `/auth/logout` | Revoke current access token |
| POST | `/auth/refresh` | Issue new token pair from refresh token |
| GET | `/auth/me` | Current user info |

### Profiles (admin-managed)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/profiles` | Create job profile (admin) |
| GET | `/profiles` | List profiles (users see active only) |
| GET | `/profiles/{id}` | Get profile with requirements |
| PUT | `/profiles/{id}` | Update profile (admin) |
| PATCH | `/profiles/{id}/requirements/{req_id}` | Patch requirement weight (admin) |

### Submissions
| Method | Endpoint | Description |
|---|---|---|
| POST | `/submissions` | Upload resume — returns immediately with `status: pending` |
| GET | `/submissions/me` | User's submission history |
| GET | `/submissions/{id}` | Poll for status / get full results |
| GET | `/submissions` | All submissions ranked by score (admin) |
| POST | `/submissions/{id}/rescore` | Re-aggregate score with updated weights (admin) |

### System
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | DB connectivity check |

---

## Security Highlights

- Passwords: bcrypt with strength requirements (8+ chars, upper, lower, digit, special)
- Tokens: JWT with `jti`, typed (`access`/`refresh`), token revocation on logout
- Account lockout: 10 failed logins → 15-minute lockout
- Rate limiting: per-endpoint via slowapi
- File validation: extension + magic byte check, 10 MB cap, 50k char text limit
- Security headers: `X-Frame-Options`, `X-Content-Type-Options`, `CSP`, HSTS (production)
- CORS: configurable origin allowlist
- Prompt injection mitigation: resume text labelled as DATA in all LLM prompts
- Global exception handler: stack traces never reach the client

---

## Submission Flow (async)

```
POST /submissions
  │
  ├─ validate file (ext, magic bytes, size)
  ├─ parse resume text
  ├─ validate job profile exists
  ├─ create Submission (status=pending)
  ├─ enqueue ARQ job → Redis
  └─ return 202 { id, status: "pending", ... }

Worker picks up job:
  ├─ status → processing
  ├─ run Claude on each requirement (parallel, with timeout)
  ├─ aggregate score deterministically
  ├─ save SubmissionResults
  └─ status → completed (or failed)

GET /submissions/{id}
  └─ client polls until status = "completed"
```

---

## Design Notes

- **Fairness / compliance:** Automated resume screening is regulated in some jurisdictions (NYC Local Law 144, Illinois, California). Names and identifiers are not used in scoring. Every result is logged. Keep a human in the loop — no auto-rejection.
- **Privacy:** Resumes contain personal data. Plan for encrypted storage and a retention/deletion policy before any production use.
- **Scalability:** The worker is stateless and can be scaled horizontally by running multiple `worker` containers. The API is also stateless (ARQ pool is per-process).
