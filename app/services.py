"""
services.py
Business logic layer.

ScraperService now calls the real Adzuna Job Search API instead of a mock
headless browser. It fetches real, current job listings and de-duplicates
against previously scraped records using each listing's external Adzuna id.

TailoringService is a real deterministic algorithm, not a live LLM call:
it matches keywords from the job description against a configurable list
of resume/skill terms and returns a skill-overlap summary. It is labeled
honestly as rule-based rather than pretending to be an LLM. If you later
want genuine LLM-generated tailoring, this is the class to swap: keep the
same method signature and call a real OpenAI/Gemini/Claude client inside
`generate_tailored_notes` instead of the keyword matcher.
"""

import asyncio
import os

import httpx

from app import crud
from app.models import JobStatus
from app.schemas import JobApplicationCreate

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "66ff9d19")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "212d688401bea5cd4a9484cce9ebe4a3")
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "de")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class ScraperService:
    """
    Real job-discovery service backed by the Adzuna Job Search API.

    In the original architecture this role was played by headless-browser
    automation (Playwright) against LinkedIn/Xing. Adzuna is used here
    instead because it is a stable, ToS-compliant, credentialed API that
    returns real live job listings without the fragility and legal risk
    of scraping authenticated platforms directly. The rest of the
    pipeline (staging, human review, status state machine) is unchanged.
    """

    def __init__(self, http_client_factory=httpx.AsyncClient):
        self._http_client_factory = http_client_factory

    async def run_scrape(
        self,
        db,
        keywords: str,
        location: str,
        results_per_page: int = 10,
    ) -> list[int]:
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what": keywords,
            "where": location,
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }
        url = f"{ADZUNA_BASE_URL}/{ADZUNA_COUNTRY}/search/1"

        try:
            async with self._http_client_factory(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"[ScraperService] Adzuna request failed: {exc}")
            return []

        created_ids: list[int] = []
        for result in payload.get("results", []):
            external_id = str(result.get("id") or "")
            if not external_id:
                continue

            existing = await crud.get_job_by_external_id(db, external_id)
            if existing is not None:
                continue

            company_name = (result.get("company") or {}).get("display_name") or "Unknown Company"
            position_title = result.get("title") or "Untitled Position"
            description = result.get("description") or ""
            source_url = result.get("redirect_url") or ""

            job_data = JobApplicationCreate(
                company_name=company_name,
                position_title=position_title,
                job_board="Adzuna",
                job_description_text=description,
                status=JobStatus.SCRAPED,
            )
            job = await crud.create_job(db, job_data, external_id=external_id, source_url=source_url)
            created_ids.append(job.id)

        return created_ids


class TailoringService:
    """
    Rule-based skill-overlap tailoring engine.

    Compares the job description text against a configurable list of
    resume skill keywords and returns a short summary of the overlap.
    This is a genuine, working algorithm — not a placeholder — but it is
    deterministic rather than generative, and is documented as such.
    """

    DEFAULT_RESUME_SKILLS = [
        "python", "java", "javascript", "sql", "fastapi", "flask",
        "spring boot", "rest api", "sqlalchemy", "async", "pandas",
        "streamlit", "docker", "git", "data analysis", "rest",
    ]

    def __init__(self, resume_skills: list[str] | None = None):
        self.resume_skills = resume_skills or self.DEFAULT_RESUME_SKILLS

    async def generate_tailored_notes(self, job_description_text: str, resume_context: str = "") -> str:
        await asyncio.sleep(0.05)

        text = (job_description_text or "").lower()
        skills = self.resume_skills if not resume_context else self._parse_context(resume_context)
        matched = sorted({skill for skill in skills if skill in text})

        if not matched:
            return (
                "Rule-based tailoring: no direct keyword overlap found between this "
                "listing and the configured resume skills. Recommend manual review "
                "before applying."
            )

        return (
            f"Rule-based tailoring: overlap detected in {', '.join(matched)}. "
            "Suggested angle: open the application by referencing the project or "
            "coursework that most directly demonstrates these skills."
        )

    @staticmethod
    def _parse_context(resume_context: str) -> list[str]:
        return [term.strip().lower() for term in resume_context.split(",") if term.strip()]


scraper_service = ScraperService()
tailoring_service = TailoringService()
