# 🚀 Freelance Hunter - Quick Start Deployment

## Prerequisites (Run Once)

```powershell
# 1. Install required tools
winget install GitHub.cli Vercel.CLI NodeJS.LTS

# 2. Login to services (interactive)
gh auth login
vercel login
```

## Deploy (Automatic)

```powershell
# Option 1: Double-click deploy.bat
# OR
# Option 2: Run in PowerShell
cd freelance-hunter
.\auto-deploy.ps1
```

## What Happens Automatically

| Step | Action |
|------|--------|
| 1️⃣ | Creates GitHub repo + pushes code |
| 2️⃣ | Deploys API to Vercel (production) |
| 3️⃣ | Deploys Frontend to Vercel |
| 4️⃣ | Sets `NEXT_PUBLIC_API_URL` |
| 4️⃣ | Adds GitHub Secrets |
| 5️⃣ | Enables GitHub Actions CI/CD |
| 6️⃣ | Triggers first deployment |

## After Deployment (Manual)

1. **Vercel Dashboard → API Project → Settings → Environment Variables:**
   ```
   DATABASE_URL=postgresql://...
   AISA_API_KEY=sk-aisa-...
   LOG_LEVEL=INFO
   ```

2. **Vercel Dashboard → Frontend Project → Settings → Environment Variables:**
   ```
   NEXT_PUBLIC_API_URL=https://your-api.vercel.app
   ```

3. **Open Frontend URL → Settings → Email tab → Configure SMTP**
   - Use Gmail App Password (not regular password)

## Required Accounts

- ✅ GitHub (gh auth login)
- ✅ Vercel (vercel login)
- ✅ PostgreSQL (Neon/Supabase - free tier)
- ✅ Gmail (for notifications)

## Files Created

| File | Purpose |
|------|---------|
| `auto-deploy.ps1` | Main PowerShell deployment script |
| `deploy.bat` | Double-click launcher |
| `.github/workflows/deploy.yml` | CI/CD pipeline |
| `vercel.json` | Vercel config |
| `.env.example` | Environment template |
| `.env` | Your actual secrets (create from example) |

## Support

- GitHub Actions: https://github.com/YOUR_USER/freelance-hunter/actions
- Vercel Dashboard: https://vercel.com/dashboard
- Issues: https://github.com/YOUR_USER/freelance-hunter/issues