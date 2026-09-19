# Freelance Hunter

A production-quality multi-agent system for continuously discovering, verifying, and analyzing freelance job opportunities that match your skills.

## ✨ Features

- **Multi-Agent Architecture**: 13 specialized agents working in concert
- **Platform Discovery**: Automatically discovers and validates 19+ freelance platforms
- **Specialized Search**: Agents for Data Entry, Documents/PDF, PowerPoint, Excel, General Freelance
- **Search Engine Integration**: Queries Google, Bing, DuckDuckGo with site-specific searches
- **Verification**: Validates job authenticity, checks for expiration, spam detection
- **Deduplication**: Removes duplicates across platforms and search sources
- **Intelligent Matching**: Scores jobs against your profile (0-100)
- **Risk Detection**: Identifies red flags and assesses risk levels (4 levels)
- **Proposal Generation**: Creates 3 customized proposals per job
- **Web Dashboard**: Full React/Next.js UI with filters, settings, job details
- **Export**: CSV, Excel, JSON, Markdown, HTML
- **Scheduling**: Automated runs (hourly, 3h, 6h, 12h, daily)
- **Daily Reports**: Formatted summary of new opportunities

## 🏗️ Architecture

```
freelance-hunter/
├── agents/                 # 13 specialized agents
├── core/
│   ├── api/               # FastAPI backend
│   ├── database/          # SQLAlchemy models & repositories
│   ├── scheduler/         # APScheduler integration
│   ├── config/            # Configuration management
│   └── utils.py           # Shared utilities
├── frontend/              # Next.js 14 + React 18 + Tailwind
├── exports/               # Export functionality
├── tests/                 # Test suite
├── config/                # Configuration files
├── api/                   # Vercel serverless API entry
└── main.py               # CLI entry point
```

## 🚀 Quick Start

### Local Development

```bash
cd freelance-hunter

# 1. Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Configure
cp config/settings.yaml config/settings.local.yaml
cp config/profile.json config/profile.local.json
# Edit config/profile.local.json with your skills/profile

# 3. Initialize database
python main.py init-db

# 4. Run a scan
python main.py scan              # Last 24h
python main.py scan --priority 2 # Last 72h

# 5. Start API + Dashboard
python -m core.api.main
# Open http://localhost:8000/dashboard

# 6. Run scheduler (continuous)
python main.py scheduler
```

### Web Dashboard (Next.js)

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

## ☁️ Deploy to Vercel (Production)

### Prerequisites
- Vercel account
- GitHub repository
- PostgreSQL database (Neon, Supabase, or Vercel Postgres)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/freelance-hunter.git
git push -u origin main
```

### 2. Deploy API to Vercel
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Import GitHub repository
3. Configure project:
   - **Framework Preset**: Python
   - **Root Directory**: `freelance-hunter` (or `/` if repo root)
   - **Build Command**: `pip install -r requirements-api.txt`
   - **Output Directory**: `.`
4. Add Environment Variables:
   - `DATABASE_URL`: Your PostgreSQL connection string
   - `AISA_API_KEY`: Your AIsa API key (optional)
   - `LOG_LEVEL`: `INFO`
5. Deploy → Get API URL (e.g., `https://freelance-hunter-api.vercel.app`)

### 3. Deploy Frontend to Vercel
1. Create **new project** in Vercel
2. Import same GitHub repo
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL`: Your API URL from step 2
5. Deploy → Get Frontend URL (e.g., `https://freelance-hunter.vercel.app`)

