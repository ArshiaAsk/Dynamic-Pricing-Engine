 #!/bin/bash
 # Database backup script for SQLite
 
 set -e
 
 # Configuration
 DB_FILE="${DATABASE_URL:-data.db}"
 BACKUP_DIR="${BACKUP_DIR:-backups/database}"
 RETENTION_DAYS="${DATABASE_BACKUP_RETENTION_DAYS:-7}"
 TIMESTAMP=$(date +%Y%m%d_%H%M%S)
 BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.db"
 
 # Colors for output
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m' # No Color
 
 echo -e "${GREEN}Starting database backup...${NC}"
 
 # Create backup directory if it doesn't exist
 mkdir -p "$BACKUP_DIR"
 
 # Check if database file exists
 if [ ! -f "$DB_FILE" ]; then
     echo -e "${RED}Error: Database file not found: $DB_FILE${NC}"
     exit 1
 fi
 
 # Create backup
 echo "Backing up $DB_FILE to $BACKUP_FILE"
 cp "$DB_FILE" "$BACKUP_FILE"
 
 # Compress backup
 echo "Compressing backup..."
 gzip "$BACKUP_FILE"
 BACKUP_FILE="${BACKUP_FILE}.gz"
 
 # Verify backup
 if [ -f "$BACKUP_FILE" ]; then
     SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
     echo -e "${GREEN}Backup created successfully: $BACKUP_FILE (${SIZE})${NC}"
 else
     echo -e "${RED}Error: Backup file not created${NC}"
     exit 1
 fi
 
 # Clean old backups
 echo "Cleaning backups older than $RETENTION_DAYS days..."
 find "$BACKUP_DIR" -name "backup_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete
 
 # List recent backups
 echo -e "\n${YELLOW}Recent backups:${NC}"
 ls -lh "$BACKUP_DIR" | tail -5
 
 echo -e "\n${GREEN}Backup completed successfully!${NC}"
