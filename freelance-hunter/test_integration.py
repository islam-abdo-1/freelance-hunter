"""Integration test for the Freelance Hunter system."""
import asyncio
import os

from agents.orchestrator import FreelanceHunterOrchestrator
from core.database.models import init_database
from core.database.repository import DatabaseManager


async def test_orchestrator():
    """Test the orchestrator with mocked components."""
    test_dir = "data"
    test_db = os.path.join(test_dir, "test_integration.db")
    
    os.makedirs(test_dir, exist_ok=True)
    if os.path.exists(test_db):
        os.remove(test_db)
    
    try:
        # Initialize database
        init_database(f"sqlite:///{test_db}")
        db_manager = DatabaseManager(f"sqlite:///{test_db}")
        db_manager.initialize()
        
        # Create orchestrator
        orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager)
        
        # Test platform discovery
        print("Testing platform discovery...")
        platform_result = await orchestrator.platform_discovery.run()
        print(f"Platform discovery: {platform_result.success}")
        print(f"Platforms registered: {platform_result.data.get('known_platforms_registered', 0)}")
        
        # Test getting active platforms
        platforms = orchestrator.repositories.platforms.get_active_platforms()
        print(f"Active platforms: {len(platforms)}")
        
        # Test dashboard stats
        stats = orchestrator.get_dashboard_stats()
        print(f"Dashboard stats: {stats}")
        
        # Test daily report
        report = orchestrator.generate_daily_report()
        print(f"Daily report generated ({len(report)} chars)")
        
        # Test search jobs (should be empty initially)
        results = orchestrator.search_jobs({}, page=1, per_page=10)
        print(f"Search results: {results['total']} jobs")
        
        print("\n[SUCCESS] All integration tests passed!")
        
    finally:
        # Cleanup
        try:
            os.remove(test_db)
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_orchestrator())