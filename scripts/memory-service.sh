#!/bin/bash
# Memory Consolidation Service wrapper script

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Load environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# Set default MEMORY_HOME if not set
export MEMORY_HOME="${MEMORY_HOME:-$HOME/.memory}"

# Ensure memory directory exists
mkdir -p "$MEMORY_HOME"

# Log file location
LOG_DIR="$MEMORY_HOME/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/consolidation-service.log"

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Change to project root
cd "$PROJECT_ROOT"

# Run the scheduler with logging
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting Memory Consolidation Service" >> "$LOG_FILE"
python -m src.memory.service.scheduler 2>&1 | tee -a "$LOG_FILE"