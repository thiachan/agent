"""
Job Tracker Service - Manages async generation jobs
Tracks status of long-running tasks like podcast generation
"""
import time
import uuid
import threading
from typing import Dict, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Job:
    def __init__(self, job_id: str, job_type: str, user_id: int):
        self.job_id = job_id
        self.job_type = job_type
        self.user_id = user_id
        self.status = JobStatus.PENDING
        self.progress = 0
        self.message = "Job created"
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at: Optional[float] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
    
    def update(self, status: JobStatus = None, progress: int = None, message: str = None, result: Dict = None, error: str = None):
        """Update job status"""
        if status:
            self.status = status
        if progress is not None:
            self.progress = progress
        if message:
            self.message = message
        if result:
            self.result = result
        if error:
            self.error = error
        
        self.updated_at = time.time()
        
        if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
            self.completed_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error": self.error
        }

class JobTracker:
    """Manages async job tracking"""
    
    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()
        # Auto-cleanup old jobs after 1 hour
        self.cleanup_interval = 3600
        self.last_cleanup = time.time()
    
    def create_job(self, job_type: str, user_id: int) -> Job:
        """Create a new job"""
        job_id = str(uuid.uuid4())
        job = Job(job_id, job_type, user_id)
        
        with self.lock:
            self.jobs[job_id] = job
            logger.info(f"Created job {job_id} for user {user_id}, type: {job_type}")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def update_job(self, job_id: str, **kwargs):
        """Update a job"""
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.update(**kwargs)
                logger.info(f"[JobTracker] Updated job {job_id}: progress={job.progress}%, status={job.status.value}, message='{job.message}'")
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> list:
        """Get jobs for a user"""
        with self.lock:
            user_jobs = [job for job in self.jobs.values() if job.user_id == user_id]
            # Sort by created_at descending
            user_jobs.sort(key=lambda j: j.created_at, reverse=True)
            return [job.to_dict() for job in user_jobs[:limit]]
    
    def cleanup_old_jobs(self):
        """Remove completed jobs older than 1 hour"""
        now = time.time()
        if now - self.last_cleanup < 300:  # Cleanup every 5 minutes max
            return
        
        with self.lock:
            old_jobs = [
                job_id for job_id, job in self.jobs.items()
                if job.completed_at and (now - job.completed_at > 3600)
            ]
            
            for job_id in old_jobs:
                del self.jobs[job_id]
                logger.info(f"Cleaned up old job {job_id}")
            
            self.last_cleanup = now

# Global job tracker instance
job_tracker = JobTracker()

