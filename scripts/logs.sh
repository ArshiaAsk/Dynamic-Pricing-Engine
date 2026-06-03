 #!/bin/bash
 # Log viewing and filtering utility
 
 # Configuration
 LOG_DIR="${LOG_DIR:-logs}"
 
 # Colors
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m'
 
 # Function to show usage
 show_usage() {
     echo "Usage: $0 [OPTIONS]"
     echo ""
     echo "Options:"
     echo "  -f, --follow          Follow log output (tail -f)"
     echo "  -n, --lines N         Show last N lines (default: 50)"
     echo "  -l, --level LEVEL     Filter by log level (DEBUG, INFO, WARNING, ERROR)"
     echo "  -s, --search TERM     Search for specific term"
     echo "  -t, --type TYPE       Log type (app, predictions, monitoring)"
     echo "  -h, --help            Show this help message"
     echo ""
     echo "Examples:"
     echo "  $0 -f                 # Follow application logs"
     echo "  $0 -l ERROR -n 100    # Show last 100 error logs"
     echo "  $0 -s 'request_id'    # Search for request_id in logs"
     echo "  $0 -t predictions     # View prediction logs"
 }
 
 # Default values
 FOLLOW=false
 LINES=50
 LEVEL=""
 SEARCH=""
 LOG_TYPE="app"
 
 # Parse arguments
 while [[ $# -gt 0 ]]; do
     case $1 in
         -f|--follow)
             FOLLOW=true
             shift
             ;;
         -n|--lines)
             LINES="$2"
             shift 2
             ;;
         -l|--level)
             LEVEL="$2"
             shift 2
             ;;
         -s|--search)
             SEARCH="$2"
             shift 2
             ;;
         -t|--type)
             LOG_TYPE="$2"
             shift 2
             ;;
         -h|--help)
             show_usage
             exit 0
             ;;
         *)
             echo "Unknown option: $1"
             show_usage
             exit 1
             ;;
     esac
 done
 
 # Determine log file
 case $LOG_TYPE in
     app)
         LOG_FILE="$LOG_DIR/app.log"
         ;;
     predictions)
         LOG_FILE=$(ls -t $LOG_DIR/predictions/*.jsonl 2>/dev/null | head -1)
         if [ -z "$LOG_FILE" ]; then
             echo -e "${RED}No prediction logs found${NC}"
             exit 1
         fi
         ;;
     monitoring)
         LOG_FILE="$LOG_DIR/monitoring/monitoring.log"
         ;;
     *)
         echo -e "${RED}Unknown log type: $LOG_TYPE${NC}"
         exit 1
         ;;
 esac
 
 # Check if log file exists
 if [ ! -f "$LOG_FILE" ]; then
     echo -e "${RED}Log file not found: $LOG_FILE${NC}"
     exit 1
 fi
 
 echo -e "${GREEN}Viewing logs: $LOG_FILE${NC}"
 echo ""
 
 # Build command
 CMD="cat $LOG_FILE"
 
 # Apply filters
 if [ -n "$LEVEL" ]; then
     CMD="$CMD | grep -i \"$LEVEL\""
 fi
 
 if [ -n "$SEARCH" ]; then
     CMD="$CMD | grep -i \"$SEARCH\""
 fi
 
 # Follow or show last N lines
 if [ "$FOLLOW" = true ]; then
     eval "$CMD | tail -f"
 else
     eval "$CMD | tail -n $LINES"
 fi
