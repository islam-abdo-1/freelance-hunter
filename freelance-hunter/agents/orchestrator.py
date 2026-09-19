"""
Orchestrator Agent - Coordinates the entire freelance job hunting pipeline.
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .base import BaseAgent, AgentResult, AgentOrchestrator
from .platform_discovery import PlatformDiscoveryAgent
from .job_search_agents import create_specialized_agents, SearchEngineAgent
from .verification import VerificationAgent, VerificationService
from .deduplication import DeduplicationAgent, DeduplicationService
from .matching import JobMatchingAgent, MatchingService
from .proposal import ProposalAgent, ProposalService
from .risk_detection import RiskDetectionAgent, RiskDetectionService
from core.config.loader import get_config
from core.database.repository import Repositories, DatabaseManager
from core.database.models import SearchRun, JobStatus

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of the complete pipeline run."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    platforms_discovered: int
    platforms_scanned: int
    queries_executed: int
    pages_scanned: int
    raw_jobs_found: int
    duplicates_removed: int
    unverified_jobs: int
    verified_jobs: int
    relevant_jobs: int
    high_match_jobs: int
    errors: List[str]
    duration_seconds: float


class FreelanceHunterOrchestrator:
    """Main orchestrator for the freelance job hunting system."""
    
    def __init__(self, db_manager=None, config: Dict[str, Any] = None):
        self.db_manager = db_manager
        self.config = config or get_config()._config
        self.repositories = Repositories(db_manager) if db_manager else None
        
        # Initialize agents
        self.platform_discovery = PlatformDiscoveryAgent(config=self.config, db_manager=db_manager)
        self.search_agents = create_specialized_agents(config=self.config, db_manager=db_manager)
        self.search_engine_agent = SearchEngineAgent(config=self.config, db_manager=db_manager)
        
        # Services
        self.verification_service = VerificationService(db_manager)
        self.dedup_service = DeduplicationService(db_manager)
        self.matching_service = MatchingService(db_manager)
        self.proposal_service = ProposalService(db_manager)
        self.risk_service = RiskDetectionService(db_manager)
        
        # Agent orchestrator for parallel execution
        self.agent_orchestrator = AgentOrchestrator(config=self.config, db_manager=db_manager)
        self._register_all_agents()
        
        self.logger = logging.getLogger("orchestrator")
    
    def _register_all_agents(self):
        """Register all agents with the orchestrator."""
        self.agent_orchestrator.register_agent(self.platform_discovery)
        for agent in self.search_agents:
            self.agent_orchestrator.register_agent(agent)
        self.agent_orchestrator.register_agent(self.search_engine_agent)
    
    async def run_full_pipeline(self, **kwargs) -> PipelineResult:
        """Run the complete job hunting pipeline."""
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.utcnow()
        errors = []
        
        # Create search run record
        search_run = None
        if self.repositories:
            search_run = self.repositories.search_runs.create({
                "run_id": run_id,
                "started_at": started_at,
                "status": "running",
                "triggered_by": kwargs.get("triggered_by", "manual")
            })
        
        self.logger.info(f"Starting pipeline run {run_id}")
        
        try:
            # Phase 1: Platform Discovery
            self.logger.info("Phase 1: Platform Discovery")
            platform_result = await self._run_platform_discovery()
            platforms = platform_result.data.get("platforms", []) if platform_result.success else []
            
            # Phase 2: Generate Search Queries
            self.logger.info("Phase 2: Generating Search Queries")
            all_queries = self._generate_all_queries()
            
            # Phase 3: Run Search Agents in Parallel
            self.logger.info("Phase 3: Running Search Agents")
            search_results = await self._run_search_agents(platforms, all_queries, **kwargs)
            all_jobs = self._collect_jobs_from_results(search_results)
            
            # Phase 4: Search Engine Queries
            self.logger.info("Phase 4: Search Engine Queries")
            engine_result = await self.search_engine_agent.run()
            # In real implementation, would execute these queries
            
            # Phase 5: Deduplication
            self.logger.info("Phase 5: Deduplication")
            unique_jobs = await self.dedup_service.deduplicate(all_jobs)
            
            # Phase 6: Verification
            self.logger.info("Phase 6: Verification")
            verified_jobs = await self.verification_service.verify_jobs(unique_jobs)
            
            # Phase 7: Job Matching
            self.logger.info("Phase 7: Job Matching")
            matched_jobs = await self.matching_service.match_jobs(verified_jobs)
            
            # Phase 8: Risk Detection
            self.logger.info("Phase 8: Risk Detection")
            risk_assessed_jobs = await self.risk_service.assess_risks(matched_jobs)
            
            # Phase 9: Proposal Generation
            self.logger.info("Phase 9: Proposal Generation")
            final_jobs = await self.proposal_service.generate_proposals(risk_assessed_jobs)
            
            # Save final jobs to database
            if self.repositories:
                await self._save_jobs(final_jobs)
            
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            
            # Calculate stats
            stats = self._calculate_stats(
                platform_result, search_results, unique_jobs, 
                verified_jobs, matched_jobs, risk_assessed_jobs
            )
            
            # Update search run
            if self.repositories and search_run:
                self.repositories.search_runs.update(search_run.run_id, {
                    "completed_at": completed_at,
                    "status": "completed",
                    **stats,
                    "duration_seconds": duration,
                    "errors": errors
                })
            
            self.logger.info(f"Pipeline run {run_id} completed in {duration:.2f}s")
            
            return PipelineResult(
                run_id=run_id,
                started_at=started_at,
                completed_at=completed_at,
                status="completed",
                duration_seconds=duration,
                errors=errors,
                **stats
            )
            
        except Exception as e:
            self.logger.exception(f"Pipeline run {run_id} failed: {e}")
            errors.append(str(e))
            
            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()
            
            if self.repositories and search_run:
                self.repositories.search_runs.update(search_run.run_id, {
                    "completed_at": completed_at,
                    "status": "failed",
                    "duration_seconds": duration,
                    "errors": errors
                })
            
            return PipelineResult(
                run_id=run_id,
                started_at=started_at,
                completed_at=completed_at,
                status="failed",
                duration_seconds=duration,
                errors=errors,
                platforms_discovered=0, platforms_scanned=0, queries_executed=0,
                pages_scanned=0, raw_jobs_found=0, duplicates_removed=0,
                unverified_jobs=0, verified_jobs=0, relevant_jobs=0, high_match_jobs=0
            )
    
    async def _run_platform_discovery(self) -> AgentResult:
        """Run platform discovery agent."""
        return await self.platform_discovery.run(
            max_new_platforms=self.config.get("agents", {}).get("platform_discovery", {}).get("max_new_platforms_per_run", 5)
        )
    
    def _generate_all_queries(self) -> List[str]:
        """Generate all search queries from all agents."""
        all_queries = set()
        
        for agent in self.search_agents:
            if hasattr(agent, 'generate_search_queries'):
                queries = agent.generate_search_queries()
                all_queries.update(queries)
        
        # Add search engine queries
        engine_queries = self.search_engine_agent.generate_search_queries()
        all_queries.update(engine_queries)
        
        return list(all_queries)[:200]  # Limit total queries
    
    async def _run_search_agents(self, platforms: List[Dict], queries: List[str], **kwargs) -> Dict[str, AgentResult]:
        """Run all search agents in parallel."""
        # Filter active platforms with job listings
        active_platforms = [p for p in platforms if p.get("has_job_listings", True)]
        
        if not active_platforms and self.repositories:
            # Fallback to database platforms
            db_platforms = self.repositories.platforms.get_active_platforms()
            active_platforms = [
                {
                    "name": p.name, "url": p.url, "jobs_url": p.jobs_url,
                    "search_url": p.search_url, "has_job_listings": True,
                    "login_required": p.login_required, "public_access": p.public_access
                }
                for p in db_platforms
            ]
        
        # Run agents in parallel
        agent_names = [agent.name for agent in self.search_agents if agent.name != "search_engine_agent"]
        
        # Prepare kwargs for each agent
        agent_kwargs = {
            name: {
                "platforms": active_platforms,
                "queries": queries,
                "priority": kwargs.get("priority", 1),
                "max_pages": kwargs.get("max_pages", 5)
            }
            for name in agent_names
        }
        
        return await self.agent_orchestrator.run_agents_parallel(agent_names, **kwargs.get("agent_kwargs", {}))
    
    def _collect_jobs_from_results(self, results: Dict[str, AgentResult]) -> List[Dict[str, Any]]:
        """Collect jobs from all search agent results."""
        all_jobs = []
        
        for agent_name, result in results.items():
            if result.success and result.data:
                jobs = result.data.get("jobs", [])
                all_jobs.extend(jobs)
                self.logger.info(f"Agent {agent_name} found {len(jobs)} jobs")
            else:
                self.logger.warning(f"Agent {agent_name} failed: {result.error}")
        
        return all_jobs
    
    def _calculate_stats(self, platform_result, search_results, unique_jobs, 
                         verified_jobs, matched_jobs, risk_assessed_jobs) -> Dict[str, int]:
        """Calculate pipeline statistics."""
        platforms_scanned = 0
        queries_executed = 0
        pages_scanned = 0
        raw_jobs_found = 0
        
        for result in search_results.values():
            if result.success and result.data:
                platforms_scanned += result.data.get("platforms_searched", 0)
                queries_executed += result.data.get("queries_used", 0)
                raw_jobs_found += result.items_found
                pages_scanned += sum(
                    j.get("pages_scanned", 0) for j in result.data.get("jobs", [])
                )
        
        duplicates_removed = raw_jobs_found - len(unique_jobs)
        unverified = len([j for j in unique_jobs if j.get("verification_status") != "VERIFIED"])
        verified = len([j for j in unique_jobs if j.get("verification_status") == "VERIFIED"])
        relevant = len([j for j in matched_jobs if j.get("match_level") in ["EXCELLENT_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH"]])
        high_match = len([j for j in matched_jobs if j.get("match_level") in ["EXCELLENT_MATCH", "GOOD_MATCH"]])
        
        return {
            "platforms_discovered": platform_result.data.get("new_platforms_discovered", 0) if platform_result.success else 0,
            "platforms_scanned": platforms_scanned,
            "queries_executed": queries_executed,
            "pages_scanned": pages_scanned,
            "raw_jobs_found": raw_jobs_found,
            "duplicates_removed": duplicates_removed,
            "unverified_jobs": unverified,
            "verified_jobs": verified,
            "relevant_jobs": relevant,
            "high_match_jobs": high_match
        }
    
    async def _save_jobs(self, jobs: List[Dict[str, Any]]):
        """Save final jobs to database."""
        for job_data in jobs:
            try:
                # Check if job already exists
                existing = self.repositories.jobs.get_by_job_id(job_data.get("job_id"))
                
                if existing:
                    # Update existing
                    self.repositories.jobs.update(existing.id, job_data)
                else:
                    # Create new
                    # Convert date strings to datetime
                    for date_field in ["date_posted", "deadline", "discovered_at"]:
                        if job_data.get(date_field) and isinstance(job_data[date_field], str):
                            from core.utils import parse_date
                            job_data[date_field] = parse_date(job_data[date_field])
                    
                    self.repositories.jobs.create(job_data)
            except Exception as e:
                self.logger.error(f"Failed to save job {job_data.get('job_id')}: {e}")
    
    async def run_scheduled_scan(self, interval_hours: int = 6):
        """Run a scheduled scan."""
        self.logger.info(f"Running scheduled scan (interval: {interval_hours}h)")
        return await self.run_full_pipeline(
            triggered_by="scheduled",
            priority=1  # High priority for recent jobs
        )
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics."""
        if not self.repositories:
            return {}
        
        return self.repositories.jobs.get_stats()
    
    def get_recent_jobs(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent jobs for dashboard."""
        if not self.repositories:
            return []
        
        jobs = self.repositories.jobs.get_recent_jobs(hours=hours, limit=limit)
        return [self._job_to_dict(j) for j in jobs]
    
    def _job_to_dict(self, job) -> Dict[str, Any]:
        """Convert Job model to dictionary."""
        return {
            "id": job.id,
            "job_id": job.job_id,
            "platform": job.platform,
            "title": job.title,
            "short_summary": job.short_summary,
            "category": job.category,
            "sub_category": job.sub_category,
            "matched_skills": job.matched_skills,
            "date_posted": job.date_posted.isoformat() if job.date_posted else None,
            "time_since_posted": job.time_since_posted,
            "budget": job.budget,
            "budget_min": job.budget_min,
            "budget_max": job.budget_max,
            "currency": job.currency,
            "fixed_price_or_hourly": job.fixed_price_or_hourly,
            "experience_level": job.experience_level,
            "required_skills": job.required_skills,
            "proposals_count": job.proposals_count,
            "hires_count": job.hires_count,
            "client_name": job.client_name,
            "client_country": job.client_country,
            "client_rating": job.client_rating,
            "client_review_count": job.client_review_count,
            "client_hire_history": job.client_hire_history,
            "client_total_spent": job.client_total_spent,
            "client_payment_status": job.client_payment_status,
            "verification_status": job.verification_status.value if job.verification_status else None,
            "match_level": job.match_level.value if job.match_level else None,
            "match_score": job.score,
            "score_breakdown": job.score_breakdown,
            "match_reason": job.match_reason,
            "risk_level": job.risk_level.value if job.risk_level else None,
            "risk_reasons": job.risk_reasons,
            "proposal_short": job.proposal_short,
            "proposal_normal": job.proposal_normal,
            "proposal_ultra_short": job.proposal_ultra_short,
            "status": job.status.value if job.status else None,
            "job_url": job.job_url,
            "discovered_at": job.discovered_at.isoformat() if job.discovered_at else None
        }
    
    def search_jobs(self, filters: Dict[str, Any], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Search jobs with filters."""
        if not self.repositories:
            return {"jobs": [], "total": 0, "page": page, "per_page": per_page, "total_pages": 0}
        
        return self.repositories.jobs.search_jobs(filters, page, per_page)
    
    def export_jobs(self, format: str = "csv", filters: Dict[str, Any] = None) -> str:
        """Export jobs to file."""
        # This would be implemented with actual export logic
        return f"exports/jobs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    def generate_daily_report(self) -> str:
        """Generate daily report."""
        if not self.repositories:
            return "No database connection"
        
        stats = self.get_dashboard_stats()
        recent_jobs = self.get_recent_jobs(hours=24, limit=20)
        
        high_match = [j for j in recent_jobs if j.get("match_level") in ["EXCELLENT_MATCH", "GOOD_MATCH"]]
        
        report = []
        report.append("=" * 50)
        report.append("FREELANCE JOB HUNTER - DAILY REPORT")
        report.append(f"{datetime.utcnow().strftime('%d %B %Y')}")
        report.append("=" * 50)
        report.append("")
        
        report.append(f"New verified opportunities: {stats.get('verified_jobs', 0)}")
        report.append(f"Highly relevant: {len([j for j in high_match if j.get('match_level') == 'EXCELLENT_MATCH'])}")
        report.append(f"Good matches: {len([j for j in high_match if j.get('match_level') == 'GOOD_MATCH'])}")
        report.append(f"Possible matches: {len([j for j in recent_jobs if j.get('match_level') == 'POSSIBLE_MATCH'])}")
        report.append("")
        
        report.append("TOP OPPORTUNITIES:")
        report.append("-" * 30)
        
        for i, job in enumerate(high_match[:10], 1):
            report.append(f"\n{i}.")
            report.append(f"  Platform: {job.get('platform')}")
            report.append(f"  Title: {job.get('title')}")
            report.append(f"  Posted: {job.get('time_since_posted')}")
            report.append(f"  Budget: {job.get('budget')}")
            report.append(f"  Client: {job.get('client_name')}")
            report.append(f"  Score: {job.get('match_score', 0):.1f}")
            report.append(f"  Why it matches: {job.get('match_reason', 'N/A')[:200]}")
            report.append(f"  Link: {job.get('job_url')}")
            if job.get("proposal_short"):
                report.append(f"  Proposal: {job['proposal_short'][:200]}...")
        
        report.append("")
        report.append("PLATFORM SUMMARY:")
        report.append("-" * 30)
        for platform, count in stats.get("platform_breakdown", {}).items():
            report.append(f"  {platform}: {count}")
        
        report.append("")
        report.append("=" * 50)
        
        return "\n".join(report)


# Convenience function for running pipeline
async def run_pipeline(db_manager=None, config: Dict[str, Any] = None, **kwargs) -> PipelineResult:
    """Run the full pipeline."""
    orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager, config=config)
    return await orchestrator.run_full_pipeline(**kwargs)