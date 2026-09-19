"""
Specialized Job Search Agents for different categories.
"""
import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote_plus

from .base import BaseAgent, AgentResult
from core.utils import (
    normalize_url, extract_domain, parse_date, extract_budget,
    categorize_job, estimate_difficulty, estimate_effort,
    extract_skills_from_text, clean_text, generate_job_id,
    validate_job_url, is_likely_spam
)
from core.config.loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class JobListing:
    """Raw job listing from a platform."""
    platform: str
    platform_url: str
    job_url: str
    title: str
    full_description: str
    short_summary: str = ""
    date_posted: Optional[datetime] = None
    time_since_posted: str = ""
    deadline: Optional[datetime] = None
    estimated_duration: str = ""
    budget: str = ""
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    currency: str = "USD"
    fixed_price_or_hourly: str = "not_specified"
    experience_level: str = ""
    required_skills: List[str] = field(default_factory=list)
    proposals_count: Optional[int] = None
    hires_count: Optional[int] = None
    bids_count: Optional[int] = None
    client_name: str = ""
    client_profile_url: str = ""
    client_country: str = ""
    client_timezone: str = ""
    client_rating: Optional[float] = None
    client_review_count: Optional[int] = None
    client_hire_history: Optional[int] = None
    client_total_spent: Optional[float] = None
    client_payment_status: str = ""
    attachments: List[str] = field(default_factory=list)
    required_files: List[str] = field(default_factory=list)
    required_output: List[str] = field(default_factory=list)
    contact_method: str = ""
    remote_allowed: bool = True
    location_requirement: str = ""
    login_required: bool = False
    source_agent: str = ""
    pages_scanned: int = 0
    results_scanned: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)


