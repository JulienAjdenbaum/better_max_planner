#!/usr/bin/env python3
"""
Script to clean up past trips from the TGVMAX database.
This script is designed to be run by cron every 3 minutes.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path setup
from src.utils import remove_past_trips
from src.logging_config import setup_logging

def main():
    """Main function to clean up past trips"""
    try:
        # Setup logging with dedicated cleanup log file
        cleanup_log_path = os.path.join(str(project_root), 'logs', 'tgvmax_cleanup_internal.log')
        setup_logging(cleanup_log_path)
        
        # Run the cleanup
        result = remove_past_trips()
        
        # Exit with appropriate code
        if result["removed"] > 0:
            print(f"✅ Cleanup successful: removed {result['removed']} past trips in {result['elapsed']:.3f}s")
        else:
            print(f"✅ No past trips to remove (checked {result['before']:,} trips in {result['elapsed']:.3f}s)")
            
        return 0
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
