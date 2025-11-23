#!/bin/bash

# Setup script for Multi-Agent Job Matching System

echo "=========================================="
echo "Job Agent System Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers (optional)
read -p "Install Playwright browsers for advanced scraping? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing Playwright browsers..."
    playwright install
fi

# Create .env file if it doesn't exist
echo ""
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  IMPORTANT: Edit .env file with your API keys and email settings"
else
    echo ".env file already exists"
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/cv/tailored
mkdir -p data/jobs
mkdir -p data/logs
echo "✓ Directories created"

# Check if master CV exists
echo ""
if [ ! -f "data/cv/master_cv.md" ]; then
    echo "⚠️  Master CV not found at data/cv/master_cv.md"
    echo "   A sample template has been created. Please update it with your information."
else
    echo "✓ Master CV found"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys and email settings"
echo "2. Edit config.yaml with your job preferences"
echo "3. Update data/cv/master_cv.md with your CV"
echo "4. Run test mode: python main.py --test"
echo "5. Run production: python main.py"
echo ""
echo "For scheduled daily runs:"
echo "  python schedule_daily.py"
echo ""
echo "Happy job hunting! 🎯"
