 #!/bin/bash
 # Pre-deployment validation script
 
 set -e
 
 # Colors
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m'
 
 echo -e "${GREEN}Pre-Deployment Validation${NC}"
 echo "=========================="
 echo ""
 
 ERRORS=0
 WARNINGS=0
 
 # Check 1: Model files exist
 echo -e "${YELLOW}[1/8] Checking model files...${NC}"
 if [ -f "models/demand_model.pkl" ] && [ -f "models/features.json" ]; then
     echo -e "${GREEN}✓ Model files found${NC}"
 else
     echo -e "${RED}✗ Model files missing${NC}"
     ERRORS=$((ERRORS + 1))
 fi
 
 # Check 2: Configuration files
 echo -e "\n${YELLOW}[2/8] Checking configuration files...${NC}"
 if [ -f "configs/config.prod.yaml" ] && [ -f ".env.example" ]; then
     echo -e "${GREEN}✓ Configuration files found${NC}"
 else
     echo -e "${RED}✗ Configuration files missing${NC}"
     ERRORS=$((ERRORS + 1))
 fi
 
 # Check 3: Docker files
 echo -e "\n${YELLOW}[3/8] Checking Docker files...${NC}"
 if [ -f "Dockerfile.prod" ] && [ -f "docker-compose.prod.yml" ]; then
     echo -e "${GREEN}✓ Docker files found${NC}"
 else
     echo -e "${RED}✗ Docker files missing${NC}"
     ERRORS=$((ERRORS + 1))
 fi
 
 # Check 4: Required scripts
 echo -e "\n${YELLOW}[4/8] Checking deployment scripts...${NC}"
 REQUIRED_SCRIPTS=("deploy.sh" "backup_database.sh" "restore_database.sh" "health_check.sh")
 for script in "${REQUIRED_SCRIPTS[@]}"; do
     if [ -f "scripts/$script" ] && [ -x "scripts/$script" ]; then
         echo -e "${GREEN}✓ $script${NC}"
     else
         echo -e "${RED}✗ $script missing or not executable${NC}"
         ERRORS=$((ERRORS + 1))
     fi
 done
 
 # Check 5: Model performance
echo -e "\n${YELLOW}[5/8] Checking model performance...${NC}"
if [ -f "reports/training_metrics.json" ]; then
    R2=$(python3 -c "import json; print(json.load(open('reports/training_metrics.json'))['R2'])")
    if python3 -c "exit(0 if float('$R2') >= 0.40 else 1)"; then
        echo -e "${GREEN}✓ Model R² = $R2 (>= 0.40)${NC}"
    else
        echo -e "${RED}✗ Model R² = $R2 (< 0.40)${NC}"
         ERRORS=$((ERRORS + 1))
     fi
 else
     echo -e "${YELLOW}⚠ No training metrics found${NC}"
     WARNINGS=$((WARNINGS + 1))
 fi
 
 # Check 6: Dependencies
 echo -e "\n${YELLOW}[6/8] Checking dependencies...${NC}"
 if [ -f "requirements.txt" ]; then
     echo -e "${GREEN}✓ requirements.txt found${NC}"
     # Check for critical dependencies
     CRITICAL_DEPS=("fastapi" "uvicorn" "xgboost" "pandas")
     for dep in "${CRITICAL_DEPS[@]}"; do
         if grep -q "$dep" requirements.txt; then
             echo -e "${GREEN}  ✓ $dep${NC}"
         else
             echo -e "${RED}  ✗ $dep missing${NC}"
             ERRORS=$((ERRORS + 1))
         fi
     done
 else
     echo -e "${RED}✗ requirements.txt missing${NC}"
     ERRORS=$((ERRORS + 1))
 fi
 
 # Check 7: Documentation
 echo -e "\n${YELLOW}[7/8] Checking documentation...${NC}"
 DOCS=("README.md" "DEPLOYMENT.md" "docs/API.md" "docs/OPERATIONS.md")
 for doc in "${DOCS[@]}"; do
     if [ -f "$doc" ]; then
         echo -e "${GREEN}✓ $doc${NC}"
     else
         echo -e "${YELLOW}⚠ $doc missing${NC}"
         WARNINGS=$((WARNINGS + 1))
     fi
 done
 
 # Check 8: Git status
 echo -e "\n${YELLOW}[8/8] Checking git status...${NC}"
 if [ -d ".git" ]; then
     if [ -z "$(git status --porcelain)" ]; then
         echo -e "${GREEN}✓ Working directory clean${NC}"
     else
         echo -e "${YELLOW}⚠ Uncommitted changes detected${NC}"
         WARNINGS=$((WARNINGS + 1))
     fi
     
     BRANCH=$(git branch --show-current)
     echo -e "${GREEN}✓ Current branch: $BRANCH${NC}"
 else
     echo -e "${YELLOW}⚠ Not a git repository${NC}"
     WARNINGS=$((WARNINGS + 1))
 fi
 
 # Summary
 echo ""
 echo "=========================="
 echo -e "${GREEN}Validation Summary${NC}"
 echo "=========================="
 
 if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
     echo -e "${GREEN}✓ All checks passed!${NC}"
     echo -e "${GREEN}Ready for deployment${NC}"
     exit 0
 elif [ $ERRORS -eq 0 ]; then
     echo -e "${YELLOW}⚠ $WARNINGS warning(s)${NC}"
     echo -e "${YELLOW}Deployment possible but review warnings${NC}"
     exit 0
 else
     echo -e "${RED}✗ $ERRORS error(s), $WARNINGS warning(s)${NC}"
     echo -e "${RED}Fix errors before deployment${NC}"
     exit 1
 fi
