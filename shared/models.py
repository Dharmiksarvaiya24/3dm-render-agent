from typing import Optional
# ===== shared/models.py =====

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped


class JobStatus(str, Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default=JobStatus.PENDING)
    priority = Column(String, nullable=False, default=Priority.NORMAL)
    worker_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    output_path = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_created_at", "created_at"),
        Index("ix_jobs_claim", "status", "priority", "created_at"),
    )


class JobResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    status: JobStatus
    priority: Priority
    worker_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    error_message: Optional[str] = None
    output_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class JobStatusUpdate(BaseModel):
    status: JobStatus
    output_path: Optional[str] = None
    error_message: Optional[str] = None


class WorkerHeartbeat(BaseModel):
    worker_id: str
    ip: str
    jobs_completed: int = 0
    current_job_id: Optional[str] = None
    utilization: Optional[float] = None
    temperature: Optional[float] = None
    fan_speed: Optional[float] = None


class StatsResponse(BaseModel):
    queue_depth: int
    done_today: int
    failed_today: int
    active_workers: int