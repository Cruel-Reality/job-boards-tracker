from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.orm_models import SectorEnum, SizeEnum, JobStatusEnum


class CanonicalJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    source_job_id: str
    company: str
    title: str
    url: str

    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    is_remote: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ServiceInfo(BaseModel):
    status: str
    service: str
    uptime_seconds: int
    version: str


class CompanyBase(BaseModel):
    source: str
    company: str
    board: str
    sector: SectorEnum | None = None
    size: SizeEnum | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

class JobApplicationBase(BaseModel):
    job_posting_id : int
    status: JobStatusEnum
    notes: str | None = None
    applied_at: datetime | None = None 

class JobApplicationCreate(JobApplicationBase):
    pass 

class JobApplicationOut(JobApplicationBase):
    id: int
    created_at: datetime
    updated_at: datetime
    