"""
Deduplication Agent - Detects and removes duplicate job listings.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from .base import BaseAgent, AgentResult
from core.utils import (
    normalize_url, calculate_similarity, is_duplicate_job,
    generate_job_id
)
from core.config.loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """Group of duplicate jobs."""
    canonical_job: Dict[str, Any]
    duplicates: List[Dict[str, Any]]
    similarity_scores: List[float]
    reasons: List[str]


class DeduplicationAgent(BaseAgent):
    """Agent that detects and handles duplicate job listings."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        super().__init__("deduplication_agent", config, db_manager)
        self.config = config or get_config()._config
        self.dedup_config = self.config.get("deduplication", {})
        self.threshold = self.dedup_config.get("similarity_threshold", 0.85)
        self.check_fields = self.dedup_config.get("check_fields", [
            "url", "title", "client_name", "description", "posted_date", "platform"
        ])
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute deduplication on jobs."""
        jobs = kwargs.get("jobs", [])
        existing_jobs = kwargs.get("existing_jobs", [])
        
        # Combine new jobs with existing for cross-checking
        all_jobs = existing_jobs + jobs
        
        # Find duplicates
        duplicate_groups = self._find_duplicates(all_jobs)
        
        # Select canonical jobs (keep best version)
        canonical_jobs = []
        duplicates_removed = 0
        
        for group in duplicate_groups:
            canonical = self._select_canonical(group)
            canonical_jobs.append(canonical)
            duplicates_removed += len(group.duplicates)
            
            # Record duplicates in database
            if self.db_manager:
                await self._record_duplicates(canonical, group.duplicates)
        
        # Add non-duplicate jobs
        duplicate_ids = set()
        for group in duplicate_groups:
            duplicate_ids.add(group.canonical_job.get("job_id"))
            for dup in group.duplicates:
                duplicate_ids.add(dup.get("job_id"))
        
        for job in all_jobs:
            if job.get("job_id") not in duplicate_ids:
                canonical_jobs.append(job)
        
        return AgentResult(
            success=True,
            data={
                "canonical_jobs": canonical_jobs,
                "duplicate_groups": len(duplicate_groups),
                "duplicates_removed": duplicates_removed,
                "unique_jobs": len(canonical_jobs)
            },
            items_found=len(all_jobs),
            items_processed=len(canonical_jobs),
            metadata={
                "threshold": self.threshold,
                "check_fields": self.check_fields
            }
        )
    
    def _find_duplicates(self, jobs: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """Find duplicate groups among jobs."""
        groups = []
        processed = set()
        
        for i, job1 in enumerate(jobs):
            job1_id = job1.get("job_id")
            if job1_id in processed:
                continue
            
            duplicates = []
            scores = []
            reasons = []
            
            for j, job2 in enumerate(jobs[i+1:], i+1):
                job2_id = job2.get("job_id")
                if job2_id in processed:
                    continue
                
                is_dup, reason, score = is_duplicate_job(job1, job2, self.threshold)
                if is_dup:
                    duplicates.append(job2)
                    scores.append(score)
                    reasons.append(reason)
                    processed.add(job2_id)
            
            if duplicates:
                groups.append(DuplicateGroup(
                    canonical_job=job1,
                    duplicates=duplicates,
                    similarity_scores=scores,
                    reasons=reasons
                ))
                processed.add(job1_id)
        
        return groups
    
    def _select_canonical(self, group: DuplicateGroup) -> Dict[str, Any]:
        """Select the best job from a duplicate group as canonical."""
        candidates = [group.canonical_job] + group.duplicates
        
        # Score each candidate
        scored = []
        for job in candidates:
            score = self._score_job_completeness(job)
            scored.append((score, job))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        canonical = scored[0][1].copy()
        
        # Merge information from duplicates
        for _, dup in scored[1:]:
            canonical = self._merge_job_info(canonical, dup)
        
        # Add metadata about deduplication
        canonical["deduplicated_from"] = len(group.duplicates)
        canonical["duplicate_sources"] = [
            d.get("source_agent", "unknown") for d in group.duplicates
        ]
        canonical["duplicate_platforms"] = list(set(
            [canonical.get("platform")] + [d.get("platform") for d in group.duplicates]
        ))
        
        return canonical
    
    def _score_job_completeness(self, job: Dict[str, Any]) -> float:
        """Score job based on completeness and quality."""
        score = 0.0
        
        # Required fields
        required = ["title", "full_description", "job_url", "platform", "date_posted"]
        for field in required:
            if job.get(field):
                score += 10
        
        # Important fields
        important = ["budget", "client_name", "client_country", "required_skills", "experience_level"]
        for field in important:
            if job.get(field):
                score += 5
        
        # Description length
        desc = job.get("full_description", "")
        if len(desc) > 500:
            score += 5
        elif len(desc) > 200:
            score += 3
        elif len(desc) > 50:
            score += 1
        
        # Has client info
        if job.get("client_rating") is not None:
            score += 3
        if job.get("client_review_count") is not None:
            score += 2
        if job.get("client_hire_history") is not None:
            score += 2
        
        # Has competition info
        if job.get("proposals_count") is not None:
            score += 2
        if job.get("hires_count") is not None:
            score += 2
        
        # Verified status
        if job.get("verification_status") == "VERIFIED":
            score += 10
        elif job.get("verification_status") == "PARTIALLY_VERIFIED":
            score += 5
        
        # Recent discovery
        discovered = job.get("discovered_at")
        if discovered:
            try:
                if isinstance(discovered, str):
                    from core.utils import parse_date
                    discovered = parse_date(discovered)
                if discovered:
                    hours_ago = (datetime.utcnow() - discovered).total_seconds() / 3600
                    if hours_ago < 24:
                        score += 5
                    elif hours_ago < 168:
                        score += 2
            except Exception:
                pass
        
        return score
    
    def _merge_job_info(self, canonical: Dict[str, Any], duplicate: Dict[str, Any]) -> Dict[str, Any]:
        """Merge information from duplicate into canonical."""
        # Fields where we want the most complete information
        merge_fields = [
            "full_description", "short_summary", "budget", "budget_min", "budget_max",
            "currency", "client_name", "client_profile_url", "client_country",
            "client_rating", "client_review_count", "client_hire_history",
            "client_total_spent", "client_payment_status", "required_skills",
            "experience_level", "deadline", "estimated_duration", "attachments",
            "required_files", "required_output", "contact_method", "remote_allowed",
            "location_requirement", "proposals_count", "hires_count", "bids_count"
        ]
        
        for field in merge_fields:
            canon_val = canonical.get(field)
            dup_val = duplicate.get(field)
            
            # If canonical is empty but duplicate has value
            if not canon_val and dup_val:
                canonical[field] = dup_val
            # If both have values, prefer longer/more complete
            elif canon_val and dup_val:
                if isinstance(canon_val, str) and isinstance(dup_val, str):
                    if len(dup_val) > len(canon_val):
                        canonical[field] = dup_val
                elif isinstance(canon_val, list) and isinstance(dup_val, list):
                    # Merge lists
                    merged = list(set(canon_val + dup_val))
                    canonical[field] = merged
        
        # Merge matched skills
        canon_skills = set(canonical.get("matched_skills", []))
        dup_skills = set(duplicate.get("matched_skills", []))
        canonical["matched_skills"] = list(canon_skills | dup_skills)
        
        # Keep earliest discovery date
        canon_disc = canonical.get("discovered_at")
        dup_disc = duplicate.get("discovered_at")
        if canon_disc and dup_disc:
            try:
                from core.utils import parse_date
                if isinstance(canon_disc, str):
                    canon_disc = parse_date(canon_disc)
                if isinstance(dup_disc, str):
                    dup_disc = parse_date(dup_disc)
                if dup_disc and dup_disc < canon_disc:
                    canonical["discovered_at"] = dup_disc.isoformat() if hasattr(dup_disc, 'isoformat') else str(dup_disc)
            except Exception:
                pass
        
        return canonical
    
    async def _record_duplicates(self, canonical: Dict[str, Any], duplicates: List[Dict[str, Any]]):
        """Record duplicate relationships in database."""
        if not self.db_manager:
            return
        
        canonical_job = self.db_manager.repositories.jobs.get_by_job_id(canonical.get("job_id"))
        if not canonical_job:
            return
        
        for dup in duplicates:
            dup_job = self.db_manager.repositories.jobs.get_by_job_id(dup.get("job_id"))
            if not dup_job:
                continue
            
            # Calculate similarity
            _, reason, score = is_duplicate_job(canonical, dup, self.threshold)
            
            # Record in database
            from core.database.models import JobDuplicate
            
            try:
                with self.db_manager.session() as session:
                    duplicate_record = JobDuplicate(
                        job_id=canonical_job.id,
                        duplicate_of_id=dup_job.id,
                        similarity_score=score,
                        duplicate_reason=reason,
                        detected_at=datetime.utcnow()
                    )
                    session.add(duplicate_record)
            except Exception as e:
                logger.error(f"Failed to record duplicate: {e}")


class DeduplicationService:
    """Service for running deduplication."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.agent = DeduplicationAgent(db_manager=db_manager)
    
    async def deduplicate(self, jobs: List[Dict[str, Any]], 
                          existing_jobs: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Deduplicate jobs against each other and existing jobs."""
        existing = existing_jobs or []
        
        # If we have database, fetch recent jobs for cross-checking
        if self.db_manager and not existing:
            recent = self.db_manager.repositories.jobs.get_recent_jobs(hours=720, limit=1000)
            existing = [self._job_to_dict(j) for j in recent]
        
        result = await self.agent.run(jobs=jobs, existing_jobs=existing)
        
        if result.success:
            return result.data["canonical_jobs"]
        return jobs
    
    def _job_to_dict(self, job) -> Dict[str, Any]:
        """Convert Job model to dictionary."""
        return {
            "job_id": job.job_id,
            "id": job.id,
            "platform": job.platform,
            "platform_url": job.platform_url,
            "job_url": job.job_url,
            "canonical_url": job.canonical_url,
            "title": job.title,
            "full_description": job.full_description,
            "short_summary": job.short_summary,
            "category": job.category,
            "sub_category": job.sub_category,
            "matched_skills": job.matched_skills,
            "date_posted": job.date_posted.isoformat() if job.date_posted else None,
            "time_since_posted": job.time_since_posted,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "estimated_duration": job.estimated_duration,
            "budget": job.budget,
            "budget_min": job.budget_min,
            "budget_max": job.budget_max,
            "currency": job.currency,
            "fixed_price_or_hourly": job.fixed_price_or_hourly,
            "experience_level": job.experience_level,
            "required_skills": job.required_skills,
            "proposals_count": job.proposals_count,
            "hires_count": job.hires_count,
            "bids_count": job.bids_count,
            "client_name": job.client_name,
            "client_profile_url": job.client_profile_url,
            "client_country": job.client_country,
            "client_rating": job.client_rating,
            "client_review_count": job.client_review_count,
            "client_hire_history": job.client_hire_history,
            "client_total_spent": job.client_total_spent,
            "client_payment_status": job.client_payment_status,
            "attachments": job.attachments,
            "required_files": job.required_files,
            "required_output": job.required_output,
            "contact_method": job.contact_method,
            "remote_allowed": job.remote_allowed,
            "location_requirement": job.location_requirement,
            "login_required": job.login_required,
            "verification_status": job.verification_status.value if job.verification_status else None,
            "match_level": job.match_level.value if job.match_level else None,
            "potential_difficulty": job.potential_difficulty,
            "estimated_effort": job.estimated_effort,
            "source_agent": job.source_agent,
            "discovered_at": job.discovered_at.isoformat() if job.discovered_at else None
        }