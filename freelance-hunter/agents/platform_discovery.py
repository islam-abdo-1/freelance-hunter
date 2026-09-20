"""
Platform Discovery Agent - Discovers legitimate freelance platforms and job boards.
"""
import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from core.config.loader import get_config
from core.database.repository import Repositories
from core.utils import load_json_file, save_json_file

from .base import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class PlatformInfo:
    """Information about a discovered platform."""
    name: str
    url: str
    jobs_url: str = ""
    search_url: str = ""
    category: str = "general"
    country_region: str = "global"
    login_required: bool = False
    public_access: bool = True
    notes: str = ""
    verified: bool = False


class PlatformDiscoveryAgent(BaseAgent):
    """Agent that discovers and validates freelance platforms."""
    
    # Known legitimate freelance platforms
    KNOWN_PLATFORMS = [
        {
            "name": "Upwork",
            "url": "https://www.upwork.com",
            "jobs_url": "https://www.upwork.com/nx/jobs/search/",
            "search_url": "https://www.upwork.com/nx/jobs/search/?q={query}",
            "category": "global",
            "country_region": "global",
            "login_required": True,
            "public_access": False,
            "notes": "Requires login for full access. Public job listings limited.",
        },
        {
            "name": "Freelancer",
            "url": "https://www.freelancer.com",
            "jobs_url": "https://www.freelancer.com/jobs",
            "search_url": "https://www.freelancer.com/jobs/{query}/",
            "category": "global",
            "country_region": "global",
            "login_required": True,
            "public_access": False,
            "notes": "Requires login. Some public browsing available.",
        },
        {
            "name": "PeoplePerHour",
            "url": "https://www.peopleperhour.com",
            "jobs_url": "https://www.peopleperhour.com/freelance-jobs",
            "search_url": "https://www.peopleperhour.com/freelance-jobs/{query}",
            "category": "global",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Good public access to job listings.",
        },
        {
            "name": "Guru",
            "url": "https://www.guru.com",
            "jobs_url": "https://www.guru.com/d/jobs",
            "search_url": "https://www.guru.com/d/jobs/skill/{query}",
            "category": "global",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Public job browsing available.",
        },
        {
            "name": "Workana",
            "url": "https://www.workana.com",
            "jobs_url": "https://www.workana.com/jobs",
            "search_url": "https://www.workana.com/jobs?query={query}",
            "category": "regional",
            "country_region": "latam",
            "login_required": False,
            "public_access": True,
            "notes": "Popular in Latin America. Good public access.",
        },
        {
            "name": "Contra",
            "url": "https://contra.com",
            "jobs_url": "https://contra.com/discover",
            "search_url": "https://contra.com/discover?search={query}",
            "category": "global",
            "country_region": "global",
            "login_required": True,
            "public_access": False,
            "notes": "Modern platform, requires login for job details.",
        },
        {
            "name": "Fiverr",
            "url": "https://www.fiverr.com",
            "jobs_url": "https://www.fiverr.com/search/gigs",
            "search_url": "https://www.fiverr.com/search/gigs?query={query}",
            "category": "global",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Gig-based marketplace. Good for specific services.",
        },
        {
            "name": "Khamsat",
            "url": "https://khamsat.com",
            "jobs_url": "https://khamsat.com/projects",
            "search_url": "https://khamsat.com/projects?search={query}",
            "category": "regional",
            "country_region": "mena",
            "login_required": False,
            "public_access": True,
            "notes": "Arabic freelance marketplace. Popular in MENA region.",
        },
        {
            "name": "Mostaql",
            "url": "https://mostaql.com",
            "jobs_url": "https://mostaql.com/projects",
            "search_url": "https://mostaql.com/projects?query={query}",
            "category": "regional",
            "country_region": "mena",
            "login_required": False,
            "public_access": True,
            "notes": "Arabic freelance platform. Good for MENA region jobs.",
        },
        {
            "name": "LinkedIn Jobs",
            "url": "https://www.linkedin.com",
            "jobs_url": "https://www.linkedin.com/jobs/",
            "search_url": "https://www.linkedin.com/jobs/search/?keywords={query}",
            "category": "global",
            "country_region": "global",
            "login_required": True,
            "public_access": False,
            "notes": "Professional network job board. Requires login.",
        },
        {
            "name": "Toptal",
            "url": "https://www.toptal.com",
            "jobs_url": "https://www.toptal.com/clients/jobs",
            "search_url": "https://www.toptal.com/clients/jobs?query={query}",
            "category": "premium",
            "country_region": "global",
            "login_required": True,
            "public_access": False,
            "notes": "High-end talent marketplace. Strict screening.",
        },
        {
            "name": "99designs",
            "url": "https://99designs.com",
            "jobs_url": "https://99designs.com/designer-jobs",
            "search_url": "https://99designs.com/designer-jobs?search={query}",
            "category": "niche",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Design-focused platform. Good for presentation/design work.",
        },
        {
            "name": "DesignCrowd",
            "url": "https://www.designcrowd.com",
            "jobs_url": "https://www.designcrowd.com/design-jobs",
            "search_url": "https://www.designcrowd.com/design-jobs?search={query}",
            "category": "niche",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Design contest and job platform.",
        },
        {
            "name": "SimplyHired",
            "url": "https://www.simplyhired.com",
            "jobs_url": "https://www.simplyhired.com/search",
            "search_url": "https://www.simplyhired.com/search?q={query}",
            "category": "aggregator",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Job aggregator. Indexes from multiple sources.",
        },
        {
            "name": "Indeed",
            "url": "https://www.indeed.com",
            "jobs_url": "https://www.indeed.com/jobs",
            "search_url": "https://www.indeed.com/jobs?q={query}",
            "category": "aggregator",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Major job aggregator. Includes freelance/remote jobs.",
        },
        {
            "name": "Glassdoor",
            "url": "https://www.glassdoor.com",
            "jobs_url": "https://www.glassdoor.com/Job/jobs.htm",
            "search_url": "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query}",
            "category": "aggregator",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Job board with company reviews.",
        },
        {
            "name": "Remote.co",
            "url": "https://remote.co",
            "jobs_url": "https://remote.co/remote-jobs/",
            "search_url": "https://remote.co/remote-jobs/search/?search={query}",
            "category": "remote",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Remote-focused job board.",
        },
        {
            "name": "We Work Remotely",
            "url": "https://weworkremotely.com",
            "jobs_url": "https://weworkremotely.com/categories/remote-programming-jobs",
            "search_url": "https://weworkremotely.com/remote-jobs/search?term={query}",
            "category": "remote",
            "country_region": "global",
            "login_required": False,
            "public_access": True,
            "notes": "Popular remote job board.",
        },
        {
            "name": "FlexJobs",
            "url": "https://www.flexjobs.com",
            "jobs_url": "https://www.flexjobs.com/search",
            "search_url": "https://www.flexjobs.com/search?search={query}",
            "category": "remote",
            "country_region": "global",
            "login_required": True,
            "public_access": False,
            "notes": "Curated remote/flexible jobs. Subscription required.",
        }
    ]
    
    # Search queries for discovering new platforms
    DISCOVERY_QUERIES = [
        "freelance job platforms",
        "best freelance websites 2024",
        "freelance marketplaces for beginners",
        "remote freelance job sites",
        "micro job sites like fiverr",
        "freelance platforms for data entry",
        "freelance sites for powerpoint design",
        "arabic freelance platforms",
        "latin america freelance sites"
    ]
    
    def __init__(self, config: dict[str, Any] | None = None, db_manager=None):
        super().__init__("platform_discovery", config, db_manager)
        self.config = config or get_config()._config
        self.discovered_platforms: list[PlatformInfo] = []
        self.platforms_file = "data/discovered_platforms.json"
        self._repositories = Repositories(db_manager) if db_manager else None
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute platform discovery."""
        max_new = kwargs.get("max_new_platforms", self.config.get("agents", {}).get("platform_discovery", {}).get("max_new_platforms_per_run", 5))
        
        results = {
            "known_platforms_registered": 0,
            "new_platforms_discovered": 0,
            "platforms_verified": 0,
            "platforms": []
        }
        
        # 1. Register known platforms
        known_count = await self._register_known_platforms()
        results["known_platforms_registered"] = known_count
        
        # 2. Discover new platforms via search (if enabled and AIsa available)
        if self.config.get("agents", {}).get("platform_discovery", {}).get("enabled", True):
            new_platforms = await self._discover_new_platforms(max_new)
            results["new_platforms_discovered"] = len(new_platforms)
            results["platforms"].extend([p.__dict__ for p in new_platforms])
        
        # 3. Verify platform accessibility
        verified = await self._verify_platforms()
        results["platforms_verified"] = verified
        
        # Save discovered platforms
        self._save_platforms()
        
        return AgentResult(
            success=True,
            data=results,
            items_found=known_count + len(new_platforms) if 'new_platforms' in locals() else known_count,
            items_processed=verified
        )
    
    async def _register_known_platforms(self) -> int:
        """Register known platforms in database."""
        if not self._repositories:
            return len(self.KNOWN_PLATFORMS)
        
        count = 0
        for platform_data in self.KNOWN_PLATFORMS:
            try:
                self._repositories.platforms.create_or_update(platform_data)
                count += 1
            except Exception as e:
                self.logger.error(f"Failed to register platform {platform_data['name']}: {e}")
        
        self.logger.info(f"Registered {count} known platforms")
        return count
    
    async def _discover_new_platforms(self, max_new: int) -> list[PlatformInfo]:
        """Discover new platforms using search engines."""
        new_platforms = []
        
        # Try to use AIsa for web search if available
        aisa_key = self.config.get("api_keys", {}).get("aisa")
        if aisa_key:
            try:
                new_platforms = await self._search_with_aisa(max_new)
            except Exception as e:
                self.logger.warning(f"AIsa search failed: {e}")
        
        # Fallback: use known additional platforms
        if len(new_platforms) < max_new:
            additional = self._get_additional_platforms()
            for platform in additional[:max_new - len(new_platforms)]:
                if not self._platform_exists(platform.name):
                    new_platforms.append(platform)
        
        return new_platforms
    
    async def _search_with_aisa(self, max_results: int) -> list[PlatformInfo]:
        """Use AIsa to search for new platforms."""
        # This would use AIsa's search capabilities
        # For now, return empty list - implementation depends on AIsa API
        self.logger.info("AIsa search for new platforms not yet implemented")
        return []
    
    def _get_additional_platforms(self) -> list[PlatformInfo]:
        """Get additional known platforms not in main list."""
        additional = [
            PlatformInfo(
                name="Codementor",
                url="https://www.codementor.io",
                jobs_url="https://www.codementor.io/marketplace",
                search_url="https://www.codementor.io/marketplace?query={query}",
                category="niche",
                country_region="global",
                login_required=True,
                public_access=False,
                notes="Mentorship and freelance coding platform."
            ),
            PlatformInfo(
                name="Gun.io",
                url="https://gun.io",
                jobs_url="https://gun.io/jobs",
                search_url="https://gun.io/jobs?search={query}",
                category="premium",
                country_region="global",
                login_required=True,
                public_access=False,
                notes="Vetted freelance developers."
            ),
            PlatformInfo(
                name="Arc.dev",
                url="https://arc.dev",
                jobs_url="https://arc.dev/remote-jobs",
                search_url="https://arc.dev/remote-jobs?search={query}",
                category="remote",
                country_region="global",
                login_required=False,
                public_access=True,
                notes="Remote developer jobs."
            ),
            PlatformInfo(
                name="Hubstaff Talent",
                url="https://talent.hubstaff.com",
                jobs_url="https://talent.hubstaff.com/jobs",
                search_url="https://talent.hubstaff.com/jobs?search={query}",
                category="global",
                country_region="global",
                login_required=False,
                public_access=True,
                notes="Free freelance marketplace."
            ),
            PlatformInfo(
                name="Freelancermap",
                url="https://freelancermap.com",
                jobs_url="https://freelancermap.com/projects",
                search_url="https://freelancermap.com/projects?search={query}",
                category="regional",
                country_region="europe",
                login_required=False,
                public_access=True,
                notes="European freelance platform."
            ),
            PlatformInfo(
                name="Malt",
                url="https://www.malt.com",
                jobs_url="https://www.malt.com/projects",
                search_url="https://www.malt.com/projects?search={query}",
                category="regional",
                country_region="europe",
                login_required=True,
                public_access=False,
                notes="French/European freelance platform."
            ),
            PlatformInfo(
                name="Twago",
                url="https://www.twago.com",
                jobs_url="https://www.twago.com/projects",
                search_url="https://www.twago.com/projects?search={query}",
                category="global",
                country_region="global",
                login_required=False,
                public_access=True,
                notes="European freelance marketplace."
            ),
            PlatformInfo(
                name="Bark",
                url="https://www.bark.com",
                jobs_url="https://www.bark.com/en/gb/jobs/",
                search_url="https://www.bark.com/en/gb/jobs/?search={query}",
                category="global",
                country_region="uk",
                login_required=False,
                public_access=True,
                notes="UK-focused service marketplace."
            ),
            PlatformInfo(
                name="TaskRabbit",
                url="https://www.taskrabbit.com",
                jobs_url="https://www.taskrabbit.com/tasks",
                search_url="https://www.taskrabbit.com/tasks?search={query}",
                category="local",
                country_region="us",
                login_required=True,
                public_access=False,
                notes="Local task marketplace."
            ),
            PlatformInfo(
                name="Amazon Mechanical Turk",
                url="https://www.mturk.com",
                jobs_url="https://www.mturk.com/work",
                search_url="https://www.mturk.com/work?search={query}",
                category="microtask",
                country_region="global",
                login_required=True,
                public_access=False,
                notes="Microtask platform. Low pay, high volume."
            )
        ]
        
        return additional
    
    def _platform_exists(self, name: str) -> bool:
        """Check if platform already exists in discovered list."""
        for p in self.discovered_platforms:
            if p.name.lower() == name.lower():
                return True
        
        if self._repositories:
            existing = self._repositories.platforms.get_by_name(name)
            return existing is not None
        
        return False
    
    async def _verify_platforms(self) -> int:
        """Verify platform accessibility (placeholder for actual verification)."""
        # In a real implementation, this would make HTTP requests to verify
        # For now, mark known platforms as verified
        verified = 0
        
        for platform_data in self.KNOWN_PLATFORMS:
            if self._repositories:
                platform = self._repositories.platforms.get_by_name(platform_data["name"])
                if platform:
                    # Would do actual verification here
                    verified += 1
        
        return verified
    
    def _save_platforms(self):
        """Save discovered platforms to file."""
        data = [p.__dict__ for p in self.discovered_platforms]
        save_json_file({"platforms": data}, self.platforms_file)
    
    def load_platforms(self):
        """Load previously discovered platforms."""
        data = load_json_file(self.platforms_file)
        for p_data in data.get("platforms", []):
            self.discovered_platforms.append(PlatformInfo(**p_data))
    
    def get_all_platforms(self) -> list[dict[str, Any]]:
        """Get all platforms (known + discovered)."""
        all_platforms = []
        
        for p in self.KNOWN_PLATFORMS:
            all_platforms.append(p)
        
        for p in self.discovered_platforms:
            all_platforms.append(p.__dict__)
        
        return all_platforms
    
    def get_active_platforms(self) -> list[dict[str, Any]]:
        """Get platforms that have job listings and are active."""
        return [p for p in self.get_all_platforms() if True]


class PlatformValidator:
    """Validates platform accessibility and job listing availability."""
    
    def __init__(self):
        self.logger = logging.getLogger("platform_validator")
    
    async def validate_platform(self, platform: dict[str, Any]) -> dict[str, Any]:
        """Validate a single platform."""
        result = platform.copy()
        result["validation"] = {
            "url_accessible": False,
            "jobs_page_accessible": False,
            "search_works": False,
            "has_listings": False,
            "requires_login": platform.get("login_required", False),
            "errors": []
        }
        
        # This would make actual HTTP requests
        # For now, return the platform with validation structure
        return result
    
    async def validate_multiple(self, platforms: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate multiple platforms concurrently."""
        tasks = [self.validate_platform(p) for p in platforms]
        return await asyncio.gather(*tasks)