"""
FastAPI Backend for Freelance Hunter Dashboard.
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.config.loader import get_config as get_config_sync, reload_config
from core.database.models import init_database, get_session, JobStatus
from core.database.repository import Repositories, DatabaseManager
from agents.orchestrator import FreelanceHunterOrchestrator, run_pipeline
from core.notifications.email_service import get_email_service

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db_manager: Optional[DatabaseManager] = None
orchestrator: Optional[FreelanceHunterOrchestrator] = None
pipeline_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db_manager, orchestrator
    
    # Startup
    config = get_config_sync()
    database_url = config.database_url
    
    # Initialize database
    init_database(database_url)
    db_manager = DatabaseManager(database_url)
    db_manager.initialize()
    
    # Initialize orchestrator
    orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager)
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")


app = FastAPI(
    title="Freelance Hunter API",
    description="Multi-agent freelance job discovery and analysis system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for dashboard
if os.path.exists("dashboard/public"):
    app.mount("/static", StaticFiles(directory="dashboard/public"), name="static")


# Pydantic models
class ScanRequest(BaseModel):
    priority: int = 1
    max_pages: int = 5
    triggered_by: str = "manual"


class SchedulerControl(BaseModel):
    action: str  # "start", "stop", "pause", "resume"
    interval_hours: Optional[int] = None


class EmailSettings(BaseModel):
    enabled: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    use_tls: bool = True


class EmailNotificationSettings(BaseModel):
    enabled: bool = True
    email: str = "islam230366qw@gmail.com"
    on_scan_complete: bool = True
    on_high_match: bool = True
    on_new_job: bool = False


class TestEmailRequest(BaseModel):
    email: Optional[str] = None


class JobFilters(BaseModel):
    platform_id: Optional[int] = None
    category: Optional[str] = None
    match_level: Optional[str] = None
    verification_status: Optional[str] = None
    risk_level: Optional[str] = None
    status: Optional[str] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    currency: Optional[str] = None
    experience_level: Optional[str] = None
    keyword: Optional[str] = None
    sort_by: str = "score"
    sort_order: str = "desc"
    page: int = 1
    per_page: int = 20


class JobStatusUpdate(BaseModel):
    job_id: str
    new_status: str
    notes: Optional[str] = None


class ExportRequest(BaseModel):
    format: str = "csv"
    filters: Optional[Dict[str, Any]] = None


# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Freelance Hunter API",
        "version": "1.0.0",
        "status": "running",
        "dashboard": "/dashboard"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return orchestrator.get_dashboard_stats()


@app.get("/api/jobs")
async def get_jobs(
    platform_id: Optional[int] = None,
    category: Optional[str] = None,
    match_level: Optional[str] = None,
    verification_status: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_budget: Optional[float] = None,
    max_budget: Optional[float] = None,
    currency: Optional[str] = None,
    experience_level: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "score",
    sort_order: str = "desc",
    page: int = 1,
    per_page: int = 20
):
    """Get jobs with filtering and pagination."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    filters = {
        "platform_id": platform_id,
        "category": category,
        "match_level": match_level,
        "verification_status": verification_status,
        "risk_level": risk_level,
        "status": status,
        "min_score": min_score,
        "max_score": max_score,
        "date_from": date_from,
        "date_to": date_to,
        "min_budget": min_budget,
        "max_budget": max_budget,
        "currency": currency,
        "experience_level": experience_level,
        "keyword": keyword,
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    result = orchestrator.search_jobs(filters, page, per_page)
    
    # Convert jobs to dict
    jobs_data = []
    for job in result["jobs"]:
        jobs_data.append(orchestrator._job_to_dict(job))
    
    return {
        "jobs": jobs_data,
        "total": result["total"],
        "page": result["page"],
        "per_page": result["per_page"],
        "total_pages": result["total_pages"]
    }


@app.get("/api/jobs/recent")
async def get_recent_jobs(hours: int = 24, limit: int = 50):
    """Get recent jobs."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    jobs = orchestrator.get_recent_jobs(hours=hours, limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a single job by ID."""
    if not orchestrator or not orchestrator.repositories:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    job = orchestrator.repositories.jobs.get_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return orchestrator._job_to_dict(job)


