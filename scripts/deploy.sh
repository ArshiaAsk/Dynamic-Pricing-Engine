 #!/bin/bash
 # Deployment script for AWS EC2
 
 set -e
 
 # Colors
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m'
 
 # Configuration
 REMOTE_USER="${DEPLOY_USER:-ubuntu}"
 REMOTE_HOST="${DEPLOY_HOST}"
 REMOTE_DIR="${DEPLOY_DIR:-/home/ubuntu/pricing-engine}"
 SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"
 
 echo -e "${GREEN}Dynamic Pricing Engine - Deployment Script${NC}"
 echo "=========================================="
 
 # Check required variables
 if [ -z "$REMOTE_HOST" ]; then
     echo -e "${RED}Error: DEPLOY_HOST environment variable not set${NC}"
     echo "Usage: DEPLOY_HOST=your-ec2-ip.com ./scripts/deploy.sh"
     exit 1
 fi
 
 echo -e "\n${YELLOW}Deployment Configuration:${NC}"
 echo "Remote Host: $REMOTE_HOST"
 echo "Remote User: $REMOTE_USER"
 echo "Remote Directory: $REMOTE_DIR"
 
 # Confirm deployment
 echo -e "\n${YELLOW}Continue with deployment? (yes/no)${NC}"
 read -r confirm
 if [ "$confirm" != "yes" ]; then
     echo "Deployment cancelled"
     exit 0
 fi
 
 # Test SSH connection
 echo -e "\n${GREEN}[1/6] Testing SSH connection...${NC}"
 if ! ssh -i "$SSH_KEY" -o ConnectTimeout=10 "$REMOTE_USER@$REMOTE_HOST" "echo 'Connection successful'"; then
     echo -e "${RED}Error: Cannot connect to remote host${NC}"
     exit 1
 fi
 
 # Create remote directory
 echo -e "\n${GREEN}[2/6] Creating remote directory...${NC}"
 ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "mkdir -p $REMOTE_DIR"
 
 # Sync files
 echo -e "\n${GREEN}[3/6] Syncing files to remote server...${NC}"
 rsync -avz --progress \
     --exclude '.git' \
     --exclude '__pycache__' \
     --exclude '*.pyc' \
     --exclude 'logs/' \
     --exclude 'mlruns/' \
     --exclude '.pytest_cache' \
     --exclude 'notebooks/' \
     -e "ssh -i $SSH_KEY" \
     ./ "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"
 
 # Build and start containers
 echo -e "\n${GREEN}[4/6] Building Docker images...${NC}"
 ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
 cd $REMOTE_DIR
 docker-compose -f docker-compose.prod.yml build
 EOF
 
 echo -e "\n${GREEN}[5/6] Starting services...${NC}"
 ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" << 'EOF'
 cd $REMOTE_DIR
 docker-compose -f docker-compose.prod.yml down
 docker-compose -f docker-compose.prod.yml up -d
 EOF
 
 # Wait for services to start
 echo -e "\n${GREEN}[6/6] Waiting for services to be healthy...${NC}"
 sleep 10
 
 # Verify deployment
 echo -e "\n${YELLOW}Verifying deployment...${NC}"
 if ssh -i "$SSH_KEY" "$REMOTE_USER@$REMOTE_HOST" "curl -f http://localhost:8000/v1/health"; then
     echo -e "\n${GREEN}✓ Deployment successful!${NC}"
     echo -e "\nAPI is available at: http://$REMOTE_HOST"
     echo -e "Health check: http://$REMOTE_HOST/v1/health"
     echo -e "API docs: http://$REMOTE_HOST/docs"
 else
     echo -e "\n${RED}✗ Deployment verification failed${NC}"
     echo "Check logs with: ssh $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs'"
     exit 1
 fi
 
 echo -e "\n${GREEN}Deployment completed!${NC}"
