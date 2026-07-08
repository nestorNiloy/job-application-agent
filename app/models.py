"""
models.py
SQLAlchemy 2.0 async models and database engine/session configuration
for the AI-Driven Autonomous Job Application & Tracking Agent.
"""

import enum
from datetime import date
from typing import Optional

from sqlalchemy import Date, Enum, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "sqlite+aiosqlite:///./jobs_agent.db"

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class JobStatus(str, enum.Enum):
    SCRAPED = "SCRAPED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPLIED = "APPLIED"
    INTERVIEWING = "INTERVIEWING"
    REJECTED = "REJECTED"
    OFFERED = "OFFERED"


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_board: Mapped[str] = mapped_column(String(100), nullable=False)
    job_description_text: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=32),
        nullable=False,
        default=JobStatus.SCRAPED,
    )
    applied_date: Mapped[date] = mapped_column(Date, nullable=True)
    ai_tailored_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Fields added beyond the original blueprint to support a real job
    # source: external_id lets re-running a scrape skip listings already
    # in the database, and source_url gives the frontend a real link to
    # the live posting on Adzuna.
    external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


async def init_db() -> None:
    """Create all tables on startup if they do not already exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session
