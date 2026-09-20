#!/usr/bin/env python3
"""
Freelance Hunter - Main Entry Point
Multi-agent system for discovering and analyzing freelance job opportunities.
"""
import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.orchestrator import FreelanceHunterOrchestrator, run_pipeline
from core.config.loader import get_config
from core.database.models import init_database
from core.database.repository import DatabaseManager
from core.scheduler.scheduler import setup_default_scheduler
from exports.manager import export_jobs


# Setup logging
def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/freelance_hunter.log', encoding='utf-8')
        ]
    )
    # Reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)


async def run_scan(args):
    """Run a single scan."""
    print("Starting Freelance Hunter scan...")
    print(f"Priority: {args.priority} (1=24h, 2=72h, 3=7d, 4=30d)")
    print(f"Max pages per platform: {args.max_pages}")
    
    config = get_config()
    database_url = config.database_url
    
    # Initialize database
    init_database(database_url)
    db_manager = DatabaseManager(database_url)
    db_manager.initialize()
    
    # Run pipeline
    result = await run_pipeline(
        db_manager,
        priority=args.priority,
        max_pages=args.max_pages,
        triggered_by="cli"
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("SCAN RESULTS")
    print("=" * 60)
    print(f"Run ID: {result.run_id}")
    print(f"Status: {result.status}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    print(f"Platforms scanned: {result.platforms_scanned}")
    print(f"Queries executed: {result.queries_executed}")
    print(f"Pages scanned: {result.pages_scanned}")
    print(f"Raw jobs found: {result.raw_jobs_found}")
    print(f"Duplicates removed: {result.duplicates_removed}")
    print(f"Verified jobs: {result.verified_jobs}")
    print(f"Relevant jobs: {result.relevant_jobs}")
    print(f"High match jobs: {result.high_match_jobs}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors[:5]:
            print(f"  - {error}")
    
    # Export if requested
    if args.export:
        print(f"\nExporting to {args.export}...")
        # Would need to fetch jobs from DB for export
        print("Export functionality requires fetching jobs from database")
    
    if result.status == "failed":
        sys.exit(1)


async def run_scheduler(args):
    """Run the scheduler."""
    print("Starting Freelance Hunter scheduler...")
    
    config = get_config()
    database_url = config.database_url
    
    # Initialize database
    init_database(database_url)
    db_manager = DatabaseManager(database_url)
    db_manager.initialize()
    
    # Create orchestrator
    orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager)
    
    # Setup scheduler
    scheduler = await setup_default_scheduler(db_manager, orchestrator)
    
    print(f"Scheduler started with {len(scheduler.get_scheduled_jobs())} jobs")
    print("Press Ctrl+C to stop")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
            # Print status periodically
            jobs = scheduler.get_scheduled_jobs()
            for job in jobs.values():
                next_run = job.next_run.strftime("%Y-%m-%d %H:%M:%S") if job.next_run else "N/A"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {job.name}: next run at {next_run}")
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.stop()


async def show_dashboard_stats(args):
    """Show dashboard statistics."""
    config = get_config()
    database_url = config.database_url
    
    init_database(database_url)
    db_manager = DatabaseManager(database_url)
    db_manager.initialize()
    
    orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager)
    stats = orchestrator.get_dashboard_stats()
    
    print("\n" + "=" * 50)
    print("DASHBOARD STATISTICS")
    print("=" * 50)
    print(f"Total Jobs: {stats.get('total_jobs', 0)}")
    print(f"Verified Jobs: {stats.get('verified_jobs', 0)}")
    print(f"New Today: {stats.get('new_today', 0)}")
    print(f"High Match Jobs: {stats.get('high_match_jobs', 0)}")
    print(f"High Risk Jobs: {stats.get('high_risk_jobs', 0)}")
    print("\nPlatform Breakdown:")
    for platform, count in stats.get('platform_breakdown', {}).items():
        print(f"  {platform}: {count}")


async def generate_report(args):
    """Generate daily report."""
    config = get_config()
    database_url = config.database_url
    
    init_database(database_url)
    db_manager = DatabaseManager(database_url)
    db_manager.initialize()
    
    orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager)
    report = orchestrator.generate_daily_report()
    
    print(report)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nReport saved to {args.output}")


