#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Freelance Hunter - Automated Deployment Script for Windows
.DESCRIPTION
    Automates deployment to GitHub + Vercel with full CI/CD setup
.NOTES
    Run after: gh auth login && vercel login
#>

param(
    [string]$RepoName = "freelance-hunter",
    [switch]$SkipGitHub,
    [switch]$SkipVercel,
    [switch]$SkipSecrets
)

# Colors
$Green = [ConsoleColor]::Green
$Blue = [ConsoleColor]::Blue
$Yellow = [ConsoleColor]::Yellow
$Red = [ConsoleColor]::Red

function Write-Color($msg, $color) {
    Write-Host $msg -ForegroundColor $color
}

function Check-Command($cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Color "❌ $cmd not found. Install it first." $Red
        exit 1
    }
}

# Clear screen
Clear-Host

Write-Color "🚀 Freelance Hunter - Automated Deployment" $Blue
Write-Color "============================================" $Blue
Write-Host ""

# Check prerequisites
Write-Color "📋 Checking prerequisites..." $Blue
@("git", "gh", "vercel", "node", "npm") | ForEach-Object {
    Check-Command $_
}

# Verify authentication
Write-Color "🔐 Verifying authentication..." $Blue

if (-not (gh auth status 2>$null)) {
    Write-Color "❌ Not logged into GitHub. Run: gh auth login" $Red
    exit 1
}

if (-not (vercel whoami 2>$null)) {
    Write-Color "❌ Not logged into Vercel. Run: vercel login" $Red
    exit 1
}

Write-Color "✅ All prerequisites met" $Green
Write-Host ""

# Get GitHub username
$githubUser = gh api user --jq '.login'
Write-Color "👤 GitHub user: $githubUser" $Blue

# Repository name
$repoName = "freelance-hunter"
$repoInput = Read-Host "Repository name [$repoName]"
if ($repoInput) { $repoName = $repoInput }

$repoUrl = "https://github.com/$($githubUser)/$repoName.git"

# Step 1: Git setup
Write-Color "📁 Setting up Git repository..." $Blue

if (-not (Test-Path ".git")) {
    git init
}

if (-not (git config user.name)) {
    $gitName = Read-Host "Git user name"
    $gitEmail = Read-Host "Git email"
    git config user.name $gitName
    git config user.email $gitEmail
}

git add .

if (-not (git diff --cached --quiet)) {
    git commit -m "Deploy: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

# Step 2: GitHub Repository
Write-Color "📦 Setting up GitHub repository..." $Blue

if (gh repo view "$githubUser/freelance-hunter" 2>$null) {
    Write-Color "✅ Repository exists" $Green
} else {
    Write-Color "Creating repository..." $Yellow
    gh repo create "$githubUser/freelance-hunter" --public --source=. --remote=origin --push
}

if (-not (git remote get-url origin 2>$null)) {
    git remote add origin "https://github.com/$githubUser/freelance-hunter.git"
}

git branch -M main
git push -u origin main --force-with-lease

Write-Color "✅ Code pushed to GitHub" $Green

# Step 3: Vercel Deployment
Write-Color "☁️ Deploying to Vercel..." $Blue

# Deploy API
Write-Color "🔧 Deploying API..." $Blue
Set-Location freelance-hunter

if (-not (Test-Path ".vercel/project.json")) {
    Write-Color "Linking Vercel project for API..." $Blue
    vercel link --yes
}

Write-Color "Deploying API to production..." $Blue
vercel --prod --yes

# Get API URL
$apiUrl = (vercel ls | Select-String "freelance-hunter" | Select-Object -First 1).Line.Split()[1]
Write-Color "✅ API deployed: $apiUrl" $Green

# Deploy Frontend
Write-Color "🎨 Deploying Frontend..." $Blue
Set-Location ../frontend

if (-not (Test-Path ".vercel/project.json")) {
    Write-Color "Linking Vercel project for Frontend..." $Blue
    vercel link --yes
}

Write-Color "Setting NEXT_PUBLIC_API_URL..." $Blue
vercel env add NEXT_PUBLIC_API_URL production <<< $apiUrl 2>$null

Write-Color "Deploying Frontend to production..." $Blue
vercel --prod --yes

$frontendUrl = (vercel ls | Select-String "freelance-hunter-frontend" | Select-Object -First 1).Line.Split()[1]
Write-Color "✅ Frontend deployed: $frontendUrl" $Green

Set-Location ../..

# Step 4: GitHub Secrets
Write-Color "🔐 Setting up GitHub Secrets..." $Blue

$secrets = @{
    "VERCEL_TOKEN" = $env:VERCEL_TOKEN
    "VERCEL_ORG_ID" = $env:VERCEL_ORG_ID
    "VERCEL_API_PROJECT_ID" = $env:VERCEL_API_PROJECT_ID
    "VERCEL_FRONTEND_PROJECT_ID" = $env:VERCEL_FRONTEND_PROJECT_ID
    "DATABASE_URL" = $env:DATABASE_URL
    "AISA_API_KEY" = $env:AISA_API_KEY
}

foreach ($secret in $secrets.Keys) {
    $value = $secrets[$secret]
    if (-not $value) {
        $value = Read-Host -AsSecureString "Enter $secret"
        $value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($value))
    }
    if ($value) {
        gh secret set $secret --body $value --repo "$githubUser/freelance-hunter"
        Write-Color "✅ Set $secret" $Green
    }
}

# Step 5: Enable GitHub Actions
Write-Color "⚙️ Enabling GitHub Actions..." $Blue
gh api repos/$githubUser/freelance-hunter/actions/permissions -X PUT -f enabled=$true -f allowed_actions=all > $null
Write-Color "✅ GitHub Actions enabled" $Green

# Step 6: Trigger first deployment
Write-Color "🚀 Triggering first deployment..." $Blue
gh workflow run deploy.yml --ref main --repo "$githubUser/freelance-hunter"

# Final output
Clear-Host
Write-Color "========================================" $Green
Write-Color "🎉 DEPLOYMENT COMPLETE!" $Green
Write-Color "========================================" $Green
Write-Host ""
Write-Color "📋 Deployment Summary:" $Blue
Write-Host "  GitHub Repo: https://github.com/$githubUser/freelance-hunter"
Write-Host "  API URL:      $apiUrl"
Write-Host "  Frontend URL: $frontendUrl"
Write-Host "  Actions:      https://github.com/$githubUser/freelance-hunter/actions"
Write-Host ""
Write-Color "📋 Next Steps:" $Yellow
Write-Host "1. Vercel Dashboard → Add Environment Variables:"
Write-Host "   DATABASE_URL (PostgreSQL from Neon/Supabase)"
Write-Host "   AISA_API_KEY"
Write-Host "   LOG_LEVEL=INFO"
Write-Host ""
Write-Host "2. Frontend project: NEXT_PUBLIC_API_URL = $apiUrl"
Write-Host ""
Write-Host "3. Open Frontend URL → Settings → Configure SMTP"
Write-Host ""
Write-Color "🎉 Deployment Complete!" $Green