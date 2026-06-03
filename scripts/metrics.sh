 #!/bin/bash
 # Display current system and application metrics
 
 # Configuration
 API_URL="${API_URL:-http://localhost:8000}"
 
 # Colors
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 BLUE='\033[0;34m'
 NC='\033[0m'
 
 echo -e "${GREEN}═══════════════════════════════════════${NC}"
 echo -e "${GREEN}  Dynamic Pricing Engine - Metrics${NC}"
 echo -e "${GREEN}═══════════════════════════════════════${NC}"
 echo ""
 
 # System Metrics
 echo -e "${BLUE}System Metrics:${NC}"
 echo "---------------"
 
 # CPU Usage
 if command -v top &> /dev/null; then
     cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
     echo -e "CPU Usage: ${YELLOW}${cpu_usage}%${NC}"
 fi
 
 # Memory Usage
 if command -v free &> /dev/null; then
     mem_info=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2 }')
     echo -e "Memory Usage: ${YELLOW}${mem_info}${NC}"
 fi
 
 # Disk Usage
 disk_usage=$(df -h . | awk 'NR==2{print $5}')
 echo -e "Disk Usage: ${YELLOW}${disk_usage}${NC}"
 
 echo ""
 
 # Application Metrics
 echo -e "${BLUE}Application Metrics:${NC}"
 echo "--------------------"
 
 if response=$(curl -s "$API_URL/v1/metrics" 2>/dev/null); then
     echo "$response" | python3 -c "
 import sys
 import json
 
 try:
     data = json.load(sys.stdin)
     
     print(f\"Total Requests: \033[1;33m{data.get('total_requests', 0)}\033[0m\")
     print(f\"Error Count: \033[1;33m{data.get('error_count', 0)}\033[0m\")
     
     error_rate = data.get('error_rate', 0)
     color = '\033[0;31m' if error_rate > 0.05 else '\033[0;32m'
     print(f\"Error Rate: {color}{error_rate:.2%}\033[0m\")
     
     print(f\"Avg Response Time: \033[1;33m{data.get('avg_response_time_ms', 0):.2f}ms\033[0m\")
     print(f\"Uptime: \033[1;33m{data.get('uptime_seconds', 0):.0f}s\033[0m\")
 except:
     print('Unable to parse metrics')
 " 2>/dev/null
 else
     echo -e "${RED}Unable to fetch application metrics${NC}"
     echo "Make sure the API is running at $API_URL"
 fi
 
 echo ""
 
 # Docker Metrics (if running in Docker)
 if command -v docker &> /dev/null && docker ps | grep -q pricing-api; then
     echo -e "${BLUE}Docker Container Metrics:${NC}"
     echo "-------------------------"
     docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep pricing-api
     echo ""
 fi
 
 # Recent Logs Summary
 echo -e "${BLUE}Recent Activity (last 10 log entries):${NC}"
 echo "---------------------------------------"
 if [ -f "logs/app.log" ]; then
     tail -10 logs/app.log | while read line; do
         if echo "$line" | grep -q "ERROR"; then
             echo -e "${RED}$line${NC}"
         elif echo "$line" | grep -q "WARNING"; then
             echo -e "${YELLOW}$line${NC}"
         else
             echo "$line"
         fi
     done
 else
     echo "No logs found"
 fi
 
 echo ""
 echo -e "${GREEN}═══════════════════════════════════════${NC}"
