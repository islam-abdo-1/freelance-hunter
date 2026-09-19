"""
Proposal/Application Agent - Generates customized proposals for jobs.
"""
import logging
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .base import BaseAgent, AgentResult
from core.utils import clean_text, truncate_text
from core.config.loader import get_config

logger = logging.getLogger(__name__)


@dataclass
class ProposalSet:
    """Set of proposals for a job."""
    job_id: str
    short: str
    normal: str
    ultra_short: str
    generated_at: datetime


class ProposalAgent(BaseAgent):
    """Agent that generates customized proposals for jobs."""
    
    def __init__(self, config: Dict[str, Any] = None, db_manager=None):
        super().__init__("proposal_agent", config, db_manager)
        self.config = config or get_config()._config
        self.proposal_config = self.config.get("proposal", {})
        self.profile = get_config().get_profile()
        
        # Guidelines
        self.guidelines = self.proposal_config.get("guidelines", [])
        self.templates_enabled = self.proposal_config.get("templates", {})
        
        # User info for proposals
        self.user_skills = self.profile.get("skills", [])
        self.user_languages = self.profile.get("languages", [])
        self.user_location = self.profile.get("location", "")
        self.user_availability = self.profile.get("availability", "Remote")
        self.user_strengths = self.profile.get("strengths", [])
        self.user_bio = self.profile.get("bio", "")
        self.hourly_range = self.profile.get("hourly_rate_range", {"min": 5, "max": 25, "currency": "USD"})
    
    async def execute(self, **kwargs) -> AgentResult:
        """Generate proposals for jobs."""
        jobs = kwargs.get("jobs", [])
        
        proposals = []
        for job in jobs:
            # Only generate for relevant matches
            match_level = job.get("match_level", "NOT_RELEVANT")
            if match_level in ["EXCELLENT_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH"]:
                proposal_set = self._generate_proposals(job)
                proposals.append(self._proposal_to_dict(proposal_set))
        
        return AgentResult(
            success=True,
            data={"proposals": proposals},
            items_found=len(jobs),
            items_processed=len(proposals)
        )
    
    def _generate_proposals(self, job: Dict[str, Any]) -> ProposalSet:
        """Generate three types of proposals for a job."""
        job_id = job.get("job_id", "unknown")
        
        # Analyze job to customize proposal
        analysis = self._analyze_job(job)
        
        # Generate proposals
        short = self._generate_short_proposal(job, analysis)
        normal = self._generate_normal_proposal(job, analysis)
        ultra_short = self._generate_ultra_short_proposal(job, analysis)
        
        return ProposalSet(
            job_id=job_id,
            short=short,
            normal=normal,
            ultra_short=ultra_short,
            generated_at=datetime.utcnow()
        )
    
    def _analyze_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze job to extract key information for proposal."""
        title = job.get("title", "")
        description = job.get("full_description", "")
        skills = job.get("required_skills", [])
        matched_skills = job.get("matched_skills", [])
        budget = job.get("budget", "")
        client_name = job.get("client_name", "Client")
        platform = job.get("platform", "")
        
        # Extract key requirements
        key_requirements = self._extract_key_requirements(description)
        deliverables = self._extract_deliverables(description)
        tools_mentioned = self._extract_tools(description)
        
        return {
            "title": title,
            "client_name": client_name,
            "platform": platform,
            "budget": budget,
            "matched_skills": matched_skills,
            "key_requirements": key_requirements,
            "deliverables": deliverables,
            "tools_mentioned": tools_mentioned,
            "is_fixed_price": job.get("fixed_price_or_hourly") == "fixed",
            "is_hourly": job.get("fixed_price_or_hourly") == "hourly"
        }
    
    def _extract_key_requirements(self, description: str) -> List[str]:
        """Extract key requirements from job description."""
        requirements = []
        desc_lower = description.lower()
        
        # Common requirement patterns
        patterns = [
            r"(?:must have|required|need|should have|experience with)\s+([^.,\n]+)",
            r"(?:proficient in|expert in|skilled in|knowledge of)\s+([^.,\n]+)",
            r"(?:familiar with|comfortable with)\s+([^.,\n]+)"
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, desc_lower)
            for match in matches:
                req = match.strip()
                if len(req) > 5 and len(req) < 100:
                    requirements.append(req)
        
        # Also look for bullet points
        lines = description.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('-', '•', '*', '–')) and len(line) > 10:
                requirements.append(line[1:].strip())
        
        return list(set(requirements))[:8]
    
    def _extract_deliverables(self, description: str) -> List[str]:
        """Extract deliverables from job description."""
        deliverables = []
        desc_lower = description.lower()
        
        keywords = ["deliver", "output", "provide", "submit", "create", "format", "convert", "organize"]
        
        import re
        sentences = re.split(r'[.!?]', description)
        for sentence in sentences:
            sentence = sentence.strip()
            if any(kw in sentence.lower() for kw in keywords) and len(sentence) > 20:
                deliverables.append(sentence)
        
        return deliverables[:5]
    
    def _extract_tools(self, description: str) -> List[str]:
        """Extract mentioned tools/software from description."""
        tools = []
        desc_lower = description.lower()
        
        known_tools = [
            "excel", "google sheets", "powerpoint", "google slides", "canva",
            "word", "google docs", "pdf", "adobe", "ocr", "vba", "macros",
            "pivot table", "vlookup", "power query", "power bi", "tableau"
        ]
        
        for tool in known_tools:
            if tool in desc_lower:
                tools.append(tool)
        
        return tools
    
    def _generate_short_proposal(self, job: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate short proposal (2-3 paragraphs)."""
        client_name = analysis["client_name"]
        title = analysis["title"]
        matched_skills = analysis["matched_skills"]
        key_requirements = analysis["key_requirements"]
        deliverables = analysis["deliverables"]
        tools = analysis["tools_mentioned"]
        
        # Build proposal
        parts = []
        
        # Greeting
        parts.append(f"Hi {client_name},")
        parts.append("")
        
        # Opening - reference specific job
        if "data entry" in title.lower() or "excel" in title.lower() or "spreadsheet" in title.lower():
            parts.append(f"I read your project '{title}' and I can help with the data entry and spreadsheet work you need.")
        elif "powerpoint" in title.lower() or "presentation" in title.lower() or "slide" in title.lower():
            parts.append(f"I saw your project '{title}' and I'd love to help create/format your presentation.")
        elif "pdf" in title.lower() or "word" in title.lower() or "document" in title.lower():
            parts.append(f"I came across your project '{title}' and I can assist with the document conversion/formatting.")
        else:
            parts.append(f"I'm interested in your project '{title}' and believe I can deliver what you need.")
        
        # Highlight matched skills
        if matched_skills:
            skills_str = ", ".join(matched_skills[:4])
            parts.append(f"I have experience with {skills_str}, which align well with your requirements.")
        
        # Mention specific requirements
        if key_requirements:
            req_str = "; ".join(key_requirements[:3])
            parts.append(f"I can handle: {req_str}.")
        
        # Deliverables
        if deliverables:
            parts.append(f"I'll deliver: {deliverables[0]}")
        
        # Tools
        if tools:
            tools_str = ", ".join(tools[:3])
            parts.append(f"I work with {tools_str} daily.")
        
        # Closing
        parts.append("")
        parts.append("I'm available to start immediately and can provide samples if helpful.")
        parts.append("")
        parts.append("Quick question: Do you have a preferred file format or template for the final deliverable?")
        parts.append("")
        parts.append("Best regards,")

        return "\n".join(parts)
    
    def _generate_normal_proposal(self, job: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate normal proposal (4-5 paragraphs)."""
        client_name = analysis["client_name"]
        title = analysis["title"]
        matched_skills = analysis["matched_skills"]
        key_requirements = analysis["key_requirements"]
        deliverables = analysis["deliverables"]
        tools = analysis["tools_mentioned"]
        is_fixed = analysis["is_fixed_price"]
        is_hourly = analysis["is_hourly"]
        
        parts = []
        
        # Greeting
        parts.append(f"Hi {client_name},")
        parts.append("")
        
        # Personalized opening
        parts.append(f"Thanks for posting '{title}' — I've reviewed the details and I'm confident I can help.")
        parts.append("")
        
        # Relevant experience
        if matched_skills:
            skills_str = ", ".join(matched_skills[:5])
            parts.append(f"My background includes {skills_str}, which directly match what you're looking for.")
            parts.append("")
        
        # Address specific requirements
        if key_requirements:
            parts.append("Based on your requirements, here's how I'll approach this:")
            for i, req in enumerate(key_requirements[:4], 1):
                parts.append(f"  {i}. {req.capitalize()}")
            parts.append("")
        
        # Deliverables commitment
        if deliverables:
            parts.append("What I'll deliver:")
            for i, deliv in enumerate(deliverables[:3], 1):
                parts.append(f"  • {deliv}")
            parts.append("")
        
        # Tools and process
        if tools:
            tools_str = ", ".join(tools[:4])
            parts.append(f"I use {tools_str} regularly, so the work will be efficient and accurate.")
            parts.append("")
        
        # Availability and terms
        parts.append(f"I'm available {self.user_availability.lower()} and can start right away.")
        
        if is_hourly:
            min_rate = self.hourly_range.get("min", 5)
            max_rate = self.hourly_range.get("max", 25)
            currency = self.hourly_range.get("currency", "USD")
            parts.append(f"My rate is {currency} {min_rate}-{max_rate}/hour depending on complexity.")
        elif is_fixed:
            parts.append("I'm happy to work within your budget — just let me know the scope.")
        
        parts.append("")
        
        # Questions
        questions = [
            "Do you have a sample file or template I should follow?",
            "What's your preferred timeline for completion?",
            "Are there any specific formatting guidelines I should know about?"
        ]
        parts.append("A couple of quick questions:")
        for q in questions[:2]:
            parts.append(f"  • {q}")
        parts.append("")
        
        # Closing
        parts.append("I take pride in clean, accurate work and clear communication. Happy to discuss further!")
        parts.append("")
        parts.append("Best regards,")

        return "\n".join(parts)
    
    def _generate_ultra_short_proposal(self, job: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate ultra-short proposal (1-2 sentences)."""
        title = analysis["title"]
        matched_skills = analysis["matched_skills"]
        client_name = analysis["client_name"]
        
        skill_str = f" with {', '.join(matched_skills[:3])}" if matched_skills else ""
        
        templates = [
            f"Hi {client_name}, I can help with '{title}'{skill_str}. Available to start immediately — let me know if you'd like to discuss.",
            f"Hi {client_name}, interested in your '{title}' project. I have experience in {skill_str.strip() or 'this area'} and can deliver quickly. Questions welcome!",
            f"Hi {client_name}, saw your '{title}' post and I'm a good fit{skill_str}. Ready to start — what's your timeline?",
            f"Hi {client_name}, I can handle your '{title}' project{skill_str}. Fast, accurate work. Happy to share relevant samples."
        ]
        
        return random.choice(templates)
    
    def _proposal_to_dict(self, proposal: ProposalSet) -> Dict[str, Any]:
        """Convert ProposalSet to dictionary."""
        return {
            "job_id": proposal.job_id,
            "short": proposal.short,
            "normal": proposal.normal,
            "ultra_short": proposal.ultra_short,
            "generated_at": proposal.generated_at.isoformat()
        }


class ProposalService:
    """Service for generating and managing proposals."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.agent = ProposalAgent(db_manager=db_manager)
    
    async def generate_proposals(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate proposals for jobs."""
        result = await self.agent.run(jobs=jobs)
        
        if self.db_manager and result.success:
            for proposal in result.data["proposals"]:
                job = self.db_manager.repositories.jobs.get_by_job_id(proposal["job_id"])
                if job:
                    self.db_manager.repositories.jobs.update(job.id, {
                        "proposal_short": proposal["short"],
                        "proposal_normal": proposal["normal"],
                        "proposal_ultra_short": proposal["ultra_short"]
                    })
                    
                    # Store in proposals table
                    for prop_type, content in [
                        ("short", proposal["short"]),
                        ("normal", proposal["normal"]),
                        ("ultra_short", proposal["ultra_short"])
                    ]:
                        self.db_manager.repositories.proposals.create({
                            "job_id": job.id,
                            "proposal_type": prop_type,
                            "content": content,
                            "generated_at": proposal["generated_at"]
                        })
        
        return result.data["proposals"]