### 4. Configure GitHub Secrets (for CI/CD)
Add these secrets in GitHub repo settings:
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID` (API project)
- `VERCEL_FRONTEND_PROJECT_ID` (Frontend project)
- `DATABASE_URL`
- `AISA_API_KEY`

## 🌐 Web Dashboard Features

| Feature | Description |
|---------|-------------|
| **Jobs Table** | Sortable, filterable, paginated table with 200+ jobs |
| **Advanced Filters** | Platform, category, match level, risk, verification, min score, keyword |
| **Job Detail Modal** | Full job info, client details, match analysis, risk flags, 3 proposals |
| **One-Click Copy** | Copy short/normal/ultra-short proposals |
| **Settings Panel** | Profile, skills, languages, strengths, preferences, rate range |
| **Export** | CSV, Excel, JSON, Markdown, HTML |
| **Daily Report** | Formatted report with top opportunities |
| **Live Scan** | Trigger scans from UI with progress |

## 📋 Configuration

### Profile (`config/profile.json`)
```json
{
  "skills": ["Microsoft Excel", "Microsoft PowerPoint", "Data Entry", ...],
  "experience_level": "Beginner/Intermediate",
  "languages": ["Arabic", "English"],
  "location": "Egypt",
  "availability": "Remote",
  "strengths": ["attention to detail", "organization", "fast learning"],
  "hourly_rate_range": {"min": 5, "max": 25, "currency": "USD"},
  "preferred_job_types": ["fixed_price", "hourly"],
  "max_hours_per_week": 30
}
```

### Settings (`config/settings.yaml`)
Key settings:
- `search.time_windows`: Recency priorities (24h, 72h, 7d, 30d)
- `search.max_pages_per_platform`: Pagination depth
- `matching.*`: Scoring weights (skill 30%, recency 20%, beginner 15%, etc.)
- `risk_detection.red_flags`: 11 pattern categories
- `scheduler.default_interval_hours`: Auto-run interval (default 6h)

## 🤖 Agent Details

| Agent | Purpose |
|-------|---------|
| Platform Discovery | Discovers 19+ platforms, validates accessibility |
| Data Entry | Data entry, Excel/Sheets, invoices, copy typing |
| Document/PDF/Word | PDF conversion, Word formatting, OCR, transcription |
| PowerPoint/Presentation | Design, pitch decks, Canva, Google Slides |
| Excel/Spreadsheet | Formulas, pivot tables, data cleaning, dashboards |
| General Freelance | Virtual assistant, web research, admin tasks |
| Search Engine | Google/Bing/DuckDuckGo site-specific queries |
| Verification | URL check, expiration, spam, profile detection |
| Deduplication | URL, title, client, description, date similarity |
| Matching | 0-100 scoring across 8 weighted components |
| Risk Detection | 11 categories, 4 severity levels |
| Proposal | 3 customized proposals per job |
| Orchestrator | Coordinates full pipeline |

## 📊 Scoring System

| Component | Weight | Max Points |
|-----------|--------|------------|
| Skill Match | 30% | 30 |
| Recency | 20% | 20 |
| Beginner Accessibility | 15% | 15 |
| Budget/Value | 10% | 10 |
| Client Quality | 10% | 10 |
| Competition | 5% | 5 |
| Clarity | 5% | 5 |
| Ease of Delivery | 5% | 5 |
| **Total** | **100%** | **100** |

**Match Levels:**
- **EXCELLENT_MATCH** (≥75, skill ≥25)
- **GOOD_MATCH** (≥60, skill ≥20)
- **POSSIBLE_MATCH** (≥45, skill ≥15)
- **WEAK_MATCH** (≥30, skill ≥10)
- **NOT_RELEVANT** (<30)

## 🛡️ Risk Levels

| Level | Description |
|-------|-------------|
| **LOW** | No red flags detected |
| **MEDIUM** | Minor concerns (unverified payment, new client) |
| **HIGH** | Significant issues (suspicious budget, platform violation) |
| **CRITICAL** | Severe risks (payment before start, passwords, illegal work) |

## 📦 Export Formats

- **CSV**: Spreadsheet compatible
- **Excel (XLSX)**: Formatted with filters, frozen headers
- **JSON**: Complete data for programmatic use
- **Markdown**: Human-readable with sections
- **HTML**: Styled report with badges and links

## 📡 API Endpoints

```
GET  /api/stats              # Dashboard statistics
GET  /api/jobs               # List jobs with filters
GET  /api/jobs/recent        # Recent jobs
GET  /api/jobs/{id}          # Single job details
POST /api/jobs/{id}/status   # Update job status
POST /api/scan               # Start new scan
GET  /api/scan/status        # Scan history
POST /api/export             # Export jobs
GET  /api/report/daily       # Daily report
GET  /api/platforms          # Platform list
GET  /api/agents/stats       # Agent performance
```

## 🔧 Scheduling

```bash
# Default: every 6 hours
python main.py scheduler

# Configure in settings.yaml:
scheduler:
  default_interval_hours: 6
  intervals: ["1h", "3h", "6h", "12h", "24h"]
  timezone: "Africa/Cairo"
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_all.py::TestUtils -v

# Run with coverage
pytest tests/ --cov=agents --cov=core
```

## 🔒 Security & Ethics

- Respects robots.txt and Terms of Service
- No CAPTCHA bypassing
- No authentication bypassing
- No private data collection
- No automated bidding/submission
- Rate limiting built-in
- Public data only

## 📋 Requirements

- Python 3.10+
- PostgreSQL (production) or SQLite (local)
- Node.js 18+ for frontend
- Playwright for browser automation (optional)

## 📄 License

MIT License

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## 📞 Support

For issues and feature requests, please use the GitHub issue tracker.