#!/usr/bin/env python3
"""
Database Optimization Script for TGV Max Planner
This script fixes soudure and coupure non autorisée issues and cleans up the database.
Can be run independently or as part of the update process.
"""

import os
import sys
import logging
from datetime import datetime
# Add the parent directory to the Python path so we can import src modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import optimize_database_complete, engine
from src.logging_config import setup_logging

setup_logging(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'tgvmax_optimization.log'))
logger = logging.getLogger(__name__)

def main():
    """Main function to optimize the database."""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting database optimization process")
        logger.info(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if database exists and is writable
        db_path = 'data/tgvmax.db'
        if not os.path.exists(db_path):
            logger.error(f"❌ Database file {db_path} not found")
            return 1

        if not os.access(db_path, os.W_OK):
            logger.error(f"❌ Database file {db_path} is not writable")
            return 1
        
        # Run the optimization
        result = optimize_database_complete(engine)
        
        # Log final summary
        logger.info("=" * 60)
        logger.info("🎉 DATABASE OPTIMIZATION COMPLETED SUCCESSFULLY")
        logger.info(f"📈 Results: +{result['new_available_trips']:,} available trips")
        logger.info(f"🔧 Coupure fixes: {result['coupure_fixes']:,}")
        logger.info(f"🔧 Soudure fixes: {result['soudure_fixes']:,}")
        logger.info(f"🧹 Trips deleted: {result['trips_deleted']:,}")
        logger.info(f"📊 Final availability: {result['final_availability_rate']:.1f}%")
        logger.info(f"⏱️  Total time: {result['total_time']:.3f}s")
        logger.info(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.exception(f"❌ Error during database optimization: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
