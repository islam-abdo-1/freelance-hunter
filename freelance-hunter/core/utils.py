"""
Core utilities for Freelance Hunter.
"""
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


def generate_job_id(platform: str, url: str, title: str) -> str:
    """Generate a unique job ID from platform, URL, and title."""
    content = f"{platform}:{url}:{title}".lower().strip()
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    if not url:
        return ""
    
    parsed = urlparse(url.strip())
    
    # Remove common tracking parameters
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'ref', 'referrer', 'source', 'campaign', 'medium', 'gclid', 'fbclid',
        'mc_cid', 'mc_eid', '_ga', '_gl'
    }
    
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_params}
    
    # Rebuild query string
    new_query = "&".join(f"{k}={v[0]}" for k, v in sorted(filtered_params.items()))
    
    # Normalize path (remove trailing slash)
    path = parsed.path.rstrip('/')
    
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{path}"
    if new_query:
        normalized += f"?{new_query}"
    
    return normalized


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc.lower().replace('www.', '')
    except Exception:
        return ""


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity ratio between two texts."""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower().strip(), text2.lower().strip()).ratio()


def is_duplicate_job(job1: dict[str, Any], job2: dict[str, Any], threshold: float = 0.85) -> tuple[bool, str, float]:
    """
    Check if two jobs are duplicates.
    Returns (is_duplicate, reason, similarity_score)
    """
    # Check URL first (most reliable)
    url1 = normalize_url(job1.get('job_url', '') or job1.get('platform_url', ''))
    url2 = normalize_url(job2.get('job_url', '') or job2.get('platform_url', ''))
    
    if url1 and url2 and url1 == url2:
        return True, "url", 1.0
    
    # Check title similarity
    title1 = job1.get('title', '')
    title2 = job2.get('title', '')
    title_sim = calculate_similarity(title1, title2)
    
    if title_sim >= threshold:
        # Check other fields for confirmation
        client1 = job1.get('client_name', '') or ''
        client2 = job2.get('client_name', '') or ''
        client_sim = calculate_similarity(client1, client2)
        
        desc1 = job1.get('full_description', '') or ''
        desc2 = job2.get('full_description', '') or ''
        desc_sim = calculate_similarity(desc1[:500], desc2[:500])  # First 500 chars
        
        # Weighted average
        weighted_sim = (title_sim * 0.5) + (client_sim * 0.2) + (desc_sim * 0.3)
        
        if weighted_sim >= threshold:
            if title_sim >= 0.95:
                return True, "title", weighted_sim
            elif client_sim >= 0.9:
                return True, "client", weighted_sim
            elif desc_sim >= 0.9:
                return True, "description", weighted_sim
            else:
                return True, "combined", weighted_sim
    
    # Check platform and date
    if job1.get('platform') == job2.get('platform'):
        date1 = job1.get('date_posted')
        date2 = job2.get('date_posted')
        if date1 and date2:
            if isinstance(date1, str):
                date1 = parse_date(date1)
            if isinstance(date2, str):
                date2 = parse_date(date2)
            if date1 and date2 and abs((date1 - date2).total_seconds()) < 3600:  # Within 1 hour
                if title_sim > 0.7:
                    return True, "date_title", title_sim
    
    return False, "", 0.0


def parse_date(date_str: str) -> datetime | None:
    """Parse various date formats."""
    if not date_str:
        return None
    
    # Common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
    ]
    
    # Try relative time parsing first
    relative = parse_relative_time(date_str)
    if relative:
        return relative
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    # Try to extract date from text
    return extract_date_from_text(date_str)


def parse_relative_time(text: str) -> datetime | None:
    """Parse relative time expressions like '2 hours ago', '3 days ago'."""
    text = text.lower().strip()
    now = datetime.utcnow()
    
    patterns = [
        (r'(\d+)\s*second', 'seconds'),
        (r'(\d+)\s*minute', 'minutes'),
        (r'(\d+)\s*hour', 'hours'),
        (r'(\d+)\s*day', 'days'),
        (r'(\d+)\s*week', 'weeks'),
        (r'(\d+)\s*month', 'days'),  # Approximate
        (r'just now|a moment ago', 'seconds'),
        (r'a minute ago', 'minutes'),
        (r'an hour ago', 'hours'),
        (r'yesterday', 'days'),
        (r'last week', 'weeks'),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, text)
        if match:
            if match.groups():
                value = int(match.group(1))
            else:
                value = 1
            
            if unit == 'seconds':
                return now - timedelta(seconds=value)
            elif unit == 'minutes':
                return now - timedelta(minutes=value)
            elif unit == 'hours':
                return now - timedelta(hours=value)
            elif unit == 'days':
                return now - timedelta(days=value)
            elif unit == 'weeks':
                return now - timedelta(weeks=value)
    
    return None


def extract_date_from_text(text: str) -> datetime | None:
    """Try to extract a date from arbitrary text."""
    # Look for date patterns
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{2}-\d{2}-\d{4})',
        r'(\w+ \d{1,2}, \d{4})',
        r'(\d{1,2} \w+ \d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return parse_date(match.group(1))
    
    return None


def format_time_ago(dt: datetime) -> str:
    """Format datetime as human-readable time ago."""
    if not dt:
        return "Unknown"
    
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 30:
        return dt.strftime("%Y-%m-%d")
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def extract_budget(text: str) -> dict[str, Any]:
    """Extract budget information from text."""
    result = {
        'budget': None,
        'budget_min': None,
        'budget_max': None,
        'currency': 'USD',
        'type': 'not_specified'
    }
    
    if not text:
        return result
    
    # Currency symbols
    currency_patterns = {
        r'\$': 'USD',
        r'€': 'EUR',
        r'£': 'GBP',
        r'₹': 'INR',
        r'AED': 'AED',
        r'SAR': 'SAR',
        r'EGP': 'EGP',
        r'USD': 'USD',
        r'EUR': 'EUR',
        r'GBP': 'GBP',
    }
    
    # Detect currency
    for pattern, currency in currency_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result['currency'] = currency
            break
    
    # Extract numbers
    # Pattern: $100, $100-$200, $100 to $200, Up to $500, etc.
    patterns = [
        r'[\$\€\£\₹]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*[\-\–\—\sto]+\s*[\$\€\£\₹]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'[\$\€\£\₹]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|EUR|GBP|USD|dollars?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            if isinstance(matches[0], tuple):
                # Range
                try:
                    min_val = float(matches[0][0].replace(',', ''))
                    max_val = float(matches[0][1].replace(',', ''))
                    result['budget_min'] = min_val
                    result['budget_max'] = max_val
                    result['budget'] = f"{result['currency']} {min_val:,.2f} - {max_val:,.2f}"
                    result['type'] = 'fixed' if min_val == max_val else 'range'
                    break
                except (ValueError, IndexError):
                    continue
            else:
                # Single value
                try:
                    val = float(matches[0].replace(',', ''))
                    result['budget_min'] = val
                    result['budget_max'] = val
                    result['budget'] = f"{result['currency']} {val:,.2f}"
                    result['type'] = 'fixed'
                    break
                except (ValueError, IndexError):
                    continue
    
    # Detect hourly vs fixed
    if re.search(r'per hour|/hr|hourly|rate', text, re.IGNORECASE):
        result['type'] = 'hourly'
    elif re.search(r'fixed|project|total|flat', text, re.IGNORECASE):
        result['type'] = 'fixed'
    
    return result


def extract_skills_from_text(text: str, skill_keywords: list[str]) -> list[str]:
    """Extract matching skills from text."""
    if not text:
        return []
    
    text_lower = text.lower()
    matched = []
    
    for skill in skill_keywords:
        # Use word boundaries for better matching
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            matched.append(skill)
    
    return matched


def categorize_job(title: str, description: str, categories: dict[str, list[str]]) -> tuple[str, str]:
    """Categorize job based on title and description."""
    text = f"{title} {description}".lower()
    
    best_category = "other"
    best_subcategory = "general"
    max_matches = 0
    
    for category, keywords in categories.items():
        matches = sum(1 for kw in keywords if kw.lower() in text)
        if matches > max_matches:
            max_matches = matches
            best_category = category
            # Find subcategory
            for kw in keywords:
                if kw.lower() in text:
                    best_subcategory = kw
                    break
    
    return best_category, best_subcategory


def estimate_difficulty(title: str, description: str, required_skills: list[str]) -> str:
    """Estimate job difficulty level."""
    text = f"{title} {description}".lower()
    
    # Advanced keywords
    advanced = ['advanced', 'expert', 'senior', 'complex', 'architecture', 'machine learning',
                'ai', 'algorithm', 'optimization', 'scalable', 'enterprise', 'migration',
                'integration', 'api development', 'custom', 'from scratch', 'framework']
    
    # Beginner keywords
    beginner = ['entry', 'beginner', 'simple', 'basic', 'easy', 'straightforward',
                'copy', 'paste', 'format', 'convert', 'organize', 'cleanup', 'entry level',
                'junior', 'assistant', 'support', 'data entry', 'typing', 'transcription']
    
    advanced_count = sum(1 for kw in advanced if kw in text)
    beginner_count = sum(1 for kw in beginner if kw in text)
    
    # Check required skills
    advanced_skills = ['machine learning', 'ai', 'deep learning', 'react', 'vue', 'angular',
                       'node.js', 'django', 'flask', 'aws', 'docker', 'kubernetes']
    
    skill_advanced = sum(1 for s in required_skills if any(a in s.lower() for a in advanced_skills))
    
    if advanced_count >= 2 or skill_advanced >= 1:
        return "hard"
    elif beginner_count >= 2 or advanced_count == 0:
        return "easy"
    else:
        return "medium"


def estimate_effort(title: str, description: str, budget_info: dict, duration: str) -> str:
    """Estimate effort required."""
    text = f"{title} {description}".lower()
    
    # Check for explicit duration
    if duration:
        duration_lower = duration.lower()
        if any(w in duration_lower for w in ['hour', 'hr']):
            return "low"
        elif any(w in duration_lower for w in ['day', 'week']):
            return "medium"
        elif any(w in duration_lower for w in ['month', 'ongoing']):
            return "high"
    
    # Check budget vs typical rates
    if budget_info.get('budget_min'):
        budget = budget_info['budget_min']
        if budget < 50:
            return "low"
        elif budget < 200:
            return "medium"
        else:
            return "high"
    
    # Keyword-based
    if any(w in text for w in ['quick', 'fast', 'urgent', 'asap', 'small', 'simple', 'minor']):
        return "low"
    elif any(w in text for w in ['large', 'extensive', 'comprehensive', 'full', 'complete', 'major']):
        return "high"
    
    return "medium"


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\[\]\/\%\$\@\#\&\*]', '', text)
    return text.strip()


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix


def is_likely_spam(title: str, description: str, client_info: dict | None = None) -> tuple[bool, list[str]]:
    """Check if job listing appears to be spam."""
    reasons = []
    text = f"{title} {description}".lower()
    
    spam_patterns = [
        (r'earn \$\d+ per (day|week|month)', "unrealistic earnings claim"),
        (r'work from home.*\$\d{3,}', "high pay for simple work"),
        (r'no experience.*high pay', "too good to be true"),
        (r'click here|visit link|telegram|whatsapp|skype', "external contact request"),
        (r'investment|deposit|payment required|pay to work', "payment required"),
        (r'crypto|bitcoin|ethereum|wallet', "crypto payment"),
        (r'urgent|immediate|asap.*hiring', "pressure tactics"),
        (r'guaranteed|risk.free|100%', "guarantees"),
        (r'data entry.*\$[5-9]\d{2,}|\$1[0-9]{3,}', "unrealistic data entry pay"),
    ]
    
    for pattern, reason in spam_patterns:
        if re.search(pattern, text):
            reasons.append(reason)
    
    # Check client info
    if client_info:
        if client_info.get('rating') == 0 and client_info.get('review_count') == 0:
            if client_info.get('total_spent', 0) == 0:
                reasons.append("new client with no history")
    
    return len(reasons) > 0, reasons


def validate_job_url(url: str, platform: str) -> bool:
    """Validate if URL looks like a legitimate job posting."""
    if not url:
        return False
    
    parsed = urlparse(url)
    parsed.netloc.lower()
    
    # Platform-specific validation
    platform_patterns = {
        'upwork': r'upwork\.com/(?:jobs|freelance)',
        'freelancer': r'freelancer\.com/(?:projects|jobs)',
        'peopleperhour': r'peopleperhour\.com/(?:job|freelance)',
        'guru': r'guru\.com/(?:jobs|projects)',
        'workana': r'workana\.com/(?:jobs|projects)',
        'contra': r'contra\.com/(?:jobs|projects)',
        'fiverr': r'fiverr\.com/(?:gigs|search)',
        'khamsat': r'khamsat\.com/(?:projects|services)',
        'mostaql': r'mostaql\.com/(?:projects|jobs)',
        'linkedin': r'linkedin\.com/jobs',
    }
    
    pattern = platform_patterns.get(platform.lower())
    if pattern and re.search(pattern, url):
        return True
    
    # Generic validation - should have path beyond domain
    return bool(parsed.path and len(parsed.path) > 1)


def load_json_file(filepath: str) -> dict[str, Any]:
    """Load JSON file safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return {}


def save_json_file(data: dict[str, Any], filepath: str):
    """Save JSON file safely."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")


def setup_logging(level: str = "INFO", log_file: str | None = None):
    """Setup logging configuration."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    handlers = [logging.StreamHandler()]
    if log_file:
        import os
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    # Reduce noise from libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)