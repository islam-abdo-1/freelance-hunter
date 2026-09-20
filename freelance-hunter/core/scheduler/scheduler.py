"""
Scheduler for automated job hunting runs.
"""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from agents.orchestrator import FreelanceHunterOrchestrator, run_pipeline
from core.config.loader import get_config
from core.database.repository import DatabaseManager

logger = logging.getLogger(__name__)


class ScheduleInterval(str, Enum):
    HOURLY_1 = "1h"
    HOURLY_3 = "3h"
    HOURLY_6 = "6h"
    HOURLY_12 = "12h"
    DAILY = "24h"


@dataclass
class ScheduledJob:
    """Scheduled job configuration."""
    id: str
    name: str
    interval: ScheduleInterval
    priority: int = 1
    max_pages: int = 5
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    run_count: int = 0
    last_status: str = "pending"
    last_error: str | None = None


class JobHunterScheduler:
    """Scheduler for automated freelance job hunting."""
    
    def __init__(self, db_manager: DatabaseManager = None, config: dict[str, Any] | None = None):
        self.db_manager = db_manager
        self.config = config or get_config()._config
        self.scheduler_config = self.config.get("scheduler", {})
        
        # Initialize APScheduler
        self.scheduler = AsyncIOScheduler(
            timezone=self.scheduler_config.get("timezone", "Africa/Cairo")
        )
        
        # Default intervals
        self.default_interval = self.scheduler_config.get("default_interval_hours", 6)
        self.available_intervals = self.scheduler_config.get("intervals", ["1h", "3h", "6h", "12h", "24h"])
        
        # Scheduled jobs registry
        self.scheduled_jobs: dict[str, ScheduledJob] = {}
        
        # Orchestrator (set later)
        self.orchestrator: FreelanceHunterOrchestrator | None = None
        
        # Callbacks
        self.on_job_start: Callable | None = None
        self.on_job_complete: Callable | None = None
        self.on_job_error: Callable | None = None
    
    def set_orchestrator(self, orchestrator: FreelanceHunterOrchestrator):
        """Set the orchestrator instance."""
        self.orchestrator = orchestrator
    
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
            
            # Add default scheduled job if enabled
            if self.scheduler_config.get("enabled", True):
                self.add_scheduled_job(
                    job_id="default_scan",
                    name="Default Scan",
                    interval=ScheduleInterval(f"{self.default_interval}h"),
                    priority=1,
                    max_pages=5
                )
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler stopped")
    
    def add_scheduled_job(self, job_id: str, name: str, interval: ScheduleInterval,
                          priority: int = 1, max_pages: int = 5, 
                          cron_expression: str | None = None) -> ScheduledJob:
        """Add a scheduled job."""
        if job_id in self.scheduled_jobs:
            self.remove_scheduled_job(job_id)
        
        scheduled_job = ScheduledJob(
            id=job_id,
            name=name,
            interval=interval,
            priority=priority,
            max_pages=max_pages
        )
        
        # Determine trigger
        if cron_expression:
            trigger = CronTrigger.from_crontab(cron_expression, timezone=self.scheduler.timezone)
        else:
            hours = int(interval.value.replace('h', ''))
            trigger = IntervalTrigger(hours=hours, timezone=self.scheduler.timezone)
        
        # Add to APScheduler
        self.scheduler.add_job(
            self._run_scheduled_scan,
            trigger=trigger,
            id=job_id,
            name=name,
            kwargs={"job_id": job_id},
            replace_existing=True
        )
        
        # Calculate next run
        job = self.scheduler.get_job(job_id)
        if job:
            scheduled_job.next_run = job.next_run_time
        
        self.scheduled_jobs[job_id] = scheduled_job
        logger.info(f"Added scheduled job: {name} ({interval.value})")
        
        return scheduled_job
    
    def remove_scheduled_job(self, job_id: str):
        """Remove a scheduled job."""
        if job_id in self.scheduled_jobs:
            self.scheduler.remove_job(job_id)
            del self.scheduled_jobs[job_id]
            logger.info(f"Removed scheduled job: {job_id}")
    
    def enable_job(self, job_id: str):
        """Enable a scheduled job."""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].enabled = True
            self.scheduler.resume_job(job_id)
    
    def disable_job(self, job_id: str):
        """Disable a scheduled job."""
        if job_id in self.scheduled_jobs:
            self.scheduled_jobs[job_id].enabled = False
            self.scheduler.pause_job(job_id)
    
    def get_scheduled_jobs(self) -> dict[str, ScheduledJob]:
        """Get all scheduled jobs."""
        # Update next_run times
        for job_id, scheduled_job in self.scheduled_jobs.items():
            job = self.scheduler.get_job(job_id)
            if job:
                scheduled_job.next_run = job.next_run_time
        
        return self.scheduled_jobs
    
    def get_job_status(self, job_id: str) -> ScheduledJob | None:
        """Get status of a scheduled job."""
        return self.scheduled_jobs.get(job_id)
    
    async def _run_scheduled_scan(self, job_id: str):
        """Run a scheduled scan."""
        scheduled_job = self.scheduled_jobs.get(job_id)
        if not scheduled_job or not scheduled_job.enabled:
            return
        
        if not self.orchestrator:
            logger.error("Orchestrator not set, cannot run scheduled scan")
            return
        
        scheduled_job.last_run = datetime.utcnow()
        scheduled_job.run_count += 1
        scheduled_job.last_status = "running"
        
        logger.info(f"Starting scheduled scan: {scheduled_job.name}")
        
        # Call start callback
        if self.on_job_start:
            try:
                await self.on_job_start(scheduled_job)
            except Exception as e:
                logger.error(f"Start callback failed: {e}")
        
        try:
            # Run pipeline
            result = await run_pipeline(
                self.db_manager,
                priority=scheduled_job.priority,
                max_pages=scheduled_job.max_pages,
                triggered_by="scheduled"
            )
            
            scheduled_job.last_status = result.status
            scheduled_job.last_error = "; ".join(result.errors) if result.errors else None
            
            logger.info(
                f"Scheduled scan {scheduled_job.name} completed: "
                f"{result.status} in {result.duration_seconds:.2f}s, "
                f"found {result.verified_jobs} verified jobs"
            )
            
            # Call complete callback
            if self.on_job_complete:
                try:
                    await self.on_job_complete(scheduled_job, result)
                except Exception as e:
                    logger.error(f"Complete callback failed: {e}")
                    
        except Exception as e:
            scheduled_job.last_status = "failed"
            scheduled_job.last_error = str(e)
            logger.exception(f"Scheduled scan {scheduled_job.name} failed: {e}")
            
            # Call error callback
            if self.on_job_error:
                try:
                    await self.on_job_error(scheduled_job, e)
                except Exception as callback_error:
                    logger.error(f"Error callback failed: {callback_error}")
    
    async def run_now(self, job_id: str = "manual_run") -> Any:
        """Run a scan immediately."""
        if not self.orchestrator:
            logger.error("Orchestrator not set")
            return None
        
        logger.info("Running manual scan")
        return await run_pipeline(
            self.db_manager,
            priority=1,
            max_pages=5,
            triggered_by="manual"
        )
    
    def get_next_run_times(self) -> dict[str, datetime]:
        """Get next run times for all jobs."""
        next_runs = {}
        for job_id in self.scheduled_jobs:
            job = self.scheduler.get_job(job_id)
            if job:
                next_runs[job_id] = job.next_run_time
        return next_runs


# Global scheduler instance
_scheduler_instance: JobHunterScheduler | None = None


def get_scheduler(db_manager: DatabaseManager = None, config: dict[str, Any] | None = None) -> JobHunterScheduler:
    """Get global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = JobHunterScheduler(db_manager=db_manager, config=config)
    return _scheduler_instance


async def setup_default_scheduler(db_manager: DatabaseManager, orchestrator: FreelanceHunterOrchestrator):
    """Setup default scheduler with orchestrator."""
    scheduler = get_scheduler(db_manager)
    scheduler.set_orchestrator(orchestrator)
    
    # Add callbacks for logging
    async def on_start(job):
        logger.info(f"Scheduled job started: {job.name}")
    
    async def on_complete(job, result):
        logger.info(f"Scheduled job completed: {job.name} - {result.status}")
    
    async def on_error(job, error):
        logger.error(f"Scheduled job error: {job.name} - {error}")
    
    scheduler.on_job_start = on_start
    scheduler.on_job_complete = on_complete
    scheduler.on_job_error = on_error
    
    scheduler.start()
    return scheduler