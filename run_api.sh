#!/bin/bash

# Portfolio Balancer API Startup Script

echo "Starting Portfolio Balancer API..."
echo "=================================="

# Change to the stock_portfolio_app directory
cd "$(dirname "$0")/stock_portfolio_app"

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv ../venv
    source ../venv/bin/activate
    pip install -r ../requirements.txt
else
    source ../venv/bin/activate
fi

# Set Python path
export PYTHONPATH="$(dirname "$0")/stock_portfolio_app:$PYTHONPATH"

echo ""
echo "Starting API server on http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo "=================================="
echo ""

# Start the API server
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

