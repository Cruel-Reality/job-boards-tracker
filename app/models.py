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


class ServiceInfo(BaseModel):
    status: str
    service: str
    uptime_seconds: int
    version: str
