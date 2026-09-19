#!/bin/bash
# Freelance Hunter - Deployment Script
# Run this script after setting up your Vercel account and GitHub repo

set -e

echo "🚀 Freelance Hunter Deployment Setup"
echo "====================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check git
if ! command -v git &> /dev/null; then
    echo "❌ Git not found. Please install git first."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Please run this from the freelance-hunter directory"
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Step 1: Initialize git if needed
if [ ! -d ".git" ]; then
    echo "🔧 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: Freelance Hunter with all features"
fi

# Step 2: Get GitHub repo URL
echo ""
echo "📦 GitHub Repository Setup"
echo "--------------------------"
read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter repository name (default: freelance-hunter): " REPO_NAME
REPO_NAME=${REPO_NAME:-freelance-hunter}

REPO_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"

# Check if remote exists
if git remote get-url origin &> /dev/null; then
    echo "✅ Git remote already configured"
else
    echo "Adding GitHub remote..."
    git remote add origin "$REPO_URL"
fi

# Push to GitHub
echo ""
read -p "Push to GitHub now? (y/n): " PUSH_NOW
if [ "$PUSH_NOW" = "y" ]; then
    git add .
    git commit -m "Deploy: Ready for Vercel deployment" || true
    git branch -M main
    git push -u origin main
    echo "✅ Pushed to GitHub: $REPO_URL"
fi

# Step 3: Vercel CLI check
echo ""
echo "☁️  Vercel Deployment"
echo "---------------------"

if ! command -v vercel &> /dev/null; then
    echo "Installing Vercel CLI..."
    npm install -g vercel
fi

# Step 4: Environment variables
echo ""
echo "🔐 Environment Variables Required"
echo "---------------------------------"
echo "You'll need to set these in Vercel Dashboard after deployment:"
echo ""
echo "For API project:"
echo "  DATABASE_URL=postgresql://user:pass@host:port/db"
echo "  AISA_API_KEY=sk-aisa-..."
echo "  LOG_LEVEL=INFO"
echo ""
echo "For Frontend project:"
echo "  NEXT_PUBLIC_API_URL=https://your-api.vercel.app"
echo ""

read -p "Have you created a Vercel account? (y/n): " HAS_VERCEL
if [ "$HAS_VERCEL" != "y" ]; then
    echo "Please create an account at https://vercel.com first"
    echo "Then run this script again"
    exit 0
fi

# Step 5: Deploy API
echo ""
read -p "Deploy API to Vercel now? (y/n): " DEPLOY_API
if [ "$DEPLOY_API" = "y" ]; then
    echo "Deploying API..."
    cd freelance-hunter
    vercel --prod --yes
    cd ..
    echo "✅ API deployed! Copy the URL above."
fi

# Step 6: Deploy Frontend
echo ""
read -p "Deploy Frontend to Vercel now? (y/n): " DEPLOY_FE
if [ "$DEPLOY_FE" = "y" ]; then
    echo "Deploying Frontend..."
    cd freelance-hunter/frontend
    vercel --prod --yes
    cd ../..
    echo "✅ Frontend deployed!"
fi

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "Next steps:"
echo "1. Add environment variables in Vercel Dashboard"
echo "2. Set NEXT_PUBLIC_API_URL in Frontend project"
echo "3. Configure SMTP in Settings panel after first login"
echo "4. Test email notifications"
echo ""
echo "🔗 Your repositories:"
echo "   GitHub: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "   Vercel Dashboard: https://vercel.com/dashboard"
echo ""

# Save deployment info
cat > DEPLOYMENT_INFO.txt << EOF
Freelance Hunter - Deployment Info
==================================
Date: $(date)
GitHub: https://github.com/$GITHUB_USER/$REPO_NAME
API URL: (check Vercel Dashboard)
Frontend URL: (check Vercel Dashboard)

Environment Variables to Set in Vercel:
---------------------------------------
API Project:
  DATABASE_URL=postgresql://...
  AISA_API_KEY=sk-aisa-...
  LOG_LEVEL=INFO

Frontend Project:
  NEXT_PUBLIC_API_URL=https://your-api.vercel.app

Post-Deployment:
----------------
1. Login to frontend, go to Settings → Email tab
2. Configure SMTP (Gmail App Password)
3. Set notification preferences
4. Test email
5. Run a scan to verify everything works
EOF

echo "📄 Deployment info saved to DEPLOYMENT_INFO.txt"