class BaseJobSearchAgent(BaseAgent, ABC):
    """Base class for specialized job search agents."""
    
    def __init__(self, name: str, category: str, keywords: List[str], config: Dict[str, Any] = None, db_manager=None):
        super().__init__(name, config, db_manager)
        self.category = category
        self.keywords = keywords
        self.skill_keywords = get_config().get_profile("skills", [])
        self.search_config = get_config().get("search", {})
        self.max_pages = self.search_config.get("max_pages_per_platform", 5)
        self.max_results = self.search_config.get("max_results_per_query", 50)
        self.rate_limit = self.search_config.get("rate_limit_delay", 2)
        self.timeout = self.search_config.get("timeout", 30)
        self.time_windows = self.search_config.get("time_windows", {})
    
    @abstractmethod
    async def search_platform(self, platform: Dict[str, Any], query: str, page: int = 1) -> List[JobListing]:
        """Search a specific platform for jobs."""
        pass
    
    @abstractmethod
    def parse_job_listing(self, raw_data: Dict[str, Any], platform: Dict[str, Any]) -> Optional[JobListing]:
        """Parse raw platform data into JobListing."""
        pass
    
    def generate_search_queries(self) -> List[str]:
        """Generate search queries for this agent's category."""
        queries = []
        
        # Base keywords
        for keyword in self.keywords:
            queries.append(keyword)
            queries.append(f"{keyword} freelance")
            queries.append(f"{keyword} remote")
            queries.append(f"{keyword} job")
            queries.append(f"freelance {keyword}")
        
        # Skill combinations
        for skill in self.skill_keywords[:10]:  # Limit to top 10 skills
            for keyword in self.keywords[:5]:  # Top 5 keywords
                queries.append(f"{skill} {keyword}")
        
        # Category-specific combinations
        queries.extend(self.get_category_queries())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique_queries.append(q)
        
        return unique_queries[:50]  # Limit total queries
    
    @abstractmethod
    def get_category_queries(self) -> List[str]:
        """Get category-specific search queries."""
        pass
    
    def filter_by_recency(self, job: JobListing, priority: int = 1) -> bool:
        """Filter job by recency based on priority level."""
        if not job.date_posted:
            return priority >= 3  # Allow unknown dates for lower priority
        
        now = datetime.utcnow()
        hours_ago = (now - job.date_posted).total_seconds() / 3600
        
        if priority == 1:
            return hours_ago <= self.time_windows.get("priority_1_hours", 24)
        elif priority == 2:
            return hours_ago <= self.time_windows.get("priority_2_hours", 72)
        elif priority == 3:
            return hours_ago <= self.time_windows.get("priority_3_hours", 168)
        else:
            return hours_ago <= self.time_windows.get("priority_4_hours", 720)
    
    def enrich_job_listing(self, job: JobListing) -> JobListing:
        """Enrich job listing with additional computed fields."""
        # Generate job ID
        job.raw_data["job_id"] = generate_job_id(job.platform, job.job_url, job.title)
        
        # Extract budget info
        budget_text = f"{job.budget} {job.full_description}"
        budget_info = extract_budget(budget_text)
        job.budget = budget_info.get("budget", job.budget)
        job.budget_min = budget_info.get("budget_min", job.budget_min)
        job.budget_max = budget_info.get("budget_max", job.budget_max)
        job.currency = budget_info.get("currency", job.currency)
        job.fixed_price_or_hourly = budget_info.get("type", job.fixed_price_or_hourly)
        
        # Categorize
        cat, subcat = categorize_job(job.title, job.full_description, self.get_category_keywords())
        job.raw_data["category"] = cat
        job.raw_data["sub_category"] = subcat
        
        # Extract matched skills
        matched_skills = extract_skills_from_text(
            f"{job.title} {job.full_description}", self.skill_keywords
        )
        job.raw_data["matched_skills"] = matched_skills
        
        # Estimate difficulty and effort
        job.raw_data["potential_difficulty"] = estimate_difficulty(
            job.title, job.full_description, job.required_skills
        )
        job.raw_data["estimated_effort"] = estimate_effort(
            job.title, job.full_description, budget_info, job.estimated_duration
        )
        
        # Check for spam
        is_spam, spam_reasons = is_likely_spam(job.title, job.full_description, {
            "rating": job.client_rating,
            "review_count": job.client_review_count,
            "total_spent": job.client_total_spent
        })
        job.raw_data["is_spam"] = is_spam
        job.raw_data["spam_reasons"] = spam_reasons
        
        # Validate URL
        job.raw_data["url_valid"] = validate_job_url(job.job_url, job.platform)
        
        return job
    
    @abstractmethod
    def get_category_keywords(self) -> Dict[str, List[str]]:
        """Get category keywords for categorization."""
        pass
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute job search across platforms."""
        platforms = kwargs.get("platforms", [])
        priority = kwargs.get("priority", 1)  # 1=highest (24h), 4=lowest (30d)
        max_pages = kwargs.get("max_pages", self.max_pages)
        queries = kwargs.get("queries", self.generate_search_queries())
        
        all_jobs = []
        total_scanned = 0
        total_kept = 0
        errors = []
        
        for platform in platforms:
            if not platform.get("has_job_listings", True):
                continue
            
            platform_jobs = []
            platform_scanned = 0
            
            for query in queries:
                if len(platform_jobs) >= self.max_results:
                    break
                
                for page in range(1, max_pages + 1):
                    try:
                        # Rate limiting
                        await asyncio.sleep(self.rate_limit)
                        
                        jobs = await self.search_platform(platform, query, page)
                        platform_scanned += len(jobs)
                        
                        # Filter by recency
                        filtered_jobs = [
                            j for j in jobs 
                            if self.filter_by_recency(j, priority)
                        ]
                        
                        # Enrich jobs
                        for job in filtered_jobs:
                            job.source_agent = self.name
                            job.pages_scanned = page
                            job.results_scanned = platform_scanned
                            job = self.enrich_job_listing(job)
                            platform_jobs.append(job)
                        
                        # Stop if no more results
                        if len(jobs) == 0:
                            break
                        
                        # Stop if enough results
                        if len(platform_jobs) >= self.max_results:
                            break
                            
                    except Exception as e:
                        error_msg = f"Error searching {platform['name']} page {page} for '{query}': {e}"
                        self.logger.warning(error_msg)
                        errors.append(error_msg)
                        break
            
            all_jobs.extend(platform_jobs)
            total_scanned += platform_scanned
            total_kept += len(platform_jobs)
            
            self.logger.info(f"Platform {platform['name']}: scanned {platform_scanned}, kept {len(platform_jobs)}")
        
        # Convert to dict format for storage
        job_dicts = [self._job_to_dict(job) for job in all_jobs]
        
        return AgentResult(
            success=len(errors) == 0,
            data={
                "jobs": job_dicts,
                "platforms_searched": len(platforms),
                "queries_used": len(queries),
                "errors": errors
            },
            items_found=total_scanned,
            items_processed=total_kept,
            metadata={"errors": errors}
        )
    
    def _job_to_dict(self, job: JobListing) -> Dict[str, Any]:
        """Convert JobListing to dictionary for storage."""
        return {
            "job_id": job.raw_data.get("job_id"),
            "platform": job.platform,
            "platform_url": job.platform_url,
            "job_url": job.job_url,
            "title": job.title,
            "full_description": job.full_description,
            "short_summary": job.short_summary or job.full_description[:500],
            "category": job.raw_data.get("category", self.category),
            "sub_category": job.raw_data.get("sub_category", ""),
            "matched_skills": job.raw_data.get("matched_skills", []),
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
            "client_timezone": job.client_timezone,
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
            "potential_difficulty": job.raw_data.get("potential_difficulty", "medium"),
            "estimated_effort": job.raw_data.get("estimated_effort", "medium"),
            "source_agent": job.source_agent,
            "pages_scanned": job.pages_scanned,
            "results_scanned": job.results_scanned,
            "raw_data": job.raw_data
        }


class DataEntryJobAgent(BaseJobSearchAgent):
    """Agent for finding data entry jobs."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        keywords = [
            "data entry", "data entry specialist", "excel data entry",
            "google sheets data entry", "copy paste", "copy typing",
            "invoice data entry", "receipt data entry", "image to excel",
            "pdf to excel", "data cleaning", "data formatting",
            "web research", "data collection", "virtual assistant",
            "administrative assistant", "database entry", "form filling",
            "catalog entry", "product listing", "data transcription",
            "manual data entry", "offline data entry", "online data entry",
            "data processing", "data extraction", "data mining"
        ]
        super().__init__("data_entry_agent", "data_entry", keywords, config, db_manager)
    
    def get_category_queries(self) -> List[str]:
        return [
            "data entry freelance jobs",
            "excel data entry remote",
            "google sheets freelance",
            "invoice data entry work",
            "pdf to excel conversion jobs",
            "image to excel data entry",
            "copy typing jobs online",
            "web research data collection",
            "virtual assistant data entry",
            "administrative data entry remote",
            "data cleaning freelance",
            "spreadsheet data entry jobs",
            "form filling data entry",
            "catalog product data entry",
            "database data entry work"
        ]
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        return {
            "data_entry": [
                "data entry", "copy typing", "copy paste", "data input",
                "data processing", "form filling", "database entry"
            ],
            "excel": [
                "excel", "spreadsheet", "google sheets", "xlsx", "csv",
                "pivot table", "vlookup", "formulas"
            ],
            "research": [
                "web research", "data collection", "data mining",
                "internet research", "lead generation", "market research"
            ],
            "conversion": [
                "pdf to excel", "image to excel", "pdf to csv",
                "scanned to excel", "ocr data entry"
            ],
            "admin": [
                "virtual assistant", "administrative", "data organizer",
                "file management", "document processing"
            ]
        }
    
    async def search_platform(self, platform: Dict[str, Any], query: str, page: int = 1) -> List[JobListing]:
        """Search platform for data entry jobs."""
        # This would be implemented with actual platform-specific scrapers
        # For now, return empty list - real implementation would use scrapers
        self.logger.debug(f"Searching {platform['name']} for: {query} (page {page})")
        return []
    
    def parse_job_listing(self, raw_data: Dict[str, Any], platform: Dict[str, Any]) -> Optional[JobListing]:
        """Parse raw data into JobListing."""
        # Platform-specific parsing would go here
        return None


