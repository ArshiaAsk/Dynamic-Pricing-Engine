 #!/bin/bash
 # Simple load testing script
 
 # Configuration
 API_URL="${API_URL:-http://localhost:8000}"
 CONCURRENT_REQUESTS="${CONCURRENT_REQUESTS:-10}"
 TOTAL_REQUESTS="${TOTAL_REQUESTS:-100}"
 
 # Colors
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m'
 
 echo -e "${GREEN}Load Testing - Dynamic Pricing API${NC}"
 echo "===================================="
 echo "API URL: $API_URL"
 echo "Concurrent Requests: $CONCURRENT_REQUESTS"
 echo "Total Requests: $TOTAL_REQUESTS"
 echo ""

# Create test payload
PAYLOAD=$(cat << 'EOF'
{
  "product_id": 42,
  "competitor_price": 89.99,
  "dow": 2,
   "is_weekend": 0,
   "week": 15,
   "month": 4,
   "sin_annual": 0.5,
   "cos_annual": 0.866,
   "lag_units_sold_1": 45.0,
   "lag_units_sold_7": 42.0,
   "lag_units_sold_14": 40.0,
   "roll_mean_units_7": 43.5,
   "roll_mean_units_14": 41.2,
   "roll_mean_units_28": 39.8,
   "roll_std_units_7": 5.2,
   "roll_std_units_14": 6.1,
   "roll_std_units_28": 7.3,
   "price_min": 70.0,
   "price_max": 110.0,
  "cost": 60.0,
  "min_margin_pct": 0.15,
  "optimization_method": "bayesian"
}
EOF
)

# Check if API is available
 echo -e "${YELLOW}Checking API availability...${NC}"
 if ! curl -sf "$API_URL/v1/health" > /dev/null; then
     echo -e "${RED}Error: API is not available at $API_URL${NC}"
     exit 1
 fi
 echo -e "${GREEN}✓ API is available${NC}"
 echo ""
 
 # Function to make a request
 make_request() {
     local start=$(date +%s%N)
     local response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/optimize-price" \
         -H "Content-Type: application/json" \
         -d "$PAYLOAD" 2>/dev/null)
     local end=$(date +%s%N)
     
     local http_code=$(echo "$response" | tail -n1)
     local duration=$(( (end - start) / 1000000 ))
     
     echo "$http_code,$duration"
 }
 
 # Run load test
 echo -e "${YELLOW}Starting load test...${NC}"
 START_TIME=$(date +%s)
 
 SUCCESS=0
 FAILED=0
 TOTAL_TIME=0
 MIN_TIME=999999
 MAX_TIME=0
 
 # Create temporary file for results
 TEMP_FILE=$(mktemp)
 
 # Run requests in parallel
 for i in $(seq 1 $TOTAL_REQUESTS); do
     make_request >> "$TEMP_FILE" &
     
     # Limit concurrent requests
     if [ $(( i % CONCURRENT_REQUESTS )) -eq 0 ]; then
         wait
     fi
     
     # Progress indicator
     if [ $(( i % 10 )) -eq 0 ]; then
         echo -ne "\rProgress: $i/$TOTAL_REQUESTS requests"
     fi
 done
 
 # Wait for remaining requests
 wait
 echo -e "\n"
 
 END_TIME=$(date +%s)
 ELAPSED=$(( END_TIME - START_TIME ))
 
 # Process results
 while IFS=',' read -r code duration; do
     if [ "$code" = "200" ]; then
         SUCCESS=$((SUCCESS + 1))
     else
         FAILED=$((FAILED + 1))
     fi
     
     TOTAL_TIME=$((TOTAL_TIME + duration))
     
     if [ $duration -lt $MIN_TIME ]; then
         MIN_TIME=$duration
     fi
     
     if [ $duration -gt $MAX_TIME ]; then
         MAX_TIME=$duration
     fi
 done < "$TEMP_FILE"
 
# Calculate statistics
AVG_TIME=$((TOTAL_TIME / TOTAL_REQUESTS))
RPS=$((TOTAL_REQUESTS / ELAPSED))
SUCCESS_RATE=$(python3 -c "print(f'{$SUCCESS * 100.0 / $TOTAL_REQUESTS:.2f}')")

# Display results
echo -e "${GREEN}Load Test Results${NC}"
 echo "================="
 echo ""
 echo "Total Requests: $TOTAL_REQUESTS"
 echo "Successful: $SUCCESS"
 echo "Failed: $FAILED"
 echo "Success Rate: ${SUCCESS_RATE}%"
 echo ""
 echo "Response Times:"
 echo "  Min: ${MIN_TIME}ms"
 echo "  Max: ${MAX_TIME}ms"
 echo "  Avg: ${AVG_TIME}ms"
 echo ""
 echo "Performance:"
 echo "  Total Time: ${ELAPSED}s"
 echo "  Requests/sec: $RPS"
 echo ""
 
 # Cleanup
 rm -f "$TEMP_FILE"
 
 # Exit code based on success rate
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Load test passed!${NC}"
    exit 0
elif python3 -c "exit(0 if float('$SUCCESS_RATE') >= 95 else 1)"; then
    echo -e "${YELLOW}⚠ Load test passed with warnings (${SUCCESS_RATE}% success rate)${NC}"
    exit 0
else
     echo -e "${RED}✗ Load test failed (${SUCCESS_RATE}% success rate)${NC}"
     exit 1
 fi
