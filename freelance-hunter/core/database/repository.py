"""
Database manager and repository classes for Freelance Hunter.
"""
import logging
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from .models import (
    Agent,
    Base,
    Client,
    ExportJob,
    Job,
    JobMatch,
    JobStatus,
    JobStatusHistory,
    MatchLevel,
    Platform,
    Proposal,
    RedFlag,
    RiskLevel,
    SearchRun,
    VerificationStatus,
    get_engine,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url
        self.engine = get_engine(database_url)
        self.SessionFactory = None
    
    def initialize(self):
        """Initialize database and create tables."""
        Base.metadata.create_all(self.engine)
        from sqlalchemy.orm import sessionmaker
        self.SessionFactory = sessionmaker(bind=self.engine)
        logger.info("Database initialized successfully")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        if self.SessionFactory is None:
            self.initialize()
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()


class PlatformRepository:
    """Repository for platform operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_or_update(self, platform_data: dict[str, Any]) -> Platform:
        """Create or update a platform."""
        with self.db.session() as session:
            platform = session.query(Platform).filter_by(name=platform_data['name']).first()
            if platform:
                for key, value in platform_data.items():
                    if hasattr(platform, key) and key != 'id':
                        setattr(platform, key, value)
                platform.updated_at = datetime.utcnow()
            else:
                platform = Platform(**platform_data)
                session.add(platform)
            session.flush()
            # Return a copy of the data we need
            platform_id = platform.id
            platform_name = platform.name
            # Expunge to avoid detached instance issues
            session.expunge(platform)
            # Return a simple object with the data
            return type('PlatformRef', (), {'id': platform_id, 'name': platform_name})()
    
    def get_by_name(self, name: str) -> Platform | None:
        with self.db.session() as session:
            platform = session.query(Platform).filter_by(name=name).first()
            if platform:
                session.expunge(platform)
            return platform
    
    def get_active_platforms(self) -> list[Platform]:
        with self.db.session() as session:
            platforms = session.query(Platform).filter_by(is_active=True).all()
            for p in platforms:
                session.expunge(p)
            return platforms
    
    def update_scan_stats(self, platform_id: int, jobs_found: int, verified: int):
        with self.db.session() as session:
            platform = session.query(Platform).get(platform_id)
            if platform:
                platform.last_scanned_at = datetime.utcnow()
                platform.scan_count += 1
                platform.jobs_found += jobs_found
                platform.verified_jobs += verified


class ClientRepository:
    """Repository for client operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_or_update(self, client_data: dict[str, Any]) -> Client:
        with self.db.session() as session:
            platform_id = client_data['platform_id']
            platform_client_id = client_data.get('platform_client_id')
            
            client = None
            if platform_client_id:
                client = session.query(Client).filter_by(
                    platform_id=platform_id,
                    platform_client_id=platform_client_id
                ).first()
            
            if client:
                for key, value in client_data.items():
                    if hasattr(client, key) and key not in ['id', 'platform_id', 'platform_client_id']:
                        setattr(client, key, value)
                client.updated_at = datetime.utcnow()
            else:
                client = Client(**client_data)
                session.add(client)
            session.flush()
            client_id = client.id
            client_name = client.display_name
            session.expunge(client)
            return type('ClientRef', (), {'id': client_id, 'display_name': client_name})()
    
    def get_by_platform_and_id(self, platform_id: int, platform_client_id: str) -> Client | None:
        with self.db.session() as session:
            client = session.query(Client).filter_by(
                platform_id=platform_id,
                platform_client_id=platform_client_id
            ).first()
            if client:
                session.expunge(client)
            return client


class JobRepository:
    """Repository for job operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, job_data: dict[str, Any]) -> Job:
        with self.db.session() as session:
            job = Job(**job_data)
            session.add(job)
            session.flush()
            job_id = job.id
            job_job_id = job.job_id
            session.expunge(job)
            return type('JobRef', (), {'id': job_id, 'job_id': job_job_id})()
    
    def get_by_id(self, job_id: int) -> Job | None:
        with self.db.session() as session:
            job = session.query(Job).get(job_id)
            if job:
                session.expunge(job)
            return job
    
    def get_by_job_id(self, job_id: str) -> Job | None:
        with self.db.session() as session:
            job = session.query(Job).filter_by(job_id=job_id).first()
            if job:
                session.expunge(job)
            return job
    
    def get_by_url(self, job_url: str) -> Job | None:
        with self.db.session() as session:
            job = session.query(Job).filter_by(job_url=job_url).first()
            if job:
                session.expunge(job)
            return job
    
    def get_by_canonical_url(self, canonical_url: str) -> Job | None:
        with self.db.session() as session:
            job = session.query(Job).filter_by(canonical_url=canonical_url).first()
            if job:
                session.expunge(job)
            return job
    
    def update(self, job_id: int, updates: dict[str, Any]) -> Job | None:
        with self.db.session() as session:
            job = session.query(Job).get(job_id)
            if job:
                for key, value in updates.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
                session.flush()
                session.expunge(job)
            return job
    
    def update_status(self, job_id: int, new_status: JobStatus, changed_by: str = "system", notes: str | None = None):
        with self.db.session() as session:
            job = session.query(Job).get(job_id)
            if job:
                old_status = job.status
                job.status = new_status
                if new_status == JobStatus.APPLIED:
                    job.applied_at = datetime.utcnow()
                
                history = JobStatusHistory(
                    job_id=job_id,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=changed_by,
                    notes=notes
                )
                session.add(history)
                session.flush()
            return job
    
    def search_jobs(self, filters: dict[str, Any], page: int = 1, per_page: int = 20) -> dict[str, Any]:
        with self.db.session() as session:
            query = session.query(Job)
            
            # Apply filters
            if filters.get('platform_id'):
                query = query.filter(Job.platform_id == filters['platform_id'])
            if filters.get('category'):
                query = query.filter(Job.category == filters['category'])
            if filters.get('match_level'):
                query = query.filter(Job.match_level == filters['match_level'])
            if filters.get('verification_status'):
                query = query.filter(Job.verification_status == filters['verification_status'])
            if filters.get('risk_level'):
                query = query.filter(Job.risk_level == filters['risk_level'])
            if filters.get('status'):
                query = query.filter(Job.status == filters['status'])
            if filters.get('min_score'):
                query = query.filter(Job.score >= filters['min_score'])
            if filters.get('max_score'):
                query = query.filter(Job.score <= filters['max_score'])
            if filters.get('date_from'):
                query = query.filter(Job.date_posted >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(Job.date_posted <= filters['date_to'])
            if filters.get('min_budget'):
                query = query.filter(Job.budget_min >= filters['min_budget'])
            if filters.get('max_budget'):
                query = query.filter(Job.budget_max <= filters['max_budget'])
            if filters.get('currency'):
                query = query.filter(Job.currency == filters['currency'])
            if filters.get('experience_level'):
                query = query.filter(Job.experience_level == filters['experience_level'])
            if filters.get('keyword'):
                keyword = f"%{filters['keyword']}%"
                query = query.filter(or_(
                    Job.title.ilike(keyword),
                    Job.full_description.ilike(keyword),
                    Job.short_summary.ilike(keyword)
                ))
            
            # Count total
            total = query.count()
            
            # Apply sorting
            sort_by = filters.get('sort_by', 'score')
            sort_order = filters.get('sort_order', 'desc')
            
            if sort_by == 'score':
                query = query.order_by(desc(Job.score) if sort_order == 'desc' else asc(Job.score))
            elif sort_by == 'date_posted':
                query = query.order_by(desc(Job.date_posted) if sort_order == 'desc' else asc(Job.date_posted))
            elif sort_by == 'discovered_at':
                query = query.order_by(desc(Job.discovered_at) if sort_order == 'desc' else asc(Job.discovered_at))
            
            # Paginate
            offset = (page - 1) * per_page
            jobs = query.offset(offset).limit(per_page).all()
            
            # Expunge all
            for job in jobs:
                session.expunge(job)
            
            return {
                'jobs': jobs,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': (total + per_page - 1) // per_page
            }
    
    def get_stats(self) -> dict[str, Any]:
        with self.db.session() as session:
            total = session.query(func.count(Job.id)).scalar()
            verified = session.query(func.count(Job.id)).filter(
                Job.verification_status == VerificationStatus.VERIFIED
            ).scalar()
            new_today = session.query(func.count(Job.id)).filter(
                Job.discovered_at >= datetime.utcnow().date()
            ).scalar()
            high_match = session.query(func.count(Job.id)).filter(
                Job.match_level.in_([MatchLevel.EXCELLENT_MATCH, MatchLevel.GOOD_MATCH])
            ).scalar()
            high_risk = session.query(func.count(Job.id)).filter(
                Job.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
            ).scalar()
            
            # Platform breakdown
            platform_stats = session.query(
                Platform.name,
                func.count(Job.id).label('count')
            ).join(Job).group_by(Platform.name).all()
            
            return {
                'total_jobs': total,
                'verified_jobs': verified,
                'new_today': new_today,
                'high_match_jobs': high_match,
                'high_risk_jobs': high_risk,
                'platform_breakdown': {name: count for name, count in platform_stats}
            }
    
    def get_recent_jobs(self, hours: int = 24, limit: int = 50) -> list[Job]:
        with self.db.session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            jobs = session.query(Job).filter(
                Job.discovered_at >= cutoff
            ).order_by(desc(Job.score)).limit(limit).all()
            
            for job in jobs:
                session.expunge(job)
            
            return jobs


class SearchRunRepository:
    """Repository for search run tracking."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, run_data: dict[str, Any]) -> SearchRun:
        with self.db.session() as session:
            run = SearchRun(**run_data)
            session.add(run)
            session.flush()
            run_id = run.run_id
            session.expunge(run)
            return type('SearchRunRef', (), {'run_id': run_id})()
    
    def update(self, run_id: str, updates: dict[str, Any]) -> SearchRun | None:
        with self.db.session() as session:
            run = session.query(SearchRun).filter_by(run_id=run_id).first()
            if run:
                for key, value in updates.items():
                    if hasattr(run, key):
                        setattr(run, key, value)
                session.flush()
            return run
    
    def get_latest(self, limit: int = 10) -> list[SearchRun]:
        with self.db.session() as session:
            runs = session.query(SearchRun).order_by(desc(SearchRun.started_at)).limit(limit).all()
            for r in runs:
                session.expunge(r)
            return runs


class AgentRepository:
    """Repository for agent tracking."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_or_update(self, agent_data: dict[str, Any]) -> Agent:
        with self.db.session() as session:
            agent = session.query(Agent).filter_by(name=agent_data['name']).first()
            if agent:
                for key, value in agent_data.items():
                    if hasattr(agent, key) and key != 'id':
                        setattr(agent, key, value)
                agent.updated_at = datetime.utcnow()
            else:
                agent = Agent(**agent_data)
                session.add(agent)
            session.flush()
            agent_id = agent.id
            agent_name = agent.name
            session.expunge(agent)
            return type('AgentRef', (), {'id': agent_id, 'name': agent_name})()
    
    def get_active_agents(self) -> list[Agent]:
        with self.db.session() as session:
            agents = session.query(Agent).filter_by(is_active=True).all()
            for a in agents:
                session.expunge(a)
            return agents


class ProposalRepository:
    """Repository for proposal operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, proposal_data: dict[str, Any]) -> Proposal:
        with self.db.session() as session:
            proposal = Proposal(**proposal_data)
            session.add(proposal)
            session.flush()
            proposal_id = proposal.id
            session.expunge(proposal)
            return type('ProposalRef', (), {'id': proposal_id})()
    
    def get_by_job(self, job_id: int) -> list[Proposal]:
        with self.db.session() as session:
            proposals = session.query(Proposal).filter_by(job_id=job_id).all()
            for p in proposals:
                session.expunge(p)
            return proposals


