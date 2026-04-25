#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run tests with coverage
echo "Running tests with coverage..."
pytest --cov=. --cov-report=html --cov-report=term-missing

echo ""
echo "✅ Tests completed!"
echo "📊 Coverage report generated in htmlcov/index.html"
echo ""
echo "To view the HTML report:"
echo "  open htmlcov/index.html"
