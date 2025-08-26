#!/bin/bash

# Run tests for Second Brain

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install test dependencies if needed
pip install -q pytest pytest-cov pytest-mock 2>/dev/null

echo "🧪 Running Second Brain Tests"
echo "=============================="
echo

# Run different test suites
if [ "$1" == "unit" ]; then
    echo "Running unit tests..."
    pytest tests/unit/ -v --tb=short
elif [ "$1" == "integration" ]; then
    echo "Running integration tests..."
    pytest tests/integration/ -v --tb=short -m integration
elif [ "$1" == "edge" ]; then
    echo "Running edge case tests..."
    pytest tests/edge_cases/ -v --tb=short
elif [ "$1" == "coverage" ]; then
    echo "Running tests with coverage..."
    pytest tests/ --cov=src/memory --cov-report=term-missing --cov-report=html
    echo
    echo "📊 Coverage report generated in htmlcov/index.html"
elif [ "$1" == "quick" ]; then
    echo "Running quick unit tests (no slow/integration tests)..."
    pytest tests/unit/ -v --tb=short -m "not slow" -k "not concurrent"
else
    echo "Usage: ./run_tests.sh [unit|integration|edge|coverage|quick|all]"
    echo
    echo "Running all tests..."
    pytest tests/ -v --tb=short
fi

echo
echo "✅ Test run complete!"