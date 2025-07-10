#!/usr/bin/env python3
"""
Database update script for TGV Max Planner
This script updates the database with fresh data from SNCF API.
Designed to be run by cron every 12 hours.
"""

import os
import sys
import logging
from datetime import datetime
from utils import update_db, engine

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/tgvmax_update.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Main function to update the database."""
    try:
        logging.info("Starting database update process")
        
        # Check if database file exists and is writable
        db_path = 'tgvmax.db'
        if not os.path.exists(db_path):
            logging.error(f"Database file {db_path} not found")
            return 1
        
        if not os.access(db_path, os.W_OK):
            logging.error(f"Database file {db_path} is not writable")
            return 1
        
        # Update the database
        update_db(engine)
        
        logging.info("Database update completed successfully")
        return 0
        
    except Exception as e:
        logging.error(f"Error during database update: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 