class DocumentPdfWordAgent(BaseJobSearchAgent):
    """Agent for finding document/PDF/Word jobs."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        keywords = [
            "pdf to word", "pdf conversion", "pdf formatting", "word formatting",
            "document formatting", "ocr", "scanned document", "typing pdf",
            "document conversion", "pdf to excel", "word to pdf", "document cleanup",
            "copy typing", "transcription", "document editing", "proofreading",
            "format conversion", "file conversion", "document processing"
        ]
        super().__init__("document_pdf_word_agent", "document_pdf_word", keywords, config, db_manager)
    
    def get_category_queries(self) -> List[str]:
        return [
            "pdf to word freelance",
            "pdf conversion jobs",
            "word formatting freelance",
            "document formatting work",
            "ocr typing jobs",
            "scanned document transcription",
            "document conversion freelance",
            "pdf to excel conversion jobs",
            "word to pdf conversion",
            "document cleanup jobs",
            "copy typing from pdf",
            "transcription freelance work",
            "document editing jobs",
            "file format conversion freelance"
        ]
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        return {
            "pdf": ["pdf", "pdf conversion", "pdf formatting", "pdf to word", "pdf to excel"],
            "word": ["word", "microsoft word", "docx", "doc", "word formatting"],
            "ocr": ["ocr", "optical character recognition", "scanned", "image to text"],
            "formatting": ["formatting", "layout", "document design", "page setup"],
            "conversion": ["conversion", "convert", "file conversion", "format conversion"],
            "typing": ["typing", "transcription", "copy typing", "data entry"]
        }
    
    async def search_platform(self, platform: Dict[str, Any], query: str, page: int = 1) -> List[JobListing]:
        self.logger.debug(f"Searching {platform['name']} for: {query} (page {page})")
        return []
    
    def parse_job_listing(self, raw_data: Dict[str, Any], platform: Dict[str, Any]) -> Optional[JobListing]:
        return None


class PowerPointPresentationAgent(BaseJobSearchAgent):
    """Agent for finding PowerPoint/presentation jobs."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        keywords = [
            "powerpoint", "powerpoint presentation", "powerpoint formatting",
            "presentation design", "presentation redesign", "slide formatting",
            "pitch deck", "business presentation", "academic presentation",
            "canva presentation", "google slides", "presentation formatting",
            "slide design", "keynote", "presentation template", "slide deck",
            "investor deck", "sales presentation", "conference presentation"
        ]
        super().__init__("powerpoint_presentation_agent", "powerpoint_presentation", keywords, config, db_manager)
    
    def get_category_queries(self) -> List[str]:
        return [
            "powerpoint presentation design freelance",
            "presentation formatting jobs",
            "pitch deck design freelance",
            "slide redesign work",
            "business presentation design",
            "academic presentation freelance",
            "canva presentation design jobs",
            "google slides freelance",
            "presentation template design",
            "slide formatting freelance",
            "powerpoint expert needed",
            "presentation makeover jobs",
            "investor deck design freelance",
            "sales presentation design"
        ]
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        return {
            "powerpoint": ["powerpoint", "ppt", "pptx", "microsoft powerpoint"],
            "design": ["design", "presentation design", "slide design", "visual design"],
            "formatting": ["formatting", "slide formatting", "layout", "template"],
            "pitch_deck": ["pitch deck", "investor deck", "funding deck", "startup deck"],
            "canva": ["canva", "canva presentation", "canva design"],
            "google_slides": ["google slides", "slides", "gslides"],
            "keynote": ["keynote", "apple keynote"]
        }
    
    async def search_platform(self, platform: Dict[str, Any], query: str, page: int = 1) -> List[JobListing]:
        self.logger.debug(f"Searching {platform['name']} for: {query} (page {page})")
        return []
    
    def parse_job_listing(self, raw_data: Dict[str, Any], platform: Dict[str, Any]) -> Optional[JobListing]:
        return None


