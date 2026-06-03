 #!/bin/bash
 # Database restore script for SQLite
 
 set -e
 
 # Configuration
 DB_FILE="${DATABASE_URL:-data.db}"
 BACKUP_DIR="${BACKUP_DIR:-backups/database}"
 
 # Colors for output
 GREEN='\033[0;32m'
 YELLOW='\033[1;33m'
 RED='\033[0;31m'
 NC='\033[0m' # No Color
 
 echo -e "${GREEN}Database Restore Utility${NC}"
 echo "================================"
 
 # Check if backup directory exists
 if [ ! -d "$BACKUP_DIR" ]; then
     echo -e "${RED}Error: Backup directory not found: $BACKUP_DIR${NC}"
     exit 1
 fi
 
 # List available backups
 echo -e "\n${YELLOW}Available backups:${NC}"
 backups=($(ls -t "$BACKUP_DIR"/backup_*.db.gz 2>/dev/null))
 
 if [ ${#backups[@]} -eq 0 ]; then
     echo -e "${RED}No backups found in $BACKUP_DIR${NC}"
     exit 1
 fi
 
 # Display backups with numbers
 for i in "${!backups[@]}"; do
     backup_file="${backups[$i]}"
     size=$(du -h "$backup_file" | cut -f1)
     date=$(basename "$backup_file" | sed 's/backup_\(.*\)\.db\.gz/\1/')
     echo "$((i+1)). $date (${size})"
 done
 
 # Get user selection
 echo -e "\n${YELLOW}Enter backup number to restore (or 'q' to quit):${NC}"
 read -r selection
 
 if [ "$selection" = "q" ]; then
     echo "Restore cancelled"
     exit 0
 fi
 
 # Validate selection
 if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#backups[@]} ]; then
     echo -e "${RED}Invalid selection${NC}"
     exit 1
 fi
 
 # Get selected backup
 selected_backup="${backups[$((selection-1))]}"
 echo -e "\n${YELLOW}Selected backup: $(basename $selected_backup)${NC}"
 
 # Confirm restore
 echo -e "${RED}WARNING: This will overwrite the current database!${NC}"
 echo -e "${YELLOW}Current database will be backed up first.${NC}"
 echo -e "\nType 'yes' to continue:"
 read -r confirm
 
 if [ "$confirm" != "yes" ]; then
     echo "Restore cancelled"
     exit 0
 fi
 
 # Backup current database
 if [ -f "$DB_FILE" ]; then
     echo "Backing up current database..."
     TIMESTAMP=$(date +%Y%m%d_%H%M%S)
     cp "$DB_FILE" "${DB_FILE}.before_restore_${TIMESTAMP}"
     echo -e "${GREEN}Current database backed up to: ${DB_FILE}.before_restore_${TIMESTAMP}${NC}"
 fi
 
 # Restore backup
 echo "Restoring backup..."
 gunzip -c "$selected_backup" > "$DB_FILE"
 
 # Verify restore
 if [ -f "$DB_FILE" ]; then
     SIZE=$(du -h "$DB_FILE" | cut -f1)
     echo -e "\n${GREEN}Database restored successfully!${NC}"
     echo "Restored database: $DB_FILE (${SIZE})"
 else
     echo -e "${RED}Error: Restore failed${NC}"
     exit 1
 fi
 
 echo -e "\n${GREEN}Restore completed!${NC}"
