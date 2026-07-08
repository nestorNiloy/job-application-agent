"""
main.py
FastAPI router setup, configuration, global error handling, and
application entry point for the AI-Driven Autonomous Job Application
& Tracking Agent.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, services
from app.crud import JobNotFoundError
from app.models import get_db, init_db
from app.schemas import (
    JobApplicationResponse,
    JobApplicationStatusUpdate,
    MetricsResponse,
    ScrapeAcceptedResponse,
    ScrapeRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AI-Driven Autonomous Job Application & Tracking Agent",
    description=(
        "A backend service that automates job discovery via the Adzuna Job "
        "Search API, tailors applications with a rule-based skill-matching "
        "engine, and tracks application status through a human-in-the-loop "
        "state machine."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(JobNotFoundError)
async def job_not_found_handler(request: Request, exc: JobNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "JOB_NOT_FOUND",
            "detail": str(exc),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


async def _run_scrape_background(keywords: str, location: str) -> None:
    """Background task wrapper: opens its own DB session for the scrape run."""
    async with models.AsyncSessionLocal() as session:
        await services.scraper_service.run_scrape(session, keywords, location)


@app.post(
    "/api/jobs/scrape",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScrapeAcceptedResponse,
    tags=["Scraping"],
    summary="Trigger a background scrape against the Adzuna Job Search API",
)
async def trigger_scrape(payload: ScrapeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_scrape_background, payload.keywords, payload.location)
    return ScrapeAcceptedResponse(
        message="Scraping job accepted and queued for background execution.",
        keywords=payload.keywords,
        location=payload.location,
        triggered_at=datetime.utcnow(),
    )


@app.get(
    "/api/jobs",
    response_model=list[JobApplicationResponse],
    tags=["Review Queue"],
    summary="Fetch every job application record, newest first (powers the Kanban board)",
)
async def get_all_jobs(db: AsyncSession = Depends(get_db)):
    jobs = await crud.get_all_jobs(db)
    return jobs


@app.get(
    "/api/jobs/pending",
    response_model=list[JobApplicationResponse],
    tags=["Review Queue"],
    summary="Fetch staged applications awaiting human review",
)
async def get_pending_jobs(db: AsyncSession = Depends(get_db)):
    jobs = await crud.get_jobs_by_status(db, models.JobStatus.PENDING_REVIEW)
    return jobs


@app.put(
    "/api/jobs/{job_id}/tailor",
    response_model=JobApplicationResponse,
    tags=["AI Tailoring"],
    summary="Run the rule-based tailoring engine against a job and store the notes",
)
async def tailor_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await crud.get_job_by_id(db, job_id)
    notes = await services.tailoring_service.generate_tailored_notes(job.job_description_text)
    job = await crud.attach_ai_notes(db, job_id, notes)
    return job


@app.put(
    "/api/jobs/{job_id}/apply",
    response_model=JobApplicationResponse,
    tags=["Application Lifecycle"],
    summary="Execute an authorized transition of a job to the APPLIED state",
)
async def apply_to_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await crud.mark_job_applied(db, job_id)
    return job


@app.put(
    "/api/jobs/{job_id}/status",
    response_model=JobApplicationResponse,
    tags=["Application Lifecycle"],
    summary="Manually update the tracked status of a job application",
)
async def update_status(job_id: int, payload: JobApplicationStatusUpdate, db: AsyncSession = Depends(get_db)):
    job = await crud.update_job_status(db, job_id, payload.new_status)
    return job


@app.get(
    "/api/jobs/metrics",
    response_model=MetricsResponse,
    tags=["Analytics"],
    summary="Return total application counts grouped by state",
)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    counts = await crud.get_status_metrics(db)
    return MetricsResponse(total=sum(counts.values()), by_status=counts)


@app.get("/api/health", tags=["Health"], summary="Health check")
async def health():
    return {"status": "ok", "service": "job-application-agent"}


# Serves the Kanban board frontend from /ui (e.g. /ui/index.html).
# Mounted after all /api routes so it never shadows them.
app.mount("/ui", StaticFiles(directory="static", html=True), name="static")
