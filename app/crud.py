"""
crud.py
Repository / Data Access Object layer. All raw database interaction
for JobApplication records is isolated here, kept fully async.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import JobApplication, JobStatus
from app.schemas import JobApplicationCreate


class JobNotFoundError(Exception):
    """Raised when a JobApplication record cannot be located by id."""

    def __init__(self, job_id: int):
        self.job_id = job_id
        super().__init__(f"JobApplication with id={job_id} was not found.")


async def create_job(
    db: AsyncSession,
    job_data: JobApplicationCreate,
    external_id: str | None = None,
    source_url: str | None = None,
) -> JobApplication:
    job = JobApplication(
        company_name=job_data.company_name,
        position_title=job_data.position_title,
        job_board=job_data.job_board,
        job_description_text=job_data.job_description_text,
        status=job_data.status,
        ai_tailored_notes=job_data.ai_tailored_notes,
        external_id=external_id,
        source_url=source_url,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_by_external_id(db: AsyncSession, external_id: str) -> JobApplication | None:
    result = await db.execute(select(JobApplication).where(JobApplication.external_id == external_id))
    return result.scalar_one_or_none()


async def get_all_jobs(db: AsyncSession) -> list[JobApplication]:
    result = await db.execute(select(JobApplication).order_by(JobApplication.id.desc()))
    return list(result.scalars().all())


async def get_job_by_id(db: AsyncSession, job_id: int) -> JobApplication:
    result = await db.execute(select(JobApplication).where(JobApplication.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise JobNotFoundError(job_id)
    return job


async def get_jobs_by_status(db: AsyncSession, status: JobStatus) -> list[JobApplication]:
    result = await db.execute(select(JobApplication).where(JobApplication.status == status))
    return list(result.scalars().all())


async def update_job_status(db: AsyncSession, job_id: int, new_status: JobStatus) -> JobApplication:
    job = await get_job_by_id(db, job_id)
    job.status = new_status
    if new_status == JobStatus.APPLIED and job.applied_date is None:
        job.applied_date = date.today()
    await db.commit()
    await db.refresh(job)
    return job


async def mark_job_applied(db: AsyncSession, job_id: int) -> JobApplication:
    job = await get_job_by_id(db, job_id)
    job.status = JobStatus.APPLIED
    job.applied_date = date.today()
    await db.commit()
    await db.refresh(job)
    return job


async def attach_ai_notes(db: AsyncSession, job_id: int, notes: str) -> JobApplication:
    job = await get_job_by_id(db, job_id)
    job.ai_tailored_notes = notes
    await db.commit()
    await db.refresh(job)
    return job


async def get_status_metrics(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(
        select(JobApplication.status, func.count(JobApplication.id)).group_by(JobApplication.status)
    )
    counts = {status.value: 0 for status in JobStatus}
    for status, count in result.all():
        key = status.value if isinstance(status, JobStatus) else status
        counts[key] = count
    return counts
