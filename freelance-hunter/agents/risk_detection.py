"""
Risk Detection Agent - Identifies red flags and risks in job listings.
"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from core.config.loader import get_config

from .base import AgentResult, BaseAgent

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class RedFlag:
    """Detected red flag."""
    flag_type: str
    severity: RiskLevel
    description: str
    evidence: str
    detected_at: datetime


@dataclass
class RiskAssessment:
    """Complete risk assessment for a job."""
    job_id: str
    overall_risk: RiskLevel
    red_flags: list[RedFlag]
    risk_score: float  # 0-100 (higher = riskier)
    summary: str


class RiskDetectionAgent(BaseAgent):
    """Agent that detects red flags and assesses risk in job listings."""
    
    def __init__(self, config: dict[str, Any] = None, db_manager=None):
        super().__init__("risk_detection_agent", config, db_manager)
        self.config = config or get_config()._config
        self.risk_config = self.config.get("risk_detection", {})
        
        # Red flag patterns with severity
        self.red_flag_patterns = self._build_patterns()
        
        # Budget thresholds for "too good to be true"
        self.suspicious_budget_thresholds = {
            "data_entry_hourly_max": 50,  # $50/hr for data entry is suspicious
            "data_entry_fixed_max": 500,  # $500 for simple data entry
            "typing_hourly_max": 40,
            "conversion_hourly_max": 60,
            "admin_hourly_max": 45
        }
    
    def _build_patterns(self) -> dict[str, dict[str, Any]]:
        """Build red flag detection patterns."""
        return {
            "unrealistic_promises": {
                "patterns": [
                    r"earn\s+\$?\d{3,}\s*(?:per|/)\s*(?:day|week|month)",
                    r"make\s+\$?\d{3,}\s*(?:per|/)\s*(?:day|week|month)",
                    r"\$?\d{3,}\s*(?:per|/)\s*(?:day|week|month)\s*(?:guaranteed|easy)",
                    r"get rich|financial freedom|passive income",
                    r"no work|autopilot|while you sleep"
                ],
                "severity": RiskLevel.HIGH,
                "description": "Unrealistic earnings promises"
            },
            "payment_before_start": {
                "patterns": [
                    r"pay\s+(?:to|for)\s+(?:start|work|access|training)",
                    r"deposit\s+required",
                    r"upfront\s+(?:payment|fee|charge)",
                    r"registration\s+fee",
                    r"membership\s+fee",
                    r"pay\s+before"
                ],
                "severity": RiskLevel.CRITICAL,
                "description": "Requests payment before starting work"
            },
            "crypto_only": {
                "patterns": [
                    r"(?:only|exclusively)\s+(?:crypto|bitcoin|ethereum|usdt|bnb)",
                    r"pay\s+(?:in|with)\s+(?:crypto|bitcoin|ethereum)",
                    r"wallet\s+address\s+required",
                    r"blockchain\s+payment"
                ],
                "severity": RiskLevel.HIGH,
                "description": "Cryptocurrency-only payment requests"
            },
            "request_passwords": {
                "patterns": [
                    r"(?:share|give|provide|send)\s+(?:your|the)\s+(?:password|login|credentials)",
                    r"account\s+(?:access|login|credentials)",
                    r"sign\s+in\s+as\s+me",
                    r"remote\s+access\s+to\s+(?:my|your)\s+(?:computer|account)",
                    r"teamviewer|anydesk|remote\s+desktop"
                ],
                "severity": RiskLevel.CRITICAL,
                "description": "Requests for passwords or account access"
            },
            "external_communication": {
                "patterns": [
                    r"contact\s+me\s+(?:on|at|via)\s+(?:telegram|whatsapp|skype|discord|email)",
                    r"(?:telegram|whatsapp|skype|discord)\s*[:\-]?\s*@?\w+",
                    r"move\s+to\s+(?:telegram|whatsapp|skype|discord)",
                    r"chat\s+on\s+(?:telegram|whatsapp|skype|discord)",
                    r"my\s+(?:telegram|whatsapp|skype)\s+is"
                ],
                "severity": RiskLevel.MEDIUM,
                "description": "Requests to move communication off-platform"
            },
            "suspicious_links": {
                "patterns": [
                    r"(?:click|visit|go to)\s+(?:here|this link|link below)",
                    r"https?://(?:bit\.ly|tinyurl|t\.co|short\.link|rebrand\.ly)",
                    r"download\s+(?:from|here)\s*[:\-]?\s*https?://",
                    r"visit\s+(?:my|our)\s+(?:website|site|page)\s+at"
                ],
                "severity": RiskLevel.MEDIUM,
                "description": "Suspicious external links"
            },
            "impossible_deadline": {
                "patterns": [
                    r"(?:urgent|asap|immediate|right now|today)\s*(?:start|need|required)",
                    r"(?:within|in)\s+(?:1|2|3|few)\s*(?:hour|minute)s?",
                    r"deadline\s+(?:today|tomorrow|asap)",
                    r"need\s+(?:this|it)\s+(?:done|finished)\s+(?:today|now|asap)"
                ],
                "severity": RiskLevel.MEDIUM,
                "description": "Impossibly short deadlines"
            },
            "extremely_low_pay": {
                "patterns": [
                    r"\$?[1-4](?:\.\d{2})?\s*(?:per|/)\s*(?:hour|hr)",
                    r"\$?[1-9]\s*(?:per|/)\s*(?:hour|hr)\s*(?:for|data entry|typing)",
                    r"total\s+budget\s+\$?[1-9]\d{0,2}\s*(?:for|data entry|typing|conversion)",
                    r"fixed\s+price\s+\$?[1-9]\d{0,2}\s*(?:for|data entry)"
                ],
                "severity": RiskLevel.MEDIUM,
                "description": "Extremely low payment for workload"
            },
            "prohibited_work": {
                "patterns": [
                    r"(?:bypass|hack|crack|scrape|steal|illegal|unauthorized)",
                    r"(?:fake|fraud|scam|phishing|spam|bot|automat)",
                    r"(?:buy|sell)\s+(?:accounts|followers|reviews|likes)",
                    r"click\s+fraud|ad\s+fraud",
                    r"carding|fraud|money\s+launder"
                ],
                "severity": RiskLevel.CRITICAL,
                "description": "Prohibited or illegal work"
            },
            "platform_violation": {
                "patterns": [
                    r"outside\s+(?:upwork|freelancer|platform|marketplace)",
                    r"direct\s+(?:payment|contract|hire)",
                    r"off\s+(?:platform|site|marketplace)",
                    r"bypass\s+(?:fees|platform)",
                    r"private\s+(?:deal|contract|payment)"
                ],
                "severity": RiskLevel.HIGH,
                "description": "Attempts to bypass platform rules"
            },
            "vague_description": {
                "patterns": [
                    r"^details\s+(?:in|via)\s+(?:chat|message|pm|dm)",
                    r"will\s+explain\s+(?:in|via)\s+(?:chat|message|pm|dm)",
                    r"contact\s+me\s+for\s+(?:details|more info)",
                    r"more\s+details\s+(?:in|via)\s+(?:chat|message|pm|dm)"
                ],
                "severity": RiskLevel.LOW,
                "description": "Vague description, details only in private chat"
            },
            "identity_theft_risk": {
                "patterns": [
                    r"(?:ssn|social security|passport|id card|driver.?s license)",
                    r"bank\s+(?:account|details|statement)",
                    r"credit\s+card\s+(?:number|details)",
                    r"personal\s+(?:information|data|details)"
                ],
                "severity": RiskLevel.CRITICAL,
                "description": "Requests for sensitive personal information"
            }
        }
    
    async def execute(self, **kwargs) -> AgentResult:
        """Execute risk detection on jobs."""
        jobs = kwargs.get("jobs", [])
        
        assessments = []
        for job in jobs:
            assessment = self._assess_risk(job)
            assessments.append(self._assessment_to_dict(assessment))
        
        # Count by risk level
        counts = {level.value: 0 for level in RiskLevel}
        for a in assessments:
            counts[a["overall_risk"]] += 1
        
        return AgentResult(
            success=True,
            data={
                "assessments": assessments,
                "summary": counts
            },
            items_found=len(jobs),
            items_processed=len(assessments)
        )
    
    def _assess_risk(self, job: dict[str, Any]) -> RiskAssessment:
        """Assess risk for a single job."""
        job_id = job.get("job_id", "unknown")
        red_flags = []
        
        # Combine text for analysis
        full_text = f"{job.get('title', '')} {job.get('full_description', '')}".lower()
        client_name = job.get("client_name", "").lower()
        
        # Check each pattern category
        for flag_type, config in self.red_flag_patterns.items():
            for pattern in config["patterns"]:
                matches = re.findall(pattern, full_text, re.IGNORECASE)
                if matches:
                    # Get context around match
                    evidence = self._get_evidence(full_text, pattern)
                    red_flags.append(RedFlag(
                        flag_type=flag_type,
                        severity=config["severity"],
                        description=config["description"],
                        evidence=evidence,
                        detected_at=datetime.utcnow()
                    ))
                    break  # One match per category is enough
        
        # Budget-based checks
        budget_flags = self._check_budget_red_flags(job)
        red_flags.extend(budget_flags)
        
        # Client-based checks
        client_flags = self._check_client_red_flags(job)
        red_flags.extend(client_flags)
        
        # Calculate overall risk
        overall_risk, risk_score = self._calculate_overall_risk(red_flags)
        
        # Generate summary
        summary = self._generate_summary(red_flags, overall_risk)
        
        return RiskAssessment(
            job_id=job_id,
            overall_risk=overall_risk,
            red_flags=red_flags,
            risk_score=risk_score,
            summary=summary
        )
    
    def _get_evidence(self, text: str, pattern: str) -> str:
        """Extract context around a pattern match."""
        import re
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return ""
        
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 100)
        return "..." + text[start:end] + "..."
    
    def _check_budget_red_flags(self, job: dict[str, Any]) -> list[RedFlag]:
        """Check for budget-related red flags."""
        flags = []
        
        budget_min = job.get("budget_min")
        budget_max = job.get("budget_max")
        job_type = job.get("fixed_price_or_hourly", "not_specified")
        category = job.get("category", "").lower()
        
        if budget_min is None:
            return flags
        
        # Determine category thresholds
        if "data_entry" in category or "admin" in category:
            hourly_max = self.suspicious_budget_thresholds["data_entry_hourly_max"]
            fixed_max = self.suspicious_budget_thresholds["data_entry_fixed_max"]
        elif "conversion" in category or "pdf" in category:
            hourly_max = self.suspicious_budget_thresholds["conversion_hourly_max"]
            fixed_max = 300
        elif "typing" in category or "transcription" in category:
            hourly_max = self.suspicious_budget_thresholds["typing_hourly_max"]
            fixed_max = 200
        else:
            hourly_max = 100
            fixed_max = 1000
        
        if job_type == "hourly":
            if budget_min > hourly_max:
                flags.append(RedFlag(
                    flag_type="suspiciously_high_pay",
                    severity=RiskLevel.MEDIUM,
                    description=f"Hourly rate ${budget_min} unusually high for {category}",
                    evidence=f"Budget: ${budget_min}/hr, Category: {category}",
                    detected_at=datetime.utcnow()
                ))
            elif budget_min < 3:  # Very low
                flags.append(RedFlag(
                    flag_type="extremely_low_pay",
                    severity=RiskLevel.MEDIUM,
                    description=f"Hourly rate ${budget_min} extremely low",
                    evidence=f"Budget: ${budget_min}/hr",
                    detected_at=datetime.utcnow()
                ))
        elif job_type == "fixed":
            if budget_max > fixed_max:
                flags.append(RedFlag(
                    flag_type="suspiciously_high_pay",
                    severity=RiskLevel.MEDIUM,
                    description=f"Fixed price ${budget_max} unusually high for {category}",
                    evidence=f"Budget: ${budget_max} fixed, Category: {category}",
                    detected_at=datetime.utcnow()
                ))
        
        return flags
    
    def _check_client_red_flags(self, job: dict[str, Any]) -> list[RedFlag]:
        """Check for client-related red flags."""
        flags = []
        
        # New client with high budget
        hire_history = job.get("client_hire_history", 0)
        total_spent = job.get("client_total_spent", 0)
        budget_max = job.get("budget_max", 0)
        
        if hire_history == 0 and total_spent == 0 and budget_max > 500:
            flags.append(RedFlag(
                flag_type="new_client_high_budget",
                severity=RiskLevel.MEDIUM,
                description="New client with no history offering high budget",
                evidence=f"Hire history: {hire_history}, Total spent: ${total_spent}, Budget: ${budget_max}",
                detected_at=datetime.utcnow()
            ))
        
        # Zero rating with reviews
        rating = job.get("client_rating")
        review_count = job.get("client_review_count", 0)
        if rating is not None and rating == 0 and review_count > 0:
            flags.append(RedFlag(
                flag_type="zero_rating_with_reviews",
                severity=RiskLevel.LOW,
                description="Client has reviews but zero rating",
                evidence=f"Rating: {rating}, Reviews: {review_count}",
                detected_at=datetime.utcnow()
            ))
        
        # Unverified payment
        payment_status = job.get("client_payment_status", "").lower()
        if payment_status in ["unverified", "not verified", "pending"]:
            flags.append(RedFlag(
                flag_type="unverified_payment",
                severity=RiskLevel.LOW,
                description="Client payment method not verified",
                evidence=f"Payment status: {payment_status}",
                detected_at=datetime.utcnow()
            ))
        
        return flags
    
    def _calculate_overall_risk(self, red_flags: list[RedFlag]) -> tuple[RiskLevel, float]:
        """Calculate overall risk level and score."""
        if not red_flags:
            return RiskLevel.LOW, 0.0
        
        # Severity weights
        severity_weights = {
            RiskLevel.CRITICAL: 30,
            RiskLevel.HIGH: 20,
            RiskLevel.MEDIUM: 10,
            RiskLevel.LOW: 3
        }
        
        # Count flags by severity
        severity_counts = {level: 0 for level in RiskLevel}
        for flag in red_flags:
            severity_counts[flag.severity] += 1
        
        # Calculate score
        score = sum(
            severity_counts[level] * severity_weights[level]
            for level in RiskLevel
        )
        
        # Cap at 100
        score = min(score, 100)
        
        # Determine overall level
        if severity_counts[RiskLevel.CRITICAL] > 0:
            return RiskLevel.CRITICAL, score
        elif severity_counts[RiskLevel.HIGH] >= 2 or severity_counts[RiskLevel.HIGH] >= 1 or severity_counts[RiskLevel.MEDIUM] >= 3:
            return RiskLevel.HIGH, score
        elif severity_counts[RiskLevel.MEDIUM] >= 1:
            return RiskLevel.MEDIUM, score
        else:
            return RiskLevel.LOW, score
    
    def _generate_summary(self, red_flags: list[RedFlag], overall_risk: RiskLevel) -> str:
        """Generate human-readable risk summary."""
        if not red_flags:
            return "No red flags detected. Job appears legitimate."
        
        parts = [f"Overall risk: {overall_risk.value}. "]
        
        # Group by severity
        by_severity = {}
        for flag in red_flags:
            if flag.severity not in by_severity:
                by_severity[flag.severity] = []
            by_severity[flag.severity].append(flag)
        
        severity_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        for severity in severity_order:
            if severity in by_severity:
                flags = by_severity[severity]
                parts.append(f"\n{severity.value}:")
                for flag in flags[:3]:  # Limit to 3 per severity
                    parts.append(f"  • {flag.description}")
        
        return "".join(parts)
    
    def _assessment_to_dict(self, assessment: RiskAssessment) -> dict[str, Any]:
        """Convert RiskAssessment to dictionary."""
        return {
            "job_id": assessment.job_id,
            "overall_risk": assessment.overall_risk.value,
            "risk_score": assessment.risk_score,
            "summary": assessment.summary,
            "red_flags": [
                {
                    "flag_type": flag.flag_type,
                    "severity": flag.severity.value,
                    "description": flag.description,
                    "evidence": flag.evidence,
                    "detected_at": flag.detected_at.isoformat()
                }
                for flag in assessment.red_flags
            ]
        }


class RiskDetectionService:
    """Service for running risk detection."""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.agent = RiskDetectionAgent(db_manager=db_manager)
    
    async def assess_risks(self, jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Assess risks for jobs and update database."""
        result = await self.agent.run(jobs=jobs)
        
        if self.db_manager and result.success:
            for assessment in result.data["assessments"]:
                job = self.db_manager.repositories.jobs.get_by_job_id(assessment["job_id"])
                if job:
                    self.db_manager.repositories.jobs.update(job.id, {
                        "risk_level": assessment["overall_risk"],
                        "risk_reasons": [f['flag_type'] for f in assessment["red_flags"]]
                    })
                    
                    # Store red flags
                    for flag in assessment["red_flags"]:
                        self.db_manager.repositories.red_flags.create({
                            "job_id": job.id,
                            "flag_type": flag["flag_type"],
                            "severity": flag["severity"],
                            "description": flag["description"],
                            "evidence": flag["evidence"],
                            "detected_at": flag["detected_at"]
                        })
        
        return result.data["assessments"]