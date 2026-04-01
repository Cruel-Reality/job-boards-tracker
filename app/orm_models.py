from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_source_source_job_id"),
    )

    application: Mapped["JobApplication | None"] = relationship(back_populates="job")

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_job_id: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    location: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_remote: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class SectorEnum(PyEnum):
    pharma = "pharma"
    tech = "tech"
    cybersecurity = "cybersecurity"
    finance = "finance"
    robotics = "robotics"
    healthcare = "healthcare"


class SizeEnum(PyEnum):
    startup = "startup"
    small = "small"
    medium = "medium"
    big = "big"


class Company(Base):
    __tablename__ = "company_sources"
    __table_args__ = (
        UniqueConstraint("source", "company", "board", name="uq_company_source_board"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    board: Mapped[str] = mapped_column(String, nullable=False)

    sector: Mapped[SectorEnum | None] = mapped_column(Enum(SectorEnum), nullable=True)
    size: Mapped[SizeEnum | None] = mapped_column(Enum(SizeEnum), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class JobStatusEnum(PyEnum):
    applied = "applied"
    unapplied = "unapplied"
    rejected = "rejected"
    offer = "offer"


class JobApplication(Base):
    __tablename__ = "job_applications"

    job: Mapped["JobPosting"] = relationship(back_populates="application")

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id"), nullable=False, unique=True
    )
    status: Mapped[JobStatusEnum] = mapped_column(
        Enum(JobStatusEnum), nullable=False, default=JobStatusEnum.unapplied
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
