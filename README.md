# AI-Driven Job Application & Tracking Agent

A backend service that pulls **real, live job listings from the Adzuna Job Search API**,
runs a keyword-based skill-matching engine to surface relevant roles, and tracks every
application through a human-in-the-loop state machine — from discovery to offer.

A lightweight Kanban board frontend visualizes the full pipeline in real time.

![Kanban Board Screenshot](kanban.gif)

---

## What it does

1. **Scrape** — POST a keyword + location query; the backend fetches real listings from
   Adzuna and stores them, skipping duplicates it has already seen.
2. **Review** — Move interesting listings to *Pending Review* before committing to apply.
3. **Tailor** — Run a rule-based skill-overlap analysis against your resume keywords;
   the engine highlights which of your skills appear in the job description and suggests
   an application angle.
4. **Track** — Advance each application through `SCRAPED → PENDING_REVIEW → APPLIED →
   INTERVIEWING → OFFERED / REJECTED` with a single button click.

---

## Architecture

Adzuna Job Search API
│
▼  (httpx async HTTP client)
┌─────────────────────────────────────┐
│         FastAPI Backend             │
│                                     │
│  Router Layer       main.py         │
│       ▼                             │
│  Service Layer      services.py     │  ← Adzuna scraper + tailoring engine
│       ▼                             │
│  Repository Layer   crud.py         │
└────────────────┬────────────────────┘
▼
SQLite  (jobs_agent.db)
Static frontend served at /ui/

**Layer breakdown**

| File | Responsibility |
|---|---|
| `app/models.py` | SQLAlchemy 2.0 async models, `JobStatus` enum, engine setup |
| `app/schemas.py` | Pydantic v2 request / response validation |
| `app/crud.py` | Repository layer — all database access lives here |
| `app/services.py` | Adzuna API client, deduplication logic, tailoring engine |
| `app/main.py` | FastAPI routes, lifespan startup, global 404 handler |
| `static/index.html` | Kanban board — vanilla JS, no build step |

---

## API Endpoints

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/api/jobs/scrape` | `{keywords, location}` | Queues a real Adzuna search (202 Accepted) |
| `GET` | `/api/jobs` | — | All jobs, newest first — feeds the Kanban board |
| `GET` | `/api/jobs/pending` | — | Jobs in `PENDING_REVIEW` only |
| `PUT` | `/api/jobs/{id}/apply` | — | Transitions a job to `APPLIED`, stamps `applied_date` |
| `PUT` | `/api/jobs/{id}/status` | `{new_status}` | Manual status update |
| `PUT` | `/api/jobs/{id}/tailor` | — | Runs the tailoring engine, saves the notes |
| `GET` | `/api/jobs/metrics` | — | Counts grouped by status |

Interactive API docs are available at `/docs` (Swagger UI) and `/redoc`.

---

## Running locally

```bash
git clone https://github.com/nestorNiloy/job-application-agent.git
cd job-application-agent

pip install -r requirements.txt

cp .env.example .env          # add your Adzuna credentials
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/ui/` for the Kanban board, or `/docs` for the full
interactive API documentation.

**Environment variables**

| Variable | Description |
|---|---|
| `ADZUNA_APP_ID` | Adzuna application ID |
| `ADZUNA_APP_KEY` | Adzuna application key |
| `ADZUNA_COUNTRY` | Two-letter country code (default: `de`) |

Register for free credentials at [developer.adzuna.com](https://developer.adzuna.com).

---

## Tech stack

Python 3.11 · FastAPI · SQLAlchemy 2.0 (async) · SQLite · aiosqlite · Pydantic v2 · httpx · Uvicorn
