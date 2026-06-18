# ===== controller/job_queue.py =====

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from shared.logger import get_logger
from shared.models import Base, Job, JobStatus, Priority

logger = get_logger("queue")

_db_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "render_agent.db"
)
_engine = create_engine(f"sqlite:///{_db_path}", echo=False, connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(bind=_engine)


def init_db() -> None:
    logger.info("Initializing database...")
    Base.metadata.create_all(_engine)
    logger.info(f"Database initialized at {_db_path}")


def create_job(file_path: str, file_name: Optional[str] = None) -> Job:
    try:
        if file_name is None:
            file_name = os.path.basename(file_path)
        logger.info(f"Creating job for file: {file_name}")
        with _SessionLocal() as session:
            job = Job(
                file_path=file_path,
                file_name=file_name,
                status=JobStatus.PENDING,
                priority=Priority.NORMAL,
                retry_count=0,
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            logger.info(f"Job created: {job.id} ({file_name})")
            return job
    except Exception as e:
        logger.error(f"Failed to create job for {file_path}: {e}")
        raise


def claim_next_job(worker_id: str) -> Optional[Job]:
    try:
        with _SessionLocal() as session:
            job = (
                session.query(Job)
                .filter(Job.status == JobStatus.PENDING)
                .order_by(
                    Job.priority.desc(),
                    Job.created_at.asc(),
                )
                .with_for_update()
                .first()
            )
            if job is None:
                session.rollback()
                return None
            job.status = JobStatus.CLAIMED
            job.worker_id = worker_id
            job.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(job)
            logger.info(f"Job {job.id} claimed by worker {worker_id}")
            return job
    except Exception as e:
        logger.error(f"Error claiming job for worker {worker_id}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


def update_job_status(
    job_id: str,
    status: str,
    output_path: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Optional[Job]:
    try:
        with _SessionLocal() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if job is None:
                logger.error(f"Job {job_id} not found for status update")
                return None

            if status == JobStatus.FAILED:
                if job.retry_count < 3:
                    job.status = JobStatus.PENDING
                    job.retry_count = job.retry_count + 1
                    job.worker_id = None
                    job.error_message = error_message
                    logger.info(
                        f"Job {job_id} failed — retry {job.retry_count}/3. Reset to PENDING."
                    )
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = error_message
                    logger.info(f"Job {job_id} permanently failed after {job.retry_count} retries.")
            else:
                job.status = status
                if output_path is not None:
                    job.output_path = output_path
                if error_message is not None:
                    job.error_message = error_message
                logger.info(f"Job {job_id} status updated to {status}")

            job.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(job)
            return job
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return None


def get_all_jobs(status_filter: Optional[str] = None) -> List[Job]:
    try:
        with _SessionLocal() as session:
            q = session.query(Job).order_by(desc(Job.created_at))
            if status_filter:
                q = q.filter(Job.status == status_filter)
            return q.all()
    except Exception as e:
        logger.error(f"Error fetching jobs: {e}")
        return []


def get_stats() -> dict:
    try:
        with _SessionLocal() as session:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            queue_depth = (
                session.query(Job)
                .filter(
                    Job.status.in_(
                        [JobStatus.PENDING, JobStatus.CLAIMED, JobStatus.PROCESSING]
                    )
                )
                .count()
            )
            done_today = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.COMPLETED,
                    Job.updated_at >= today,
                )
                .count()
            )
            failed_today = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.FAILED,
                    Job.updated_at >= today,
                )
                .count()
            )
            return {
                "queue_depth": queue_depth,
                "done_today": done_today,
                "failed_today": failed_today,
            }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"queue_depth": 0, "done_today": 0, "failed_today": 0}


def clear_all_jobs() -> int:
    try:
        with _SessionLocal() as session:
            count = session.query(Job).delete()
            session.commit()
            logger.info(f"Cleared {count} job(s) from database")
            return count
    except Exception as e:
        logger.error(f"Error clearing jobs: {e}")
        return 0


def reset_stuck_jobs(timeout_minutes: int = 30) -> int:
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        with _SessionLocal() as session:
            stuck = (
                session.query(Job)
                .filter(
                    Job.status == JobStatus.CLAIMED,
                    Job.updated_at <= cutoff,
                )
                .all()
            )
            count = 0
            for job in stuck:
                job.status = JobStatus.PENDING
                job.worker_id = None
                job.updated_at = datetime.utcnow()
                count += 1
            session.commit()
            if count > 0:
                logger.info(f"Reset {count} stuck job(s) back to PENDING")
            return count
    except Exception as e:
        logger.error(f"Error resetting stuck jobs: {e}")
        return 0