class ExcelSpreadsheetAgent(BaseJobSearchAgent):
    """Agent for finding Excel/spreadsheet jobs."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        keywords = [
            "excel", "microsoft excel", "google sheets", "spreadsheet",
            "spreadsheet formatting", "spreadsheet cleanup", "excel formulas",
            "excel data cleaning", "excel formatting", "excel conversion",
            "spreadsheet organization", "data analysis excel", "vlookup",
            "pivot table", "excel dashboard", "excel automation", "excel macros",
            "spreadsheet data entry", "excel data entry", "sheets formatting"
        ]
        super().__init__("excel_spreadsheet_agent", "excel_spreadsheet", keywords, config, db_manager)
    
    def get_category_queries(self) -> List[str]:
        return [
            "excel freelance jobs",
            "google sheets freelance",
            "spreadsheet formatting jobs",
            "excel data cleaning freelance",
            "excel formulas help",
            "pivot table freelance",
            "excel dashboard design",
            "spreadsheet organization work",
            "excel automation freelance",
            "excel vlookup jobs",
            "data analysis excel freelance",
            "spreadsheet cleanup jobs",
            "excel conversion freelance",
            "microsoft excel expert needed"
        ]
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        return {
            "excel": ["excel", "microsoft excel", "xlsx", "xls", "excel formulas"],
            "google_sheets": ["google sheets", "sheets", "gsheets"],
            "formulas": ["formulas", "vlookup", "index match", "sumif", "pivot table"],
            "cleaning": ["data cleaning", "cleanup", "data quality", "deduplication"],
            "formatting": ["formatting", "conditional formatting", "charts", "dashboards"],
            "automation": ["automation", "macros", "vba", "scripts", "power query"]
        }
    
    async def search_platform(self, platform: Dict[str, Any], query: str, page: int = 1) -> List[JobListing]:
        self.logger.debug(f"Searching {platform['name']} for: {query} (page {page})")
        return []
    
    def parse_job_listing(self, raw_data: Dict[str, Any], platform: Dict[str, Any]) -> Optional[JobListing]:
        return None


class GeneralFreelanceAgent(BaseJobSearchAgent):
    """Agent for finding general easy-entry freelance work."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        keywords = [
            "virtual assistant", "web research", "copy paste", "data collection",
            "administrative tasks", "product listing", "file conversion",
            "internet research", "microsoft office", "google workspace",
            "administrative support", "simple computer tasks", "data extraction",
            "file organization", "document organization", "online research",
            "data entry clerk", "office assistant", "remote assistant",
            "data processor", "information researcher", "content organizer"
        ]
        super().__init__("general_freelance_agent", "general_freelance", keywords, config, db_manager)
    
    def get_category_queries(self) -> List[str]:
        return [
            "virtual assistant jobs remote",
            "web research freelance",
            "copy paste jobs online",
            "data collection freelance",
            "administrative assistant remote",
            "product listing jobs",
            "file conversion freelance",
            "internet research jobs",
            "microsoft office freelance",
            "google workspace jobs",
            "administrative support remote",
            "simple data entry tasks",
            "file organization freelance",
            "document organization jobs",
            "online researcher needed"
        ]
    
    def get_category_keywords(self) -> Dict[str, List[str]]:
        return {
            "virtual_assistant": ["virtual assistant", "va", "remote assistant", "online assistant"],
            "research": ["research", "web research", "internet research", "market research"],
            "admin": ["administrative", "admin", "office support", "clerical"],
            "data": ["data entry", "data processing", "data collection", "data extraction"],
            "organization": ["organization", "file organization", "document management"],
            "conversion": ["conversion", "file conversion", "format conversion"],
            "listing": ["product listing", "catalog", "ecommerce listing", "data listing"]
        }
    
    async def search_platform(self, platform: Dict[str, Any], query: str, page: int = 1) -> List[JobListing]:
        self.logger.debug(f"Searching {platform['name']} for: {query} (page {page})")
        return []
    
    def parse_job_listing(self, raw_data: Dict[str, Any], platform: Dict[str, Any]) -> Optional[JobListing]:
        return None


