# 🤖 AI-Driven Job Application & Tracking Agent

A robust FastAPI backend service that pulls real-time job listings from the **Adzuna Job Search API**, processes them via a rule-based skill-overlap analysis engine, and tracks individual application states through a structured pipeline. Featuring a lightweight, responsive vanilla JS Kanban board frontend.

<p align="center">
  <img src="kanban.gif" alt="Kanban Board Demo" max-width="500px" width="100%" />
</p>

---

## ✨ Key Features

* **Automated Ingestion** — Fetch live job data using keyword and location targets via an asynchronous HTTP client, filtering out pre-existing duplicates automatically.
* **Granular Review Pipeline** — Stage raw scraped listings in a `PENDING_REVIEW` phase to separate interesting leads from background noise.
* **Skill Tailoring Engine** — Evaluate job descriptions against specified resume target keywords to map skills and extract strategic talking points.
* **State Machine Tracking** — Step applications seamlessly across states:  
  `SCRAPED` ➔ `PENDING_REVIEW` ➔ `APPLIED` ➔ `INTERVIEWING` ➔ `OFFERED` / `REJECTED`

---

## 🏗️ Architecture

```text
       ┌────────────────────────────────────────────────────────┐
       │               Adzuna Job Search API                    │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   │ (httpx async client)
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                   FastAPI Backend                      │
       │                                                        │
       │   Router Layer      [main.py]                          │
       │        ▼                                               │
       │   Service Layer     [services.py]  🠔 Scraper & Engine  │
       │        ▼                                               │
       │   Repository Layer  [crud.py]                          │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │            SQLite Database (jobs_agent.db)             │
       │           & Static UI Served at /ui/                   │
       └────────────────────────────────────────────────────────┘


📂 Layer Breakdown

File Component,Domain Responsibility
app/models.py,"SQLAlchemy 2.0 async models, JobStatus enums, and database engine core."
app/schemas.py,Pydantic v2 request/response strong type validation schemas.
app/crud.py,Repository layer decoupling raw database mutations and queries.
app/services.py,"Adzuna API communications client, data deduplication, and tailoring algorithms."
app/main.py,"REST API routing declarations, lifecycle execution hooks, and global handlers."
static/index.html,Client-side Kanban UI engine written in buildless Vanilla ES6+ JavaScript.

⚙️ Core API Endpoints

Method,Endpoint,Payload / Parameters,Functionality
POST,/api/jobs/scrape,"{ ""keywords"": ""..."", ""location"": ""..."" }",Triggers background Adzuna crawling (Returns 202 Accepted)
GET,/api/jobs,None,Queries comprehensive collection sorted chronologically for the Kanban engine
GET,/api/jobs/pending,None,Exposes targeted isolation of listings flagged inside PENDING_REVIEW
PUT,/api/jobs/{id}/apply,None,Advances workflow status to APPLIED and commits an applied_date stamp
PUT,/api/jobs/{id}/status,"{ ""new_status"": ""..."" }",Explicit administrative route allowing manual pipeline manipulation
PUT,/api/jobs/{id}/tailor,None,Runs the processing parser engine against target resume goals
GET,/api/jobs/metrics,None,Computes aggregation counters grouped natively by active state keys

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

