#!/bin/bash
# Freelance Hunter - Automated Deployment Script
# Run this after: gh auth login && vercel login

set -e

echo "🚀 Freelance Hunter - Automated Deployment"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check prerequisites
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}❌ $1 not found. Please install it first.${NC}"
        exit 1
    fi
}

echo -e "${BLUE}📋 Checking prerequisites...${NC}"
check_command git
check_command gh
check_command vercel
check_command node
check_command npm

# Verify authentication
echo -e "${BLUE}🔐 Verifying authentication...${NC}"
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Not logged into GitHub. Run: gh auth login${NC}"
    exit 1
fi

if ! vercel whoami &> /dev/null; then
    echo -e "${RED}❌ Not logged into Vercel. Run: vercel login${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Get GitHub username
GITHUB_USER=$(gh api user --jq '.login')
echo -e "${BLUE}👤 GitHub user: $GITHUB_USER${NC}"

# Repository name
REPO_NAME="freelance-hunter"
read -p "Repository name [$REPO_NAME]: " INPUT_REPO
REPO_NAME=${INPUT_REPO:-$REPO_NAME}

REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"

# Step 1: Initialize git if needed
echo -e "${BLUE}📁 Setting up Git repository...${NC}"
if [ ! -d ".git" ]; then
    git init
fi

# Configure git if needed
if ! git config user.name &> /dev/null; then
    read -p "Git user name: " GIT_NAME
    read -p "Git email: " GIT_EMAIL
    git config user.name "$GIT_NAME"
    git config user.email "$GIT_EMAIL"
fi

# Add all files
git add .

# Commit if there are changes
if ! git diff --cached --quiet; then
    git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M')"
fi

# Step 2: Create GitHub repo if needed
echo -e "${BLUE}📦 Setting up GitHub repository...${NC}"
if gh repo view "$GITHUB_USER/$REPO_NAME" &> /dev/null; then
    echo -e "${GREEN}✅ Repository exists${NC}"
else
    echo -e "${YELLOW}Creating repository...${NC}"
    gh repo create "$GITHUB_USER/$REPO_NAME" --public --source=. --remote=origin --push
fi

# Ensure remote is set
if ! git remote get-url origin &> /dev/null; then
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
fi

# Push to GitHub
echo -e "${BLUE}📤 Pushing to GitHub...${NC}"
git branch -M main
git push -u origin main --force-with-lease

echo -e "${GREEN}✅ Code pushed to GitHub${NC}"

# Step 3: Vercel Deployment
echo ""
echo -e "${BLUE}☁️  Deploying to Vercel...${NC}"

# Deploy API
echo -e "${BLUE}🔧 Deploying API...${NC}"
cd freelance-hunter

# Link Vercel project for API
if [ ! -f ".vercel/project.json" ]; then
    echo "Linking Vercel project for API..."
    vercel link --yes --scope=$(vercel whoami | awk '{print $1}')
fi

# Deploy API
echo "Deploying API to production..."
vercel --prod --yes
API_URL=$(vercel ls --scope=$(vercel whoami | awk '{print $1}') | grep freelance-hunter | head -1 | awk '{print $2}')
echo -e "${GREEN}✅ API deployed: $API_URL${NC}"

# Deploy Frontend
echo -e "${BLUE}🎨 Deploying Frontend...${NC}"
cd ../frontend

# Link Vercel project for Frontend
if [ ! -f ".vercel/project.json" ]; then
    echo "Linking Vercel project for Frontend..."
    vercel link --yes --scope=$(vercel whoami | awk '{print $1}')
fi

# Update NEXT_PUBLIC_API_URL
echo "Setting NEXT_PUBLIC_API_URL..."
vercel env add NEXT_PUBLIC_API_URL production <<< "$API_URL" 2>/dev/null || true

# Deploy Frontend
vercel --prod --yes
FRONTEND_URL=$(vercel ls --scope=$(vercel whoami | awk '{print $1}') | grep freelance-hunter-frontend | head -1 | awk '{print $2}')
echo -e "${GREEN}✅ Frontend deployed: $FRONTEND_URL${NC}"

cd ../..

# Step 4: Configure GitHub Secrets
echo ""
echo -e "${BLUE}🔐 Setting up GitHub Secrets...${NC}"

# Read environment variables from .env.example or prompt
if [ -f ".env" ]; then
    echo "Loading environment from .env..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Required secrets
declare -A SECRETS=(
    ["VERCEL_TOKEN"]="${VERCEL_TOKEN:-}"
    ["VERCEL_ORG_ID"]="${VERCEL_ORG_ID:-}"
    ["VERCEL_API_PROJECT_ID"]="${VERCEL_API_PROJECT_ID:-}"
    ["VERCEL_FRONTEND_PROJECT_ID"]="${VERCEL_FRONTEND_PROJECT_ID:-}"
    ["DATABASE_URL"]="${DATABASE_URL:-}"
    ["AISA_API_KEY"]="${AISA_API_KEY:-}"
)

for secret in "${!SECRETS[@]}"; do
    value="${SECRETS[$secret]}"
    if [ -z "$value" ]; then
        read -sp "Enter $secret: " value
        echo ""
    fi
    if [ -n "$value" ]; then
        gh secret set "$secret" --body "$value" --repo "$GITHUB_USER/$REPO_NAME"
        echo -e "${GREEN}✅ Set $secret${NC}"
    fi
done

# Step 5: Enable GitHub Actions
echo -e "${BLUE}⚙️  Enabling GitHub Actions...${NC}"
gh api repos/$GITHUB_USER/freelance-hunter/actions/permissions -X PUT -f enabled=true -f allowed_actions=all > /dev/null
echo -e "${GREEN}✅ GitHub Actions enabled${NC}"

# Step 6: Trigger first deployment
echo ""
echo -e "${BLUE}🚀 Triggering first deployment...${NC}"
gh workflow run deploy.yml --ref main --repo "$GITHUB_USER/freelance-hunter"

# Final output
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📋 Deployment Summary:${NC}"
echo -e "  GitHub Repo: ${GREEN}https://github.com/$GITHUB_USER/freelance-hunter${NC}"
echo -e "  API URL:      ${GREEN}$API_URL${NC}"
echo -e "  Frontend URL: ${GREEN}$FRONTEND_URL${NC}"
echo -e "  Actions:      ${GREEN}https://github.com/$GITHUB_USER/freelance-hunter/actions${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Go to Vercel Dashboard → Add Environment Variables:"
echo "   - DATABASE_URL (PostgreSQL)"
echo "   - AISA_API_KEY"
echo "   - LOG_LEVEL=INFO"
echo ""
echo "2. In Frontend project settings:"
echo "   - NEXT_PUBLIC_API_URL = $API_URL"
echo ""
echo "3. Go to your frontend URL and configure SMTP in Settings"
echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"