class SearchEngineAgent(BaseAgent):
    """Agent that searches search engines for job listings."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        super().__init__("search_engine_agent", config, db_manager)
        self.config = config or get_config()._config
        self.search_engines = self.config.get("search", {}).get("search_engines", ["google", "bing", "duckduckgo"])
        self.site_queries = {
            "upwork": "site:upwork.com/jobs",
            "freelancer": "site:freelancer.com/projects",
            "peopleperhour": "site:peopleperhour.com/freelance-jobs",
            "guru": "site:guru.com/d/jobs",
            "workana": "site:workana.com/jobs",
            "contra": "site:contra.com/discover",
            "fiverr": "site:fiverr.com/search/gigs",
            "khamsat": "site:khamsat.com/projects",
            "mostaql": "site:mostaql.com/projects",
            "linkedin": "site:linkedin.com/jobs"
        }
    
    def generate_search_queries(self, category: str = "all") -> List[str]:
        """Generate search engine queries for job discovery."""
        base_queries = [
            '"PowerPoint presentation" freelance job',
            '"PDF to Word" freelance job',
            '"Excel data entry" freelance',
            '"image to Excel" freelance',
            '"invoice data entry" freelance',
            '"Google Sheets" freelance job',
            '"presentation formatting" freelance',
            '"data entry" remote freelance',
            '"copy typing" freelance',
            '"PDF conversion" freelance job',
            '"virtual assistant" freelance job',
            '"web research" freelance',
            '"document formatting" freelance',
            '"spreadsheet cleanup" freelance',
            '"pitch deck design" freelance'
        ]
        
        # Add site-specific queries
        queries = []
        for site, site_query in self.site_queries.items():
            for base in base_queries:
                queries.append(f"{site_query} {base}")
        
        # Add general queries
        queries.extend(base_queries)
        
        # Add variations
        variations = []
        for q in queries[:20]:  # Limit base queries
            variations.append(q.replace('freelance', 'remote'))
            variations.append(q.replace('freelance', 'contract'))
            variations.append(q.replace('job', 'project'))
            variations.append(q.replace('job', 'gig'))
        
        queries.extend(variations)
        
        # Deduplicate
        seen = set()
        unique = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique.append(q)
        
        return unique[:100]
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute search engine queries."""
        # This would use actual search engine APIs or scraping
        # For now, return the generated queries as a result
        queries = self.generate_search_queries()
        
        return AgentResult(
            success=True,
            data={
                "queries": queries,
                "search_engines": self.search_engines,
                "site_queries": self.site_queries
            },
            items_found=len(queries),
            items_processed=0,
            metadata={"note": "Search engine integration requires API keys or scraping implementation"}
        )


# Factory function to create all specialized agents
def create_specialized_agents(config: Dict[str, Any] = None, db_manager=None) -> List[BaseJobSearchAgent]:
    """Create all specialized job search agents."""
    agents = [
        DataEntryJobAgent(config, db_manager),
        DocumentPdfWordAgent(config, db_manager),
        PowerPointPresentationAgent(config, db_manager),
        ExcelSpreadsheetAgent(config, db_manager),
        GeneralFreelanceAgent(config, db_manager),
        SearchEngineAgent(config, db_manager)
    ]
    return agents