async def export_data(args):
    """Export jobs data."""
    config = get_config()
    database_url = config.database_url
    
    init_database(database_url)
    db_manager = DatabaseManager(database_url)
    db_manager.initialize()
    
    orchestrator = FreelanceHunterOrchestrator(db_manager=db_manager)
    
    # Get jobs with filters
    filters = {}
    if args.match_level:
        filters["match_level"] = args.match_level
    if args.min_score:
        filters["min_score"] = args.min_score
    if args.platform:
        # Would need platform ID lookup
        pass
    
    result = orchestrator.search_jobs(filters, page=1, per_page=args.limit)
    jobs = [orchestrator._job_to_dict(j) for j in result["jobs"]]
    
    if not jobs:
        print("No jobs found matching criteria")
        return
    
    filepath = export_jobs(jobs, format=args.format, filename=args.output)
    print(f"Exported {len(jobs)} jobs to {filepath}")


async def init_db(args):
    """Initialize database."""
    config = get_config()
    database_url = config.database_url
    
    print(f"Initializing database at {database_url}...")
    init_database(database_url)
    print("Database initialized successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Freelance Hunter - Multi-agent freelance job discovery system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scan                    # Run a scan (last 24h)
  python main.py scan --priority 2       # Run scan (last 72h)
  python main.py scheduler               # Run continuous scheduler
  python main.py stats                   # Show dashboard stats
  python main.py report                  # Generate daily report
  python main.py export --format xlsx    # Export to Excel
  python main.py init-db                 # Initialize database
        """
    )
    
    parser.add_argument(
        '--log-level', 
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Run a single job scan')
    scan_parser.add_argument('--priority', type=int, default=1, choices=[1,2,3,4],
                            help='Time window: 1=24h, 2=72h, 3=7d, 4=30d')
    scan_parser.add_argument('--max-pages', type=int, default=5,
                            help='Max pages per platform')
    scan_parser.add_argument('--export', choices=['csv', 'xlsx', 'json', 'md', 'html'],
                            help='Export results after scan')
    
    # Scheduler command
    subparsers.add_parser('scheduler', help='Run continuous scheduler')
    
    # Stats command
    subparsers.add_parser('stats', help='Show dashboard statistics')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate daily report')
    report_parser.add_argument('--output', help='Save report to file')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export jobs data')
    export_parser.add_argument('--format', default='csv', choices=['csv', 'xlsx', 'json', 'md', 'html'])
    export_parser.add_argument('--limit', type=int, default=1000, help='Max jobs to export')
    export_parser.add_argument('--match-level', help='Filter by match level')
    export_parser.add_argument('--min-score', type=float, help='Minimum match score')
    export_parser.add_argument('--platform', help='Filter by platform')
    export_parser.add_argument('--output', help='Output filename')
    
    # Init DB command
    subparsers.add_parser('init-db', help='Initialize database')
    
    # Config command
    subparsers.add_parser('config', help='Show current configuration')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run command
    if args.command == 'scan':
        asyncio.run(run_scan(args))
    elif args.command == 'scheduler':
        asyncio.run(run_scheduler(args))
    elif args.command == 'stats':
        asyncio.run(show_dashboard_stats(args))
    elif args.command == 'report':
        asyncio.run(generate_report(args))
    elif args.command == 'export':
        asyncio.run(export_data(args))
    elif args.command == 'init-db':
        asyncio.run(init_db(args))
    elif args.command == 'config':
        config = get_config()
        import json
        print(json.dumps(config._config, indent=2, default=str))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()