"""
Job Matching Agent - Evaluates jobs against user profile and skills.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from core.config.loader import get_config
from core.utils import calculate_similarity, extract_skills_from_text

from .base import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class MatchLevel(str, Enum):
    EXCELLENT_MATCH = "EXCELLENT_MATCH"
    GOOD_MATCH = "GOOD_MATCH"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    WEAK_MATCH = "WEAK_MATCH"
    NOT_RELEVANT = "NOT_RELEVANT"


@dataclass
class MatchResult:
    """Result of job matching."""
    job_id: str
    match_level: MatchLevel
    match_score: float  # 0-100
    score_breakdown: dict[str, float]
    matched_skills: list[str]
    missing_skills: list[str]
    match_reason: str
    recommended: bool


class JobMatchingAgent(BaseAgent):
    """Agent that matches jobs against user profile."""
    
    def __init__(self, config: dict[str, Any] | None = None, db_manager=None):
        super().__init__("job_matching_agent", config, db_manager)
        self.config = config or get_config()._config
        self.matching_config = self.config.get("matching", {})
        self.scoring_config = self.config.get("scoring", {})
        self.profile = get_config().get_profile()
        
        # Weights for scoring components
        self.weights = {
            "skill_match": self.matching_config.get("skill_match_weight", 0.30),
            "recency": self.matching_config.get("recency_weight", 0.20),
            "beginner_accessibility": self.matching_config.get("beginner_accessibility_weight", 0.15),
            "budget_value": self.matching_config.get("budget_weight", 0.10),
            "client_quality": self.matching_config.get("client_quality_weight", 0.10),
            "competition": self.matching_config.get("competition_weight", 0.05),
            "clarity": self.matching_config.get("clarity_weight", 0.05),
            "ease": self.matching_config.get("ease_weight", 0.05)
        }
        
        # Max scores for each component
        self.max_scores = self.scoring_config.get("components", {
            "skill_match": 30,
            "recency": 20,
            "beginner_accessibility": 15,
            "budget_value": 10,
            "client_quality": 10,
            "competition": 5,
            "clarity": 5,
            "ease": 5
        })
        
        # User skills
        self.user_skills = [s.lower() for s in self.profile.get("skills", [])]
        self.user_languages = [l.lower() for l in self.profile.get("languages", [])]
        self.experience_level = self.profile.get("experience_level", "Beginner/Intermediate")
        self.hourly_range = self.profile.get("hourly_rate_range", {"min": 5, "max": 25, "currency": "USD"})
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute job matching."""
        jobs = kwargs.get("jobs", [])
        
        results = []
        for job in jobs:
            match_result = self._match_job(job)
            results.append(self._result_to_dict(match_result))
        
        # Count by match level
        counts = {level.value: 0 for level in MatchLevel}
        for r in results:
            counts[r["match_level"]] += 1
        
        return AgentResult(
            success=True,
            data={
                "matches": results,
                "summary": counts
            },
            items_found=len(jobs),
            items_processed=len(results)
        )
    
    def _match_job(self, job: dict[str, Any]) -> MatchResult:
        """Match a single job against user profile."""
        job_id = job.get("job_id", "unknown")
        
        # Calculate component scores
        skill_score, matched_skills, missing_skills = self._calculate_skill_match(job)
        recency_score = self._calculate_recency_score(job)
        beginner_score = self._calculate_beginner_accessibility(job)
        budget_score = self._calculate_budget_value(job)
        client_score = self._calculate_client_quality(job)
        competition_score = self._calculate_competition_score(job)
        clarity_score = self._calculate_clarity_score(job)
        ease_score = self._calculate_ease_score(job)
        
        # Weighted total
        breakdown = {
            "skill_match": skill_score,
            "recency": recency_score,
            "beginner_accessibility": beginner_score,
            "budget_value": budget_score,
            "client_quality": client_score,
            "competition": competition_score,
            "clarity": clarity_score,
            "ease": ease_score
        }
        
        total_score = sum(
            breakdown[comp] * self.weights.get(comp, 0) 
            for comp in breakdown
        )
        
        # Determine match level
        match_level = self._determine_match_level(total_score, skill_score)
        
        # Generate match reason
        match_reason = self._generate_match_reason(
            job, matched_skills, missing_skills, breakdown
        )
        
        # Determine if recommended
        recommended = match_level in [MatchLevel.EXCELLENT_MATCH, MatchLevel.GOOD_MATCH] and total_score >= 50
        
        return MatchResult(
            job_id=job_id,
            match_level=match_level,
            match_score=round(total_score, 1),
            score_breakdown={k: round(v, 1) for k, v in breakdown.items()},
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            match_reason=match_reason,
            recommended=recommended
        )
    
    def _calculate_skill_match(self, job: dict[str, Any]) -> tuple[float, list[str], list[str]]:
        """Calculate skill match score (0-30)."""
        # Get job skills
        job_skills = job.get("required_skills", [])
        if isinstance(job_skills, str):
            job_skills = [job_skills]
        
        job_matched_skills = job.get("matched_skills", [])
        if isinstance(job_matched_skills, str):
            job_matched_skills = [job_matched_skills]
        
        all_job_skills = list({s.lower() for s in job_skills + job_matched_skills})
        
        # Extract skills from description
        desc_skills = extract_skills_from_text(
            f"{job.get('title', '')} {job.get('full_description', '')}",
            self.profile.get("skills", [])
        )
        all_job_skills.extend([s.lower() for s in desc_skills])
        all_job_skills = list(set(all_job_skills))
        
        # Match against user skills
        matched = []
        for user_skill in self.user_skills:
            for job_skill in all_job_skills:
                if user_skill in job_skill or job_skill in user_skill:
                    matched.append(user_skill)
                    break
                # Fuzzy match
                if calculate_similarity(user_skill, job_skill) > 0.8:
                    matched.append(user_skill)
                    break
        
        matched = list(set(matched))
        missing = [s for s in all_job_skills if s not in [m.lower() for m in matched]]
        
        # Score based on match ratio
        if not all_job_skills:
            return 15.0, [], []  # Neutral if no skills specified
        
        match_ratio = len(matched) / max(len(all_job_skills), 1)
        score = match_ratio * self.max_scores["skill_match"]
        
        # Bonus for core skill matches
        core_skills = ["excel", "powerpoint", "word", "data entry", "pdf", "google sheets"]
        core_matches = sum(1 for m in matched if any(c in m for c in core_skills))
        score += min(core_matches * 2, 10)
        
        return min(score, self.max_scores["skill_match"]), matched, missing[:10]
    
    def _calculate_recency_score(self, job: dict[str, Any]) -> float:
        """Calculate recency score (0-20)."""
        date_posted = job.get("date_posted")
        if not date_posted:
            return 5.0  # Neutral for unknown date
        
        try:
            if isinstance(date_posted, str):
                from core.utils import parse_date
                date_posted = parse_date(date_posted)
            
            if not date_posted:
                return 5.0
            
            hours_ago = (datetime.utcnow() - date_posted).total_seconds() / 3600
            
            if hours_ago <= 24:
                return self.max_scores["recency"]  # 20
            elif hours_ago <= 72:
                return self.max_scores["recency"] * 0.8  # 16
            elif hours_ago <= 168:
                return self.max_scores["recency"] * 0.5  # 10
            elif hours_ago <= 720:
                return self.max_scores["recency"] * 0.2  # 4
            else:
                return 1.0
        except Exception:
            return 5.0
    
    def _calculate_beginner_accessibility(self, job: dict[str, Any]) -> float:
        """Calculate beginner accessibility score (0-15)."""
        score = self.max_scores["beginner_accessibility"]  # Start at max
        
        # Check experience level
        exp_level = job.get("experience_level", "").lower()
        if any(word in exp_level for word in ["expert", "senior", "lead", "principal", "architect"]):
            score -= 8
        elif any(word in exp_level for word in ["intermediate", "mid", "experienced"]):
            score -= 3
        elif any(word in exp_level for word in ["entry", "junior", "beginner", "fresh"]):
            score += 2
        
        # Check required skills for advanced technologies
        advanced_skills = [
            "machine learning", "ai", "deep learning", "tensorflow", "pytorch",
            "react", "vue", "angular", "node.js", "django", "flask",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
            "microservices", "distributed systems", "blockchain", "smart contracts"
        ]
        
        job_skills = job.get("required_skills", [])
        if isinstance(job_skills, str):
            job_skills = [job_skills]
        
        desc_skills = extract_skills_from_text(
            f"{job.get('title', '')} {job.get('full_description', '')}",
            advanced_skills
        )
        all_job_skills = [s.lower() for s in job_skills + desc_skills]
        
        advanced_count = sum(1 for s in all_job_skills if any(a in s for a in advanced_skills))
        score -= min(advanced_count * 2, 8)
        
        # Check for beginner-friendly keywords
        beginner_keywords = [
            "entry level", "beginner friendly", "no experience", "training provided",
            "willing to learn", "junior", "starter", "simple", "basic", "easy"
        ]
        text = f"{job.get('title', '')} {job.get('full_description', '')}".lower()
        beginner_bonus = sum(1 for kw in beginner_keywords if kw in text)
        score += min(beginner_bonus * 1.5, 5)
        
        return max(0, min(score, self.max_scores["beginner_accessibility"]))
    
    def _calculate_budget_value(self, job: dict[str, Any]) -> float:
        """Calculate budget value score (0-10)."""
        budget_min = job.get("budget_min")
        budget_max = job.get("budget_max")
        currency = job.get("currency", "USD")
        job_type = job.get("fixed_price_or_hourly", "not_specified")
        
        if budget_min is None:
            return 5.0  # Neutral for unspecified budget
        
        # Convert to USD if needed (simplified)
        usd_rate = 1.0
        if currency != "USD":
            # Would use real exchange rates in production
            rates = {"EUR": 1.1, "GBP": 1.3, "INR": 0.012, "EGP": 0.02, "AED": 0.27, "SAR": 0.27}
            usd_rate = rates.get(currency, 1.0)
        
        min_usd = budget_min * usd_rate
        budget_max * usd_rate if budget_max else min_usd
        
        if job_type == "hourly":
            # Hourly rate evaluation
            hourly_rate = min_usd
            user_min = self.hourly_range.get("min", 5)
            user_max = self.hourly_range.get("max", 25)
            
            if hourly_rate < user_min:
                return 2.0  # Too low
            elif hourly_rate <= user_max:
                return self.max_scores["budget_value"]  # Good range
            elif hourly_rate <= user_max * 2:
                return self.max_scores["budget_value"] * 0.7  # Above range but acceptable
            else:
                return self.max_scores["budget_value"] * 0.4  # High but possible
        else:
            # Fixed price - evaluate based on estimated effort
            effort = job.get("estimated_effort", "medium")
            duration = job.get("estimated_duration", "").lower()
            
            # Estimate hours
            if "hour" in duration:
                import re
                hours_match = re.search(r'(\d+)', duration)
                est_hours = int(hours_match.group(1)) if hours_match else 10
            elif "day" in duration:
                import re
                days_match = re.search(r'(\d+)', duration)
                est_hours = int(days_match.group(1)) * 8 if days_match else 40
            elif "week" in duration:
                import re
                weeks_match = re.search(r'(\d+)', duration)
                est_hours = int(weeks_match.group(1)) * 40 if weeks_match else 160
            else:
                # Estimate from effort
                effort_hours = {"low": 5, "medium": 20, "high": 80}
                est_hours = effort_hours.get(effort, 20)
            
            if est_hours > 0:
                implied_hourly = min_usd / est_hours
                user_min = self.hourly_range.get("min", 5)
                user_max = self.hourly_range.get("max", 25)
                
                if implied_hourly < user_min:
                    return 2.0
                elif implied_hourly <= user_max:
                    return self.max_scores["budget_value"]
                elif implied_hourly <= user_max * 2:
                    return self.max_scores["budget_value"] * 0.7
                else:
                    return self.max_scores["budget_value"] * 0.4
        
        return 5.0
    
    def _calculate_client_quality(self, job: dict[str, Any]) -> float:
        """Calculate client quality score (0-10)."""
        score = 5.0  # Base score
        
        # Rating
        rating = job.get("client_rating")
        if rating is not None:
            if rating >= 4.8:
                score += 3
            elif rating >= 4.5:
                score += 2
            elif rating >= 4.0:
                score += 1
            elif rating < 3.0:
                score -= 2
        
        # Review count
        reviews = job.get("client_review_count")
        if reviews is not None:
            if reviews >= 50:
                score += 2
            elif reviews >= 10:
                score += 1
            elif reviews == 0:
                score -= 1
        
        # Hire history
        hires = job.get("client_hire_history")
        if hires is not None:
            if hires >= 20:
                score += 2
            elif hires >= 5:
                score += 1
            elif hires == 0:
                score -= 1
        
        # Total spent
        spent = job.get("client_total_spent")
        if spent is not None:
            if spent >= 10000:
                score += 2
            elif spent >= 1000:
                score += 1
        
        # Payment verified
        if job.get("client_payment_status") in ["verified", "payment_verified"]:
            score += 1
        
        return max(0, min(score, self.max_scores["client_quality"]))
    
    def _calculate_competition_score(self, job: dict[str, Any]) -> float:
        """Calculate competition score (0-5). Lower competition = higher score."""
        proposals = job.get("proposals_count")
        job.get("hires_count")
        bids = job.get("bids_count")
        
        # Use available competition metric
        competition = proposals or bids or 0
        
        if competition == 0:
            return self.max_scores["competition"]  # 5 - No competition
        elif competition <= 5:
            return self.max_scores["competition"] * 0.8  # 4
        elif competition <= 15:
            return self.max_scores["competition"] * 0.5  # 2.5
        elif competition <= 30:
            return self.max_scores["competition"] * 0.2  # 1
        else:
            return 0.5  # High competition
    
    def _calculate_clarity_score(self, job: dict[str, Any]) -> float:
        """Calculate requirement clarity score (0-5)."""
        score = 2.5  # Base
        
        description = job.get("full_description", "")
        job.get("title", "")
        
        # Length indicates detail
        if len(description) > 1000:
            score += 1.5
        elif len(description) > 500:
            score += 1
        elif len(description) > 200:
            score += 0.5
        elif len(description) < 50:
            score -= 1
        
        # Has specific requirements
        req_keywords = ["must have", "required", "need", "should have", "experience with"]
        req_count = sum(1 for kw in req_keywords if kw in description.lower())
        score += min(req_count * 0.3, 1.5)
        
        # Has deliverables mentioned
        deliverable_keywords = ["deliver", "output", "result", "provide", "submit", "format"]
        if any(kw in description.lower() for kw in deliverable_keywords):
            score += 0.5
        
        return max(0, min(score, self.max_scores["clarity"]))
    
    def _calculate_ease_score(self, job: dict[str, Any]) -> float:
        """Calculate ease of delivery score (0-5)."""
        difficulty = job.get("potential_difficulty", "medium")
        effort = job.get("estimated_effort", "medium")
        
        difficulty_scores = {"easy": 5, "medium": 3, "hard": 1}
        effort_scores = {"low": 5, "medium": 3, "high": 1}
        
        diff_score = difficulty_scores.get(difficulty, 3)
        effort_score = effort_scores.get(effort, 3)
        
        # Average of both
        return (diff_score + effort_score) / 2
    
    def _determine_match_level(self, total_score: float, skill_score: float) -> MatchLevel:
        """Determine match level from scores."""
        # Skill score is most important
        if skill_score >= 25 and total_score >= 75:
            return MatchLevel.EXCELLENT_MATCH
        elif skill_score >= 20 and total_score >= 60:
            return MatchLevel.GOOD_MATCH
        elif skill_score >= 15 and total_score >= 45:
            return MatchLevel.POSSIBLE_MATCH
        elif skill_score >= 10 and total_score >= 30:
            return MatchLevel.WEAK_MATCH
        else:
            return MatchLevel.NOT_RELEVANT
    
    def _generate_match_reason(self, job: dict[str, Any], matched_skills: list[str],
                               missing_skills: list[str], breakdown: dict[str, float]) -> str:
        """Generate human-readable match reason."""
        reasons = []
        
        # Skill match
        if matched_skills:
            reasons.append(f"Matches your skills: {', '.join(matched_skills[:5])}")
        else:
            reasons.append("No direct skill matches found")
        
        # Recency
        recency = breakdown.get("recency", 0)
        if recency >= 16:
            reasons.append("Posted very recently (high priority)")
        elif recency >= 10:
            reasons.append("Posted within last 3 days")
        elif recency >= 4:
            reasons.append("Posted within last week")
        
        # Beginner accessibility
        beginner = breakdown.get("beginner_accessibility", 0)
        if beginner >= 12:
            reasons.append("Beginner-friendly requirements")
        elif beginner <= 5:
            reasons.append("May require advanced experience")
        
        # Budget
        budget = breakdown.get("budget_value", 0)
        if budget >= 8:
            reasons.append("Good budget for your rate range")
        elif budget <= 3:
            reasons.append("Budget may be below your expectations")
        
        # Client quality
        client = breakdown.get("client_quality", 0)
        if client >= 8:
            reasons.append("High-quality client with good history")
        elif client <= 3:
            reasons.append("New or unverified client")
        
        # Competition
        comp = breakdown.get("competition", 0)
        if comp >= 4:
            reasons.append("Low competition")
        elif comp <= 1:
            reasons.append("High competition")
        
        return ". ".join(reasons) + "."
    
    def _result_to_dict(self, result: MatchResult) -> dict[str, Any]:
        """Convert MatchResult to dictionary."""
        return {
            "job_id": result.job_id,
            "match_level": result.match_level.value,
            "match_score": result.match_score,
            "score_breakdown": result.score_breakdown,
            "matched_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
            "match_reason": result.match_reason,
            "recommended": result.recommended
        }


class MatchingService:
    """Service for running job matching."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.agent = JobMatchingAgent(db_manager=db_manager)
    
    async def match_jobs(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Match jobs and update database."""
        result = await self.agent.run(jobs=jobs)
        
        if self.db_manager and result.success:
            for match in result.data["matches"]:
                job = self.db_manager.repositories.jobs.get_by_job_id(match["job_id"])
                if job:
                    self.db_manager.repositories.jobs.update(job.id, {
                        "match_level": match["match_level"],
                        "score": match["match_score"],
                        "score_breakdown": match["score_breakdown"],
                        "matched_skills": match["matched_skills"],
                        "match_reason": match["match_reason"]
                    })
                    
                    # Store individual skill matches
                    for skill in match["matched_skills"]:
                        self.db_manager.repositories.job_matches.create_matches(job.id, [{
                            "skill_name": skill,
                            "match_score": 1.0,
                            "match_type": "exact"
                        }])
        
        return result.data["matches"]