class RedFlagRepository:
    """Repository for red flag operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, flag_data: dict[str, Any]) -> RedFlag:
        with self.db.session() as session:
            flag = RedFlag(**flag_data)
            session.add(flag)
            session.flush()
            flag_id = flag.id
            session.expunge(flag)
            return type('RedFlagRef', (), {'id': flag_id})()
    
    def get_by_job(self, job_id: int) -> list[RedFlag]:
        with self.db.session() as session:
            flags = session.query(RedFlag).filter_by(job_id=job_id).all()
            for f in flags:
                session.expunge(f)
            return flags


class JobMatchRepository:
    """Repository for job match operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create_matches(self, job_id: int, matches: list[dict[str, Any]]):
        with self.db.session() as session:
            for match in matches:
                match['job_id'] = job_id
                job_match = JobMatch(**match)
                session.add(job_match)
    
    def get_by_job(self, job_id: int) -> list[JobMatch]:
        with self.db.session() as session:
            matches = session.query(JobMatch).filter_by(job_id=job_id).all()
            for m in matches:
                session.expunge(m)
            return matches


class ExportJobRepository:
    """Repository for export job tracking."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, export_data: dict[str, Any]) -> ExportJob:
        with self.db.session() as session:
            export = ExportJob(**export_data)
            session.add(export)
            session.flush()
            export_id = export.export_id
            session.expunge(export)
            return type('ExportJobRef', (), {'export_id': export_id})()
    
    def update(self, export_id: str, updates: dict[str, Any]) -> ExportJob | None:
        with self.db.session() as session:
            export = session.query(ExportJob).filter_by(export_id=export_id).first()
            if export:
                for key, value in updates.items():
                    if hasattr(export, key):
                        setattr(export, key, value)
                session.flush()
            return export


# Initialize all repositories
class Repositories:
    """Container for all repositories."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.platforms = PlatformRepository(db_manager)
        self.clients = ClientRepository(db_manager)
        self.jobs = JobRepository(db_manager)
        self.search_runs = SearchRunRepository(db_manager)
        self.agents = AgentRepository(db_manager)
        self.proposals = ProposalRepository(db_manager)
        self.red_flags = RedFlagRepository(db_manager)
        self.job_matches = JobMatchRepository(db_manager)
        self.exports = ExportJobRepository(db_manager)