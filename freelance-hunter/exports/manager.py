"""
Export functionality for Freelance Hunter.
"""
import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Template

from core.config.loader import get_config

logger = logging.getLogger(__name__)


class ExportManager:
    """Manages export of jobs to various formats."""
    
    def __init__(self, output_dir: str = None):
        self.config = get_config()
        self.output_dir = Path(output_dir or self.config.get("export", {}).get("output_dir", "exports"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Column definitions for exports
        self.columns = [
            "platform", "title", "job_url", "date_posted", "budget", "currency",
            "category", "required_skills", "client_name", "client_country",
            "client_rating", "client_review_count", "client_hire_history",
            "client_total_spent", "client_payment_status",
            "match_score", "match_level", "risk_level",
            "short_summary", "why_it_matches", "proposal_normal",
            "discovered_at", "verification_status", "status"
        ]
    
    def export_jobs(self, jobs: list[dict[str, Any]], format: str = "csv", 
                    filename: str = None) -> str:
        """Export jobs to specified format."""
        if not jobs:
            logger.warning("No jobs to export")
            return ""
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"freelance_jobs_{timestamp}.{format}"
        filepath = self.output_dir / filename
        
        try:
            if format == "csv":
                return self._export_csv(jobs, filepath)
            elif format == "xlsx":
                return self._export_excel(jobs, filepath)
            elif format == "json":
                return self._export_json(jobs, filepath)
            elif format == "markdown":
                return self._export_markdown(jobs, filepath)
            elif format == "html":
                return self._export_html(jobs, filepath)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
    
    def _export_csv(self, jobs: list[dict[str, Any]], filepath: Path) -> str:
        """Export to CSV."""
        # Prepare rows
        rows = []
        for job in jobs:
            row = self._job_to_row(job)
            rows.append(row)
        
        # Write CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Exported {len(jobs)} jobs to CSV: {filepath}")
        return str(filepath)
    
    def _export_excel(self, jobs: list[dict[str, Any]], filepath: Path) -> str:
        """Export to Excel with formatting."""
        rows = []
        for job in jobs:
            row = self._job_to_row(job)
            rows.append(row)
        
        df = pd.DataFrame(rows, columns=self.columns)
        
        # Create Excel writer with formatting
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Jobs')
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Jobs']
            
            # Auto-fit columns
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Add header formatting
            from openpyxl.styles import Alignment, Font, PatternFill
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
            header_alignment = Alignment(horizontal="center", wrap_text=True)
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            
            # Freeze header row
            worksheet.freeze_panes = "A2"
            
            # Add filters
            worksheet.auto_filter.ref = worksheet.dimensions
        
        logger.info(f"Exported {len(jobs)} jobs to Excel: {filepath}")
        return str(filepath)
    
    def _export_json(self, jobs: list[dict[str, Any]], filepath: Path) -> str:
        """Export to JSON."""
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "total_jobs": len(jobs),
            "jobs": jobs
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Exported {len(jobs)} jobs to JSON: {filepath}")
        return str(filepath)
    
    def _export_markdown(self, jobs: list[dict[str, Any]], filepath: Path) -> str:
        """Export to Markdown."""
        lines = []
        lines.append("# Freelance Job Opportunities")
        lines.append(f"\nExported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        lines.append(f"Total Jobs: {len(jobs)}")
        lines.append("")
        
        # Group by match level
        match_levels = ["EXCELLENT_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH", "WEAK_MATCH", "NOT_RELEVANT"]
        
        for level in match_levels:
            level_jobs = [j for j in jobs if j.get("match_level") == level]
            if not level_jobs:
                continue
            
            lines.append(f"## {level.replace('_', ' ').title()} ({len(level_jobs)})")
            lines.append("")
            
            for i, job in enumerate(level_jobs, 1):
                lines.append(f"### {i}. {job.get('title', 'Untitled')}")
                lines.append("")
                lines.append(f"- **Platform:** {job.get('platform', 'N/A')}")
                lines.append(f"- **Posted:** {job.get('time_since_posted', 'N/A')}")
                lines.append(f"- **Budget:** {job.get('budget', 'N/A')}")
                lines.append(f"- **Client:** {job.get('client_name', 'N/A')} ({job.get('client_country', 'N/A')})")
                lines.append(f"- **Match Score:** {job.get('match_score', 0):.1f}")
                lines.append(f"- **Risk Level:** {job.get('risk_level', 'N/A')}")
                lines.append(f"- **Category:** {job.get('category', 'N/A')}")
                lines.append(f"- **Skills:** {', '.join(job.get('matched_skills', []))}")
                lines.append("")
                lines.append(f"**Summary:** {job.get('short_summary', 'N/A')[:300]}...")
                lines.append("")
                lines.append(f"**Why it matches:** {job.get('match_reason', 'N/A')}")
                lines.append("")
                lines.append("**Proposal:**")
                lines.append(f"> {job.get('proposal_normal', 'N/A')[:500]}...")
                lines.append("")
                lines.append(f"**Link:** [{job.get('job_url', '#')}]({job.get('job_url', '#')})")
                lines.append("")
                lines.append("---")
                lines.append("")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        
        logger.info(f"Exported {len(jobs)} jobs to Markdown: {filepath}")
        return str(filepath)
    
    def _export_html(self, jobs: list[dict[str, Any]], filepath: Path) -> str:
        """Export to HTML."""
        html_template = Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Freelance Job Opportunities - {{ export_date }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #1a1a2e; border-bottom: 3px solid #2F5496; padding-bottom: 10px; }
        .meta { color: #666; margin-bottom: 30px; }
        .job-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: #fafafa; }
        .job-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px; }
        .job-title { font-size: 1.3em; font-weight: 600; color: #1a1a2e; margin: 0; }
        .badges { display: flex; gap: 8px; flex-wrap: wrap; }
        .badge { padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: 500; }
        .badge-excellent { background: #e8f5e9; color: #2e7d32; }
        .badge-good { background: #e3f2fd; color: #1565c0; }
        .badge-possible { background: #fff3e0; color: #ef6c00; }
        .badge-weak { background: #fce4ec; color: #c2185b; }
        .badge-not-relevant { background: #f5f5f5; color: #757575; }
        .badge-low { background: #e8f5e9; color: #2e7d32; }
        .badge-medium { background: #fff3e0; color: #ef6c00; }
        .badge-high { background: #ffebee; color: #c62828; }
        .badge-critical { background: #fce4ec; color: #c2185b; }
        .job-meta { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .meta-item { background: white; padding: 10px; border-radius: 6px; border: 1px solid #eee; }
        .meta-label { font-size: 0.75em; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
        .meta-value { font-size: 1em; font-weight: 500; color: #333; }
        .job-description { background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #2F5496; margin-bottom: 15px; }
        .job-proposal { background: #f5f5f5; padding: 15px; border-radius: 6px; margin-bottom: 15px; }
        .proposal-label { font-size: 0.85em; color: #666; margin-bottom: 5px; }
        .btn { display: inline-block; padding: 8px 16px; background: #2F5496; color: white; text-decoration: none; border-radius: 4px; font-weight: 500; }
        .btn:hover { background: #1e3d6e; }
        .section { margin-bottom: 40px; }
        .section-title { font-size: 1.2em; color: #333; border-left: 4px solid #2F5496; padding-left: 15px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Freelance Job Opportunities</h1>
        <div class="meta">
            <p>Generated: {{ export_date }}</p>
            <p>Total Jobs: {{ total_jobs }}</p>
        </div>
        
        {% for level, level_jobs in jobs_by_level.items() %}
        {% if level_jobs %}
        <div class="section">
            <h2 class="section-title">{{ level.replace('_', ' ') }} ({{ level_jobs|length }})</h2>
            
            {% for job in level_jobs %}
            <div class="job-card">
                <div class="job-header">
                    <h3 class="job-title">{{ job.title }}</h3>
                    <div class="badges">
                        <span class="badge badge-{{ job.match_level.lower().replace('_', '-') }}">{{ job.match_level.replace('_', ' ') }}</span>
                        <span class="badge badge-{{ job.risk_level.lower() }}">{{ job.risk_level }}</span>
                    </div>
                </div>
                
                <div class="job-meta">
                    <div class="meta-item">
                        <div class="meta-label">Platform</div>
                        <div class="meta-value">{{ job.platform }}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Posted</div>
                        <div class="meta-value">{{ job.time_since_posted }}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Budget</div>
                        <div class="meta-value">{{ job.budget }}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Client</div>
                        <div class="meta-value">{{ job.client_name }} ({{ job.client_country }})</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Match Score</div>
                        <div class="meta-value">{{ "%.1f"|format(job.match_score) }}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Category</div>
                        <div class="meta-value">{{ job.category }}</div>
                    </div>
                </div>
                
                <div class="job-meta">
                    <div class="meta-item">
                        <div class="meta-label">Skills</div>
                        <div class="meta-value">{{ job.matched_skills|join(', ') }}</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Client Rating</div>
                        <div class="meta-value">{{ job.client_rating or 'N/A' }} ({{ job.client_review_count or 0 }} reviews)</div>
                    </div>
                    <div class="meta-item">
                        <div class="meta-label">Client History</div>
                        <div class="meta-value">{{ job.client_hire_history or 0 }} hires, ${{ job.client_total_spent or 0 }} spent</div>
                    </div>
                </div>
                
                <div class="job-description">
                    <strong>Summary:</strong> {{ job.short_summary[:500] }}{% if job.short_summary|length > 500 %}...{% endif %}
                </div>
                
                <div class="job-description">
                    <strong>Why it matches:</strong> {{ job.match_reason }}
                </div>
                
                <div class="job-proposal">
                    <div class="proposal-label">Suggested Proposal:</div>
                    {{ job.proposal_normal[:500] }}{% if job.proposal_normal|length > 500 %}...{% endif %}
                </div>
                
                <a href="{{ job.job_url }}" class="btn" target="_blank">View Job</a>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endfor %}
    </div>
</body>
</html>
        """)
        
        # Group jobs by match level
        match_levels = ["EXCELLENT_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH", "WEAK_MATCH", "NOT_RELEVANT"]
        jobs_by_level = {}
        for level in match_levels:
            level_jobs = [j for j in jobs if j.get("match_level") == level]
            if level_jobs:
                jobs_by_level[level] = level_jobs
        
        html = html_template.render(
            export_date=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            total_jobs=len(jobs),
            jobs_by_level=jobs_by_level
        )
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Exported {len(jobs)} jobs to HTML: {filepath}")
        return str(filepath)
    
    def _job_to_row(self, job: dict[str, Any]) -> dict[str, Any]:
        """Convert job dict to export row."""
        # Format date
        date_posted = job.get("date_posted")
        if date_posted and isinstance(date_posted, str):
            try:
                from core.utils import parse_date
                dt = parse_date(date_posted)
                if dt:
                    date_posted = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        discovered_at = job.get("discovered_at")
        if discovered_at and isinstance(discovered_at, str):
            try:
                from core.utils import parse_date
                dt = parse_date(discovered_at)
                if dt:
                    discovered_at = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        return {
            "platform": job.get("platform", ""),
            "title": job.get("title", ""),
            "job_url": job.get("job_url", ""),
            "date_posted": date_posted or "",
            "budget": job.get("budget", ""),
            "currency": job.get("currency", "USD"),
            "category": job.get("category", ""),
            "required_skills": ", ".join(job.get("required_skills", [])),
            "client_name": job.get("client_name", ""),
            "client_country": job.get("client_country", ""),
            "client_rating": job.get("client_rating", ""),
            "client_review_count": job.get("client_review_count", ""),
            "client_hire_history": job.get("client_hire_history", ""),
            "client_total_spent": job.get("client_total_spent", ""),
            "client_payment_status": job.get("client_payment_status", ""),
            "match_score": job.get("match_score", 0),
            "match_level": job.get("match_level", ""),
            "risk_level": job.get("risk_level", ""),
            "short_summary": job.get("short_summary", "")[:500],
            "why_it_matches": job.get("match_reason", ""),
            "proposal_normal": job.get("proposal_normal", "")[:1000],
            "discovered_at": discovered_at or "",
            "verification_status": job.get("verification_status", ""),
            "status": job.get("status", "")
        }


# Convenience function
def export_jobs(jobs: list[dict[str, Any]], format: str = "csv", 
                output_dir: str = None, filename: str = None) -> str:
    """Export jobs to file."""
    manager = ExportManager(output_dir)
    return manager.export_jobs(jobs, format, filename)