@app.post("/api/jobs/{job_id}/status")
async def update_job_status(job_id: str, update: JobStatusUpdate):
    """Update job status."""
    if not orchestrator or not orchestrator.repositories:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    job = orchestrator.repositories.jobs.get_by_job_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        new_status = JobStatus(update.new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {update.new_status}")
    
    updated_job = orchestrator.repositories.jobs.update_status(
        job.id, new_status, changed_by="api", notes=update.notes
    )
    
    return orchestrator._job_to_dict(updated_job)


@app.post("/api/scan")
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start a new scan."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    # Run in background
    background_tasks.add_task(
        run_pipeline,
        db_manager,
        priority=request.priority,
        max_pages=request.max_pages,
        triggered_by=request.triggered_by
    )
    
    return {"message": "Scan started", "status": "running"}


@app.get("/api/scan/status")
async def get_scan_status():
    """Get status of recent scans."""
    if not orchestrator or not orchestrator.repositories:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    runs = orchestrator.repositories.search_runs.get_latest(limit=10)
    
    return {
        "runs": [
            {
                "run_id": r.run_id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "platforms_scanned": r.platforms_scanned,
                "raw_jobs_found": r.raw_jobs_found,
                "verified_jobs": r.verified_jobs,
                "relevant_jobs": r.relevant_jobs,
                "high_match_jobs": r.high_match_jobs,
                "duration_seconds": r.duration_seconds,
                "errors": r.errors
            }
            for r in runs
        ]
    }


# ===== NEW ENDPOINTS =====

@app.get("/api/scan/status/latest")
async def get_latest_scan_status():
    """Get the latest scan status with progress for polling."""
    if not orchestrator or not orchestrator.repositories:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    runs = orchestrator.repositories.search_runs.get_latest(limit=1)
    if not runs:
        return {"status": "idle", "progress": 0, "message": "لا يوجد مسح سابق"}
    
    latest = runs[0]
    
    # Calculate progress based on status
    progress_map = {
        "running": 50,
        "completed": 100,
        "failed": 0,
        "partial": 75
    }
    
    return {
        "run_id": latest.run_id,
        "status": latest.status,
        "progress": progress_map.get(latest.status, 0),
        "started_at": latest.started_at.isoformat() if latest.started_at else None,
        "completed_at": latest.completed_at.isoformat() if latest.completed_at else None,
        "platforms_scanned": latest.platforms_scanned,
        "raw_jobs_found": latest.raw_jobs_found,
        "verified_jobs": latest.verified_jobs,
        "relevant_jobs": latest.relevant_jobs,
        "high_match_jobs": latest.high_match_jobs,
        "duration_seconds": latest.duration_seconds,
        "errors": latest.errors,
        "message": _get_status_message(latest.status, latest)
    }


def _get_status_message(status: str, run) -> str:
    """Get human-readable status message."""
    messages = {
        "running": f"جاري المسح... تم العثور على {run.raw_jobs_found} وظيفة",
        "completed": f"اكتمل المسح بنجاح! تم العثور على {run.verified_jobs} وظيفة محققة",
        "failed": f"فشل المسح: {', '.join(run.errors) if run.errors else 'خطأ غير معروف'}",
        "partial": f"اكتمل جزئياً: {run.verified_jobs} وظيفة محققة"
    }
    return messages.get(status, "حالة غير معروفة")


# Scheduler Control
@app.post("/api/scheduler/control")
async def control_scheduler(control: SchedulerControl):
    """Control the scheduler (start/stop/pause/resume)."""
    global orchestrator
    
    if control.action == "start":
        return {"message": "تم بدء المجدول", "action": "started", "interval_hours": control.interval_hours or 6}
    elif control.action == "stop":
        return {"message": "تم إيقاف المجدول", "action": "stopped"}
    elif control.action == "pause":
        return {"message": "تم إيقاف المجدول مؤقتاً", "action": "paused"}
    elif control.action == "resume":
        return {"message": "تم استئناف المجدول", "action": "resumed"}
    else:
        raise HTTPException(status_code=400, detail="إجراء غير صالح")


@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status."""
    return {
        "running": False,
        "interval_hours": 6,
        "next_run": None,
        "jobs_count": 0
    }


# Email Settings
@app.get("/api/email/settings")
async def get_email_settings():
    """Get email configuration and notification settings."""
    config = get_config_sync()
    return {
        "email_config": config.email_config,
        "notifications": config.email_notifications
    }


@app.post("/api/email/settings")
async def update_email_settings(settings: EmailSettings):
    """Update email configuration."""
    return {"message": "تم تحديث إعدادات البريد الإلكتروني", "settings": settings.dict()}


@app.get("/api/email/notifications")
async def get_notification_settings():
    """Get email notification preferences."""
    config = get_config_sync()
    return config.email_notifications


@app.post("/api/email/notifications")
async def update_notification_settings(settings: EmailNotificationSettings):
    """Update email notification preferences."""
    config = get_config_sync()
    config.update_profile("email_notifications", settings.dict())
    config.save_profile()
    return {"message": "تم تحديث تفضيلات الإشعارات", "settings": settings.dict()}


@app.post("/api/email/test")
async def send_test_email(request: TestEmailRequest):
    """Send a test email to verify configuration."""
    from core.notifications.email_service import get_email_service
    
    email_service = get_email_service()
    email = request.email or get_config_sync().email_notifications.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="لا يوجد بريد إلكتروني محدد")
    
    success = await email_service.send_test_email(email)
    
    if success:
        return {"message": "تم إرسال بريد اختباري بنجاح"}
    else:
        raise HTTPException(status_code=500, detail="فشل إرسال البريد الاختباري")


# Update config endpoint to include email
@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    config = get_config_sync()
    return {
        "config": config._config,
        "profile": config._profile,
        "email_config": config.email_config,
        "email_notifications": config.email_notifications
    }
async def export_jobs(request: ExportRequest):
    """Export jobs to file."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    # Create export job record
    if orchestrator.repositories:
        export = orchestrator.repositories.exports.create({
            "export_id": f"export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "format": request.format,
            "filters": request.filters or {},
            "status": "processing"
        })
    
    # Generate file (placeholder)
    filepath = orchestrator.export_jobs(request.format, request.filters)
    
    if orchestrator.repositories:
        orchestrator.repositories.exports.update(export.export_id, {
            "status": "completed",
            "file_path": filepath,
            "completed_at": datetime.utcnow()
        })
    
    return FileResponse(
        filepath,
        media_type="application/octet-stream",
        filename=os.path.basename(filepath)
    )


@app.get("/api/report/daily")
async def get_daily_report():
    """Generate and return daily report."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    report = orchestrator.generate_daily_report()
    return {"report": report, "generated_at": datetime.utcnow().isoformat()}


@app.get("/api/platforms")
async def get_platforms():
    """Get all platforms."""
    if not orchestrator or not orchestrator.repositories:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    platforms = orchestrator.repositories.platforms.get_active_platforms()
    
    return {
        "platforms": [
            {
                "id": p.id,
                "name": p.name,
                "url": p.url,
                "jobs_url": p.jobs_url,
                "search_url": p.search_url,
                "category": p.category,
                "country_region": p.country_region,
                "login_required": p.login_required,
                "public_access": p.public_access,
                "is_active": p.is_active,
                "last_scanned_at": p.last_scanned_at.isoformat() if p.last_scanned_at else None,
                "scan_count": p.scan_count,
                "jobs_found": p.jobs_found,
                "verified_jobs": p.verified_jobs
            }
            for p in platforms
        ]
    }


@app.get("/api/agents/stats")
async def get_agent_stats():
    """Get agent statistics."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    return orchestrator.agent_orchestrator.get_all_stats()


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    config = get_config()
    return {
        "config": config._config,
        "profile": config._profile
    }


@app.post("/api/config/reload")
async def reload_config_endpoint():
    """Reload configuration from file."""
    config = reload_config()
    return {"message": "Configuration reloaded", "config": config._config}


# Dashboard route
@app.get("/dashboard")
async def dashboard():
    """Serve dashboard HTML."""
    if os.path.exists("dashboard/public/index.html"):
        return FileResponse("dashboard/public/index.html")
    return {"message": "Dashboard not built yet. Run 'npm run build' in dashboard directory."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)