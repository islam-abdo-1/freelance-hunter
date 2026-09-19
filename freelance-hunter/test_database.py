from core.database.models import init_database, Platform, Client, Job, MatchLevel, VerificationStatus, RiskLevel, JobStatus
from core.database.repository import DatabaseManager, Repositories
from core.config.loader import get_config
from core.utils import parse_date
import os
from datetime import datetime

# Clean up test database
test_dir = "data"
test_db = os.path.join(test_dir, "test_freelance_hunter.db")

# Create data directory
os.makedirs(test_dir, exist_ok=True)

if os.path.exists(test_db):
    os.remove(test_db)

# Initialize
init_database(f"sqlite:///{test_db}")
db_manager = DatabaseManager(f"sqlite:///{test_db}")
db_manager.initialize()
repos = Repositories(db_manager)

print("Database initialized successfully")

# Test Platform
platform_data = {
    "name": "Test Platform",
    "url": "https://test.com",
    "jobs_url": "https://test.com/jobs",
    "search_url": "https://test.com/search?q={query}",
    "category": "test",
    "country_region": "global",
    "login_required": False,
    "public_access": True,
    "notes": "Test platform"
}
platform = repos.platforms.create_or_update(platform_data)
print(f"Created platform: {platform.name} (ID: {platform.id})")

# Test Client
client_data = {
    "platform_id": platform.id,
    "platform_client_id": "client_123",
    "display_name": "Test Client",
    "company_name": "Test Corp",
    "country": "USA",
    "rating": 4.8,
    "review_count": 25,
    "hire_history": 10,
    "total_spent": 5000.0,
    "payment_verified": True
}
client = repos.clients.create_or_update(client_data)
print(f"Created client: {client.display_name} (ID: {client.id})")

# Test Job - convert date strings to datetime objects
job_data = {
    "job_id": "test_job_123",
    "platform_id": platform.id,
    "client_id": client.id,
    "platform_url": platform_data["url"],
    "job_url": "https://test.com/jobs/123",
    "title": "Test Data Entry Job",
    "full_description": "We need someone to enter data from PDFs into Excel spreadsheets. Must have Excel experience.",
    "short_summary": "Data entry from PDF to Excel",
    "category": "data_entry",
    "sub_category": "excel",
    "matched_skills": ["Excel", "Data Entry"],
    "date_posted": parse_date("2024-01-15T10:30:00Z"),
    "time_since_posted": "2 hours ago",
    "budget": "$100",
    "budget_min": 100.0,
    "budget_max": 100.0,
    "currency": "USD",
    "fixed_price_or_hourly": "fixed",
    "experience_level": "Entry",
    "required_skills": ["Excel", "Data Entry"],
    "client_name": client.display_name,
    "client_country": client_data["country"],
    "client_rating": client_data["rating"],
    "client_review_count": client_data["review_count"],
    "client_hire_history": client_data["hire_history"],
    "client_total_spent": client_data["total_spent"],
    "client_payment_status": "verified",
    "verification_status": VerificationStatus.VERIFIED,
    "match_level": MatchLevel.GOOD_MATCH,
    "risk_level": RiskLevel.LOW,
    "score": 75.5,
    "score_breakdown": {"skill_match": 25, "recency": 18, "beginner_accessibility": 12, "budget_value": 8, "client_quality": 9, "competition": 4, "clarity": 4, "ease": 4},
    "match_reason": "Matches your skills: Excel, Data Entry. Posted very recently. Beginner-friendly requirements.",
    "source_agent": "data_entry_agent",
    "status": JobStatus.NEW,
    "discovered_at": datetime.utcnow()
}
job = repos.jobs.create(job_data)
print(f"Created job: (ID: {job.id}, job_id: {job.job_id})")

# Test search
results = repos.jobs.search_jobs({"category": "data_entry"}, page=1, per_page=10)
print(f"Search results: {results['total']} jobs found")

# Test stats
stats = repos.jobs.get_stats()
print(f"Stats: {stats}")

# Test recent jobs
recent = repos.jobs.get_recent_jobs(hours=24, limit=10)
print(f"Recent jobs: {len(recent)}")

print("\nAll database tests passed!")

# Cleanup
os.remove(test_db)
print("Test database cleaned up")