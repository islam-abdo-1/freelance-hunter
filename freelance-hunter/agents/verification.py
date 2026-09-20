"""
Verification Agent - Verifies job listings for authenticity and completeness.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from core.config.loader import get_config
from core.utils import extract_budget, is_likely_spam, parse_date, validate_job_url

from .base import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of job verification."""
    job_id: str
    is_verified: bool
    verification_status: str  # VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, FAILED
    checks_passed: list[str]
    checks_failed: list[str]
    missing_fields: list[str]
    warnings: list[str]
    verified_at: datetime
    verified_fields: dict[str, Any]


class VerificationAgent(BaseAgent):
    """Agent that verifies job listings."""
    
    def __init__(self, config: dict[str, Any] | None = None, db_manager=None):
        super().__init__("verification_agent", config, db_manager)
        self.config = config or get_config()._config
        self.verification_config = self.config.get("verification", {})
        self.min_fields = self.verification_config.get("require_minimum_fields", 5)
        
        # Required fields for verification
        self.required_fields = [
            "title", "full_description", "job_url", "platform",
            "date_posted", "budget", "client_name"
        ]
        
        # Optional but important fields
        self.important_fields = [
            "experience_level", "required_skills", "client_rating",
            "client_country", "deadline", "estimated_duration"
        ]
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute verification on jobs."""
        jobs = kwargs.get("jobs", [])
        force_reverify = kwargs.get("force_reverify", False)
        
        results = []
        verified_count = 0
        partially_verified = 0
        unverified_count = 0
        failed_count = 0
        
        for job in jobs:
            # Skip already verified unless forced
            if not force_reverify and job.get("verification_status") == "VERIFIED":
                results.append(self._create_skipped_result(job))
                verified_count += 1
                continue
            
            result = await self._verify_job(job)
            results.append(result)
            
            if result.verification_status == "VERIFIED":
                verified_count += 1
            elif result.verification_status == "PARTIALLY_VERIFIED":
                partially_verified += 1
            elif result.verification_status == "UNVERIFIED":
                unverified_count += 1
            else:
                failed_count += 1
        
        return AgentResult(
            success=True,
            data={
                "results": [self._result_to_dict(r) for r in results],
                "summary": {
                    "verified": verified_count,
                    "partially_verified": partially_verified,
                    "unverified": unverified_count,
                    "failed": failed_count,
                    "total": len(jobs)
                }
            },
            items_found=len(jobs),
            items_processed=verified_count + partially_verified
        )
    
    async def _verify_job(self, job: dict[str, Any]) -> VerificationResult:
        """Verify a single job listing."""
        job_id = job.get("job_id") or job.get("id", "unknown")
        checks_passed = []
        checks_failed = []
        missing_fields = []
        warnings = []
        verified_fields = {}
        
        # 1. Check required fields
        for field in self.required_fields:
            value = job.get(field)
            if value and str(value).strip():
                checks_passed.append(f"field_{field}")
                verified_fields[field] = value
            else:
                checks_failed.append(f"field_{field}")
                missing_fields.append(field)
        
        # 2. Check important fields
        for field in self.important_fields:
            value = job.get(field)
            if value and str(value).strip():
                checks_passed.append(f"field_{field}")
                verified_fields[field] = value
            else:
                warnings.append(f"missing_important_field_{field}")
        
        # 3. Validate URL
        job_url = job.get("job_url", "")
        if job_url:
            if validate_job_url(job_url, job.get("platform", "")):
                checks_passed.append("url_valid")
                verified_fields["job_url"] = job_url
            else:
                checks_failed.append("url_invalid")
                warnings.append("job_url_does_not_match_platform")
        else:
            checks_failed.append("url_missing")
            missing_fields.append("job_url")
        
        # 4. Check if listing exists (would make HTTP request in real implementation)
        url_accessible = await self._check_url_accessible(job_url)
        if url_accessible:
            checks_passed.append("url_accessible")
        else:
            checks_failed.append("url_not_accessible")
            warnings.append("could_not_verify_url_accessibility")
        
        # 5. Check if job is expired/closed
        is_expired = self._check_if_expired(job)
        if is_expired:
            checks_failed.append("job_expired")
            warnings.append("job_appears_expired_or_closed")
        else:
            checks_passed.append("job_not_expired")
        
        # 6. Check if it's a real job (not freelancer profile)
        is_real_job = self._check_is_real_job(job)
        if is_real_job:
            checks_passed.append("is_real_job")
        else:
            checks_failed.append("not_real_job")
            warnings.append("may_be_freelancer_profile_not_job")
        
        # 7. Check for spam
        is_spam, spam_reasons = is_likely_spam(
            job.get("title", ""),
            job.get("full_description", ""),
            {
                "rating": job.get("client_rating"),
                "review_count": job.get("client_review_count"),
                "total_spent": job.get("client_total_spent")
            }
        )
        if is_spam:
            checks_failed.append("spam_detected")
            warnings.extend([f"spam_{r}" for r in spam_reasons])
        else:
            checks_passed.append("not_spam")
        
        # 8. Validate date
        date_posted = job.get("date_posted")
        if date_posted:
            try:
                if isinstance(date_posted, str):
                    parsed_date = parse_date(date_posted)
                    if parsed_date:
                        checks_passed.append("date_valid")
                        verified_fields["date_posted"] = parsed_date.isoformat()
                    else:
                        checks_failed.append("date_invalid")
                else:
                    checks_passed.append("date_valid")
            except Exception:
                checks_failed.append("date_parse_error")
        else:
            checks_failed.append("date_missing")
            missing_fields.append("date_posted")
        
        # 9. Validate budget
        budget = job.get("budget")
        if budget:
            budget_info = extract_budget(str(budget))
            if budget_info.get("budget_min") is not None:
                checks_passed.append("budget_valid")
                verified_fields["budget_min"] = budget_info["budget_min"]
                verified_fields["budget_max"] = budget_info["budget_max"]
                verified_fields["currency"] = budget_info["currency"]
            else:
                warnings.append("budget_format_unclear")
        else:
            warnings.append("budget_not_specified")
        
        # 10. Check platform validity
        platform = job.get("platform", "")
        if platform:
            checks_passed.append("platform_specified")
        else:
            checks_failed.append("platform_missing")
            missing_fields.append("platform")
        
        # Determine overall verification status
        required_passed = sum(1 for c in checks_passed if c.startswith("field_") and c.split("_")[1] in self.required_fields)
        required_total = len(self.required_fields)
        
        if required_passed == required_total and len(checks_failed) == 0:
            verification_status = "VERIFIED"
        elif required_passed >= self.min_fields and "job_expired" not in checks_failed and "not_real_job" not in checks_failed:
            verification_status = "PARTIALLY_VERIFIED"
        elif "not_real_job" in checks_failed or "spam_detected" in checks_failed:
            verification_status = "FAILED"
        else:
            verification_status = "UNVERIFIED"
        
        return VerificationResult(
            job_id=job_id,
            is_verified=verification_status == "VERIFIED",
            verification_status=verification_status,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            missing_fields=missing_fields,
            warnings=warnings,
            verified_at=datetime.utcnow(),
            verified_fields=verified_fields
        )
    
    async def _check_url_accessible(self, url: str) -> bool:
        """Check if URL is accessible (placeholder for real implementation)."""
        # In real implementation, would make HTTP HEAD request
        # For now, return True for known platforms
        if not url:
            return False
        
        domain = urlparse(url).netloc.lower()
        known_domains = [
            "upwork.com", "freelancer.com", "peopleperhour.com",
            "guru.com", "workana.com", "contra.com", "fiverr.com",
            "khamsat.com", "mostaql.com", "linkedin.com"
        ]
        
        return any(d in domain for d in known_domains)
    
    def _check_if_expired(self, job: dict[str, Any]) -> bool:
        """Check if job appears to be expired or closed."""
        # Check explicit status
        status = job.get("status", "").lower()
        if any(s in status for s in ["closed", "expired", "filled", "completed", "cancelled"]):
            return True
        
        # Check deadline
        deadline = job.get("deadline")
        if deadline:
            try:
                if isinstance(deadline, str):
                    deadline_dt = parse_date(deadline)
                else:
                    deadline_dt = deadline
                
                if deadline_dt and deadline_dt < datetime.utcnow():
                    return True
            except Exception:
                pass
        
        # Check for expired keywords in description
        description = job.get("full_description", "").lower()
        expired_keywords = [
            "this job is closed", "position filled", "no longer accepting",
            "hiring complete", "job expired", "application closed"
        ]
        return bool(any(kw in description for kw in expired_keywords))
    
    def _check_is_real_job(self, job: dict[str, Any]) -> bool:
        """Check if listing is a real job posting (not freelancer profile)."""
        title = job.get("title", "").lower()
        description = job.get("full_description", "").lower()
        url = job.get("job_url", "").lower()
        
        # Profile indicators
        profile_indicators = [
            "profile", "portfolio", "freelancer", "my services",
            "i offer", "i provide", "hire me", "my skills",
            "about me", "my experience", "my work"
        ]
        
        # Job indicators
        job_indicators = [
            "looking for", "need", "seeking", "wanted", "required",
            "job description", "requirements", "responsibilities",
            "we need", "our company", "project details", "deliverables"
        ]
        
        profile_score = sum(1 for ind in profile_indicators if ind in title or ind in description)
        job_score = sum(1 for ind in job_indicators if ind in description)
        
        # URL checks
        if any(p in url for p in ["/profile/", "/freelancer/", "/portfolio/"]):
            profile_score += 2
        
        if any(p in url for p in ["/jobs/", "/projects/", "/job/", "/project/"]):
            job_score += 2
        
        return job_score > profile_score
    
    def _create_skipped_result(self, job: dict[str, Any]) -> VerificationResult:
        """Create result for skipped (already verified) job."""
        return VerificationResult(
            job_id=job.get("job_id", "unknown"),
            is_verified=True,
            verification_status="VERIFIED",
            checks_passed=["already_verified"],
            checks_failed=[],
            missing_fields=[],
            warnings=[],
            verified_at=datetime.utcnow(),
            verified_fields={}
        )
    
    def _result_to_dict(self, result: VerificationResult) -> dict[str, Any]:
        """Convert VerificationResult to dictionary."""
        return {
            "job_id": result.job_id,
            "is_verified": result.is_verified,
            "verification_status": result.verification_status,
            "checks_passed": result.checks_passed,
            "checks_failed": result.checks_failed,
            "missing_fields": result.missing_fields,
            "warnings": result.warnings,
            "verified_at": result.verified_at.isoformat(),
            "verified_fields": result.verified_fields
        }


class VerificationService:
    """Service for running verification on jobs."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.agent = VerificationAgent(db_manager=db_manager)
    
    async def verify_jobs(self, jobs: list[dict[str, Any]], force: bool = False) -> list[dict[str, Any]]:
        """Verify a list of jobs and update database."""
        result = await self.agent.run(jobs=jobs, force_reverify=force)
        
        if self.db_manager and result.success:
            # Update jobs in database
            for verification in result.data["results"]:
                job_id = verification["job_id"]
                job = self.db_manager.repositories.jobs.get_by_job_id(job_id)
                if job:
                    self.db_manager.repositories.jobs.update(job.id, {
                        "verification_status": verification["verification_status"],
                        "verified_at": verification["verified_at"]
                    })
        
        return result.data["results"]