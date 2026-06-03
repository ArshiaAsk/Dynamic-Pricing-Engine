 #!/bin/bash
 # Health check script for monitoring
 
 set -e
 
 # Configuration
 API_URL="${API_URL:-http://localhost:8000}"
 
 # Colors
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m'
 
 echo -e "${GREEN}Health Check Report${NC}"
 echo "===================="
 echo "API URL: $API_URL"
 echo ""
 
 # Check health endpoint
 echo -e "${YELLOW}Checking /v1/health...${NC}"
 if response=$(curl -s -w "\n%{http_code}" "$API_URL/v1/health"); then
     http_code=$(echo "$response" | tail -n1)
     body=$(echo "$response" | head -n-1)
     
     if [ "$http_code" = "200" ]; then
         echo -e "${GREEN}✓ Health check passed${NC}"
         echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
     else
         echo -e "${RED}✗ Health check failed (HTTP $http_code)${NC}"
         echo "$body"
         exit 1
     fi
 else
     echo -e "${RED}✗ Cannot connect to API${NC}"
     exit 1
 fi
 
 echo ""
 
 # Check readiness
 echo -e "${YELLOW}Checking /v1/health/ready...${NC}"
 if response=$(curl -s -w "\n%{http_code}" "$API_URL/v1/health/ready"); then
     http_code=$(echo "$response" | tail -n1)
     
     if [ "$http_code" = "200" ]; then
         echo -e "${GREEN}✓ Service is ready${NC}"
     else
         echo -e "${RED}✗ Service not ready (HTTP $http_code)${NC}"
     fi
 fi
 
 echo ""
 
 # Check metrics
 echo -e "${YELLOW}Checking /v1/metrics...${NC}"
 if response=$(curl -s -w "\n%{http_code}" "$API_URL/v1/metrics"); then
     http_code=$(echo "$response" | tail -n1)
     body=$(echo "$response" | head -n-1)
     
     if [ "$http_code" = "200" ]; then
         echo -e "${GREEN}✓ Metrics available${NC}"
         echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
     fi
 fi
 
 echo ""
 echo -e "${GREEN}Health check completed${NC}"
