"""
schemas.py
Pydantic v2 validation schemas for job application creation,
status mutation, scraping requests, and response serialization.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import JobStatus


class JobApplicationBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255, examples=["BMW"])
    position_title: str = Field(..., min_length=1, max_length=255, examples=["Data Analyst Werkstudent"])
    job_board: str = Field(..., min_length=1, max_length=100, examples=["LinkedIn"])
    job_description_text: Optional[str] = None


class JobApplicationCreate(JobApplicationBase):
    status: JobStatus = JobStatus.SCRAPED
    ai_tailored_notes: Optional[str] = None


class JobApplicationStatusUpdate(BaseModel):
    new_status: JobStatus


class JobApplicationResponse(JobApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: JobStatus
    applied_date: Optional[date] = None
    ai_tailored_notes: Optional[str] = None
    source_url: Optional[str] = None


class ScrapeRequest(BaseModel):
    keywords: str = Field(..., min_length=1, examples=["Werkstudent Data Analyst"])
    location: str = Field(..., min_length=1, examples=["Hamburg, Germany"])


class ScrapeAcceptedResponse(BaseModel):
    message: str
    keywords: str
    location: str
    triggered_at: datetime


class MetricsResponse(BaseModel):
    total: int
    by_status: dict[str, int]


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: datetime
