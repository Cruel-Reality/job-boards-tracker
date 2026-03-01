from datetime import datetime

from pydantic import BaseModel


class CanonicalJob(BaseModel):
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
    updaated_at: datetime | None = None


class ServiceInfo(BaseModel):
    status: str
    service: str
    uptime_seconds: int
    version: str


class CompanyBase(BaseModel):
    source: str
    company: str
    board: str
    sector: str | None = None
    size: str | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyOut(CompanyBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True
