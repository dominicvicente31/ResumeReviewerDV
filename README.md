# ResumeReviewerDV

An AI-powered resume screening tool. Admins define job profiles with weighted requirements. Users upload resumes and receive an alignment score with per-requirement verdicts, evidence quotes, and confidence ratings — all backed by Claude AI and deterministic scoring logic.

## Status

Backend and frontend are feature-complete. Core infrastructure (auth, scoring pipeline, job queue, Docker) is production-hardened. See the [Before Deploying](#before-deploying) checklist for remaining gaps before a first real deployment.

---

## Features

### User
- Sign up / log in with JWT auth (access + refresh tokens)
- Email verification on signup (resendable, 24-hour token)
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
| Database (local) | PostgreSQL via Docker |
| Database (production) | [Neon](https://neon.tech) — swap `DATABASE_URL` to the Neon connection string, no code changes |
| Auth | JWT (access + refresh tokens), bcrypt, token revocation, email verification |
| Email | aiosmtplib (SMTP); logs link to stdout when `SMTP_HOST` is unset |
| Job Queue | ARQ (Redis-backed async worker) |
| AI | Anthropic Claude via structured output |
| Parsing | pdfplumber (PDF), python-docx (DOCX) |
| Config | Pydantic Settings |
| Frontend | Next.js 16 (App Router, TypeScript) + Tailwind CSS + shadcn/ui |
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

## Running Locally

### Option A — Docker (recommended)

The fastest way to run everything. One command starts all five services.

**1. Create your `.env`**

```bash
cp backend/.env.example .env
```

Fill in the three required values:

```env
JWT_SECRET_KEY=        # python -c "import secrets; print(secrets.token_hex(32))"
ANTHROPIC_API_KEY=     # from console.anthropic.com
POSTGRES_PASSWORD=     # anything, e.g. localdev
POSTGRES_DB=resumereviewerdv
```

**2. Build and start**

```bash
docker-compose up --build
```

| Container | URL | Role |
|---|---|---|
| `frontend` | http://localhost:3000 | Next.js app |
| `app` | http://localhost:8000 | FastAPI backend |
| `worker` | — | ARQ scoring worker |
| `db` | — | PostgreSQL 16 |
| `redis` | — | Redis 7 (job queue) |

API docs: http://localhost:8000/docs

**3. First-time only — create the database tables**

```bash
docker-compose exec app alembic upgrade head
```

> If Alembic migrations haven't been initialised yet, `create_all` in the app lifespan handles the initial schema automatically. Run the above command once migrations are set up.

---

### Option B — Local processes (hot reload)

Use this when actively developing — both the backend and frontend support hot reload.

**Prerequisites:** Python 3.11+, Node 18+, PostgreSQL, Redis (or start just the DB and Redis via Docker)

**Start just the backing services:**

```bash
docker-compose up db redis
```

**Backend**

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Configure environment
cp backend/.env.example .env
# Fill in JWT_SECRET_KEY, ANTHROPIC_API_KEY, DATABASE_URL, REDIS_URL

# Start the API (hot reload)
uvicorn backend.main:app --reload

# Start the worker (separate terminal)
python -m arq backend.worker.WorkerSettings
```

**Frontend**

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

Frontend runs on http://localhost:3000, backend on http://localhost:8000. The `frontend/.env.local` already points `NEXT_PUBLIC_API_URL` at `http://localhost:8000`.

---

### Useful Docker commands

```bash
# Tail logs
docker-compose logs -f app
docker-compose logs -f worker
docker-compose logs -f frontend

# Stop everything
docker-compose down

# Stop and wipe all data volumes
docker-compose down -v

# Rebuild a single service after code changes
docker-compose up --build frontend
docker-compose up --build app
```

---

## API Reference

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Register — sends verification email (5/min rate limit) |
| POST | `/auth/login` | Login (10/min, lockout after 10 failures) |
| POST | `/auth/logout` | Revoke current access token |
| POST | `/auth/refresh` | Issue new token pair from refresh token |
| GET | `/auth/me` | Current user info (includes `is_verified`) |
| GET | `/auth/verify-email?token=` | Mark email as verified via token from signup email |
| POST | `/auth/resend-verification` | Re-send verification email (3/hour, silent on unknown addresses) |

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

### Admin
| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/users` | List all users |
| POST | `/admin/users` | Create a new user |

### System
| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | DB connectivity check |

---

## Security Highlights

- Passwords: bcrypt with strength requirements (8+ chars, upper, lower, digit, special)
- Tokens: JWT with `jti`, typed (`access`/`refresh`/`verify_email`), token revocation on logout
- Email verification: 24-hour signed JWT; resend endpoint is silent on unknown addresses to prevent enumeration
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

## Before Deploying

The backend is feature-complete but these items must be addressed before a production deployment:

| Item | Status | Notes |
|---|---|---|
| Alembic migrations | ❌ Missing | `alembic/` directory doesn't exist. `create_all` works for a fresh DB but won't handle schema changes in production. Run `alembic init alembic`, create a baseline, then generate a migration for the `is_verified` column. |
| SMTP configured | ⚠️ Optional | Without `SMTP_HOST`, verification links log to stdout only. Set real SMTP creds before launch. |
| Sentry initialized | ⚠️ Wired but inactive | `SENTRY_DSN` is in config but `sentry_sdk` is never called in `main.py`. Add `sentry_sdk.init(dsn=settings.sentry_dsn)` if you want error tracking. |
| `is_verified` enforcement | ⚠️ Unenforced | The field exists and gets set, but login does not check it. Decide whether unverified users should be blocked or just restricted, and add the check to the login endpoint. |
| Test suite | ❌ Missing | No tests exist. At minimum: auth flow, submission upload + status polling, score aggregation logic. |
| Secrets rotation plan | ❌ Not defined | Document how to rotate `JWT_SECRET_KEY` (invalidates all sessions) and `ANTHROPIC_API_KEY`. |
| Resume file storage | ⚠️ Local disk | Files are written to `UPLOAD_DIR` on the container filesystem. For multi-container or cloud deployments, swap to S3/GCS before launch. |

---

## Design Notes

- **Fairness / compliance:** Automated resume screening is regulated in some jurisdictions (NYC Local Law 144, Illinois, California). Names and identifiers are not used in scoring. Every result is logged. Keep a human in the loop — no auto-rejection.
- **Privacy:** Resumes contain personal data. Plan for encrypted storage and a retention/deletion policy before any production use.
- **Scalability:** The worker is stateless and can be scaled horizontally by running multiple `worker` containers. The API is also stateless (ARQ pool is per-process).
