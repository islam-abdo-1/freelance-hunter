"""
Database models for Freelance Hunter system.
Supports both SQLite and PostgreSQL.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MatchLevel(str, Enum):
    EXCELLENT_MATCH = "EXCELLENT_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    NOT_RELEVANT = "NOT_RELEVANT"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    FAILED = "FAILED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class JobStatus(str, Enum):
    NEW = "NEW"
    VIEWED = "VIEWED"
    APPLIED = "APPLIED"
    SAVED = "SAVED"
    IGNORED = "IGNORED"
    CLOSED = "CLOSED"
    EXPIRED = "EXPIRED"


class Platform(Base):
    __tablename__ = "platforms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    url = Column(String(500), nullable=False)
    jobs_url = Column(String(500))
    search_url = Column(String(500))
    category = Column(String(100))
    country_region = Column(String(100))
    login_required = Column(Boolean, default=False)
    public_access = Column(Boolean, default=True)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_scanned_at = Column(DateTime)
    scan_count = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    verified_jobs = Column(Integer, default=0)
    
    jobs = relationship("Job", back_populates="platform_obj")
    
    __table_args__ = (
        Index('ix_platforms_name_active', 'name', 'is_active'),
    )


class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False, index=True)
    platform_client_id = Column(String(200), index=True)
    display_name = Column(String(300))
    company_name = Column(String(300))
    profile_url = Column(String(500))
    country = Column(String(100))
    timezone = Column(String(100))
    rating = Column(Float)
    review_count = Column(Integer)
    hire_history = Column(Integer)
    total_spent = Column(Float)
    currency = Column(String(10))
    payment_verified = Column(Boolean)
    account_age_days = Column(Integer)
    hiring_frequency = Column(Float)
    is_verified = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    platform = relationship("Platform")
    jobs = relationship("Job", back_populates="client")
    
    __table_args__ = (
        UniqueConstraint('platform_id', 'platform_client_id', name='uq_platform_client'),
        Index('ix_clients_platform_country', 'platform_id', 'country'),
    )


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    
    platform_url = Column(String(500), nullable=False)
    job_url = Column(String(1000), nullable=False, index=True)
    canonical_url = Column(String(1000))
    source_url = Column(String(1000))
    
    title = Column(String(500), nullable=False)
    full_description = Column(Text)
    short_summary = Column(Text)
    
    category = Column(String(100), index=True)
    sub_category = Column(String(100))
    matched_skills = Column(JSON)
    
    date_posted = Column(DateTime, index=True)
    time_since_posted = Column(String(50))
    deadline = Column(DateTime)
    estimated_duration = Column(String(100))
    discovered_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    budget = Column(String(100))
    budget_min = Column(Float)
    budget_max = Column(Float)
    currency = Column(String(10), default="USD")
    fixed_price_or_hourly = Column(String(20))
    
    experience_level = Column(String(50))
    required_skills = Column(JSON)
    
    proposals_count = Column(Integer)
    hires_count = Column(Integer)
    bids_count = Column(Integer)
    
    client_name = Column(String(300))
    client_country = Column(String(100))
    client_rating = Column(Float)
    client_review_count = Column(Integer)
    client_hire_history = Column(Integer)
    client_total_spent = Column(Float)
    client_payment_status = Column(String(50))
    
    attachments = Column(JSON)
    required_files = Column(JSON)
    required_output = Column(JSON)
    contact_method = Column(String(200))
    remote_allowed = Column(Boolean, default=True)
    location_requirement = Column(String(200))
    login_required = Column(Boolean, default=False)
    
    verification_status = Column(SQLEnum(VerificationStatus), default=VerificationStatus.UNVERIFIED, index=True)
    match_level = Column(SQLEnum(MatchLevel), default=MatchLevel.NOT_RELEVANT, index=True)
    match_reason = Column(Text)
    potential_difficulty = Column(String(50))
    estimated_effort = Column(String(50))
    recommended_application_style = Column(String(50))
    
    proposal_short = Column(Text)
    proposal_normal = Column(Text)
    proposal_ultra_short = Column(Text)
    
    score = Column(Float, default=0.0, index=True)
    score_breakdown = Column(JSON)
    
    risk_level = Column(SQLEnum(RiskLevel), default=RiskLevel.LOW, index=True)
    risk_reasons = Column(JSON)
    
    status = Column(SQLEnum(JobStatus), default=JobStatus.NEW, index=True)
    applied_at = Column(DateTime)
    notes = Column(Text)
    
    source_agent = Column(String(100))
    pages_scanned = Column(Integer)
    results_scanned = Column(Integer)
    
    platform_obj = relationship("Platform", back_populates="jobs")
    client = relationship("Client", back_populates="jobs")
    matches = relationship("JobMatch", back_populates="job")
    status_history = relationship("JobStatusHistory", back_populates="job")
    duplicates = relationship("JobDuplicate", foreign_keys="JobDuplicate.job_id", back_populates="job")
    duplicate_of = relationship("JobDuplicate", foreign_keys="JobDuplicate.duplicate_of_id", back_populates="duplicate_job")
    
    __table_args__ = (
        Index('ix_jobs_platform_posted', 'platform_id', 'date_posted'),
        Index('ix_jobs_status_match', 'status', 'match_level'),
        Index('ix_jobs_score_posted', 'score', 'date_posted'),
        Index('ix_jobs_category_platform', 'category', 'platform_id'),
    )


class JobMatch(Base):
    __tablename__ = "job_matches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    skill_name = Column(String(200), nullable=False)
    match_score = Column(Float)
    match_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="matches")
    
    __table_args__ = (
        Index('ix_job_matches_job_skill', 'job_id', 'skill_name'),
    )


class JobStatusHistory(Base):
    __tablename__ = "job_status_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    old_status = Column(SQLEnum(JobStatus))
    new_status = Column(SQLEnum(JobStatus), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, index=True)
    changed_by = Column(String(100))
    notes = Column(Text)
    
    job = relationship("Job", back_populates="status_history")


class JobDuplicate(Base):
    __tablename__ = "job_duplicates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    duplicate_of_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    similarity_score = Column(Float)
    duplicate_reason = Column(String(200))
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    
    job = relationship("Job", foreign_keys=[job_id], back_populates="duplicates")
    duplicate_job = relationship("Job", foreign_keys=[duplicate_of_id], back_populates="duplicate_of")


class SearchRun(Base):
    __tablename__ = "search_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(100), unique=True, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    status = Column(String(50))
    platforms_scanned = Column(JSON)
    queries_executed = Column(Integer, default=0)
    pages_scanned = Column(Integer, default=0)
    raw_jobs_found = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    unverified_jobs = Column(Integer, default=0)
    verified_jobs = Column(Integer, default=0)
    relevant_jobs = Column(Integer, default=0)
    high_match_jobs = Column(Integer, default=0)
    errors = Column(JSON)
    duration_seconds = Column(Float)
    triggered_by = Column(String(50))


class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    agent_type = Column(String(50))
    description = Column(Text)
    config = Column(JSON)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    last_run_status = Column(String(50))
    last_run_duration = Column(Float)
    jobs_found = Column(Integer, default=0)
    jobs_verified = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Proposal(Base):
    __tablename__ = "proposals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    proposal_type = Column(String(20))
    content = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    response_received = Column(Boolean, default=False)
    
    job = relationship("Job")


class RedFlag(Base):
    __tablename__ = "red_flags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    flag_type = Column(String(100), nullable=False)
    severity = Column(SQLEnum(RiskLevel), nullable=False)
    description = Column(Text)
    evidence = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)


class ExportJob(Base):
    __tablename__ = "export_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    export_id = Column(String(100), unique=True, nullable=False, index=True)
    format = Column(String(20))
    filters = Column(JSON)
    status = Column(String(50))
    file_path = Column(String(500))
    record_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error = Column(Text)


def get_engine(database_url: str | None = None):
    """Create SQLAlchemy engine."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    
    if database_url is None:
        import os
        database_url = os.getenv("DATABASE_URL", "sqlite:///data/freelance_hunter.db")
    
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
    else:
        engine = create_engine(database_url, echo=False)
    
    return engine


def init_database(database_url: str | None = None):
    """Initialize database tables."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(database_url: str | None = None):
    """Get database session."""
    from sqlalchemy.orm import sessionmaker
    engine = get_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()