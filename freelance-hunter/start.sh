#!/bin/bash
# Freelance Hunter - Linux/Mac Startup Script

set -e

echo "========================================"
echo "Freelance Hunter - Multi-Agent Job Hunter"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.10+"
    exit 1
fi

echo "Python found:"
python3 --version

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Create necessary directories
mkdir -p data logs exports

# Initialize database
echo "Initializing database..."
python main.py init-db

echo
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo
echo "To run a scan:"
echo "  python main.py scan"
echo
echo "To run continuous scheduler:"
echo "  python main.py scheduler"
echo
echo "To start dashboard API:"
echo "  python -m core.api.main"
echo
echo "Then open http://localhost:8000/dashboard"
echo