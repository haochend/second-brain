#!/bin/bash
# Service control script for Memory Consolidation Service

SERVICE_NAME="com.secondbrain.memory"
PLIST_FILE="$(dirname "$0")/../config/${SERVICE_NAME}.plist"
LAUNCHD_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCHD_DIR/${SERVICE_NAME}.plist"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Make sure the script is executable
chmod +x "$(dirname "$0")/memory-service.sh"

function install_service() {
    echo -e "${YELLOW}Installing Memory Consolidation Service...${NC}"
    
    # Create LaunchAgents directory if it doesn't exist
    mkdir -p "$LAUNCHD_DIR"
    
    # Copy plist file
    cp "$PLIST_FILE" "$INSTALLED_PLIST"
    
    # Load the service
    launchctl load "$INSTALLED_PLIST"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Service installed and started successfully${NC}"
        echo "Service will run automatically:"
        echo "  • Queue processing: Every 5 minutes"
        echo "  • Daily consolidation: 2:00 AM"
        echo "  • Weekly patterns: Sunday 3:00 AM"
        echo "  • Knowledge synthesis: 1st of month 4:00 AM"
        echo "  • Wisdom extraction: Quarterly 5:00 AM"
    else
        echo -e "${RED}✗ Failed to install service${NC}"
        exit 1
    fi
}

function uninstall_service() {
    echo -e "${YELLOW}Uninstalling Memory Consolidation Service...${NC}"
    
    if [ -f "$INSTALLED_PLIST" ]; then
        # Unload the service
        launchctl unload "$INSTALLED_PLIST"
        
        # Remove the plist file
        rm "$INSTALLED_PLIST"
        
        echo -e "${GREEN}✓ Service uninstalled successfully${NC}"
    else
        echo -e "${RED}Service is not installed${NC}"
    fi
}

function start_service() {
    echo -e "${YELLOW}Starting Memory Consolidation Service...${NC}"
    
    if [ ! -f "$INSTALLED_PLIST" ]; then
        echo -e "${RED}Service is not installed. Run: $0 install${NC}"
        exit 1
    fi
    
    launchctl start "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Service started${NC}"
    else
        echo -e "${RED}✗ Failed to start service${NC}"
        exit 1
    fi
}

function stop_service() {
    echo -e "${YELLOW}Stopping Memory Consolidation Service...${NC}"
    
    launchctl stop "$SERVICE_NAME"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Service stopped${NC}"
    else
        echo -e "${RED}✗ Failed to stop service${NC}"
        exit 1
    fi
}

function restart_service() {
    stop_service
    sleep 2
    start_service
}

function status_service() {
    echo -e "${YELLOW}Memory Consolidation Service Status:${NC}"
    echo ""
    
    # Check if plist is installed
    if [ ! -f "$INSTALLED_PLIST" ]; then
        echo -e "${RED}✗ Service is not installed${NC}"
        exit 1
    fi
    
    # Get service status
    STATUS=$(launchctl list | grep "$SERVICE_NAME" | awk '{print $1}')
    
    if [ -n "$STATUS" ]; then
        if [ "$STATUS" = "-" ]; then
            echo -e "${YELLOW}⚠ Service is loaded but not running${NC}"
        elif [ "$STATUS" = "0" ]; then
            echo -e "${GREEN}✓ Service is running successfully${NC}"
        else
            echo -e "${RED}✗ Service exited with error code: $STATUS${NC}"
        fi
        
        # Show full status
        launchctl list "$SERVICE_NAME"
        
        # Show recent logs
        echo ""
        echo -e "${YELLOW}Recent logs:${NC}"
        if [ -f "$HOME/.memory/logs/consolidation-service.log" ]; then
            tail -n 10 "$HOME/.memory/logs/consolidation-service.log"
        else
            echo "No logs available yet"
        fi
    else
        echo -e "${RED}✗ Service is not loaded${NC}"
    fi
}

function view_logs() {
    LOG_FILE="$HOME/.memory/logs/consolidation-service.log"
    
    if [ -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Following service logs (Ctrl+C to exit):${NC}"
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}No log file found at: $LOG_FILE${NC}"
    fi
}

function run_task() {
    TASK=$1
    echo -e "${YELLOW}Running task: $TASK${NC}"
    
    # Run the task directly
    cd "$(dirname "$0")/.."
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    python -m src.memory.service.scheduler --once "$TASK"
}

# Main command processing
case "$1" in
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    run)
        if [ -z "$2" ]; then
            echo "Usage: $0 run [queue|daily|weekly|knowledge|wisdom]"
            exit 1
        fi
        run_task "$2"
        ;;
    *)
        echo "Usage: $0 {install|uninstall|start|stop|restart|status|logs|run <task>}"
        echo ""
        echo "Commands:"
        echo "  install    - Install and start the service"
        echo "  uninstall  - Stop and remove the service"
        echo "  start      - Start the service"
        echo "  stop       - Stop the service"
        echo "  restart    - Restart the service"
        echo "  status     - Show service status"
        echo "  logs       - Follow service logs"
        echo "  run <task> - Run a specific task once"
        echo ""
        echo "Tasks for 'run' command:"
        echo "  queue     - Process pending memories"
        echo "  daily     - Run daily consolidation"
        echo "  weekly    - Run weekly pattern recognition"
        echo "  knowledge - Run knowledge synthesis"
        echo "  wisdom    - Run wisdom extraction"
        exit 1
        ;;
esac