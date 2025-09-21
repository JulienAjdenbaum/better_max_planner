#!/usr/bin/env python3
"""
Database Testing Helper Script

This script provides utilities for safely testing database transforms
without modifying the original database.
"""

import os
import sys
import shutil
import argparse
from datetime import datetime
from sqlalchemy import create_engine, text

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils import update_db

# Database paths
ORIGINAL_DB = 'data/tgvmax.db'
TEST_DB = 'data/tgvmax_test.db'
BACKUP_DB = 'data/tgvmax_backup.db'


def create_backup():
    """Create a backup of the original database"""
    if os.path.exists(ORIGINAL_DB):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"data/tgvmax_backup_{timestamp}.db"
        shutil.copy2(ORIGINAL_DB, backup_file)
        print(f"✅ Created backup: {backup_file}")
        return backup_file
    else:
        print(f"❌ Original database not found: {ORIGINAL_DB}")
        return None


def create_test_database():
    """Create a test copy of the original database"""
    if os.path.exists(ORIGINAL_DB):
        # Create backup if it doesn't exist
        if not os.path.exists(BACKUP_DB):
            shutil.copy2(ORIGINAL_DB, BACKUP_DB)
            print(f"✅ Created permanent backup: {BACKUP_DB}")
        
        # Create test database
        shutil.copy2(ORIGINAL_DB, TEST_DB)
        print(f"✅ Created test database: {TEST_DB}")
        return True
    else:
        print(f"❌ Original database not found: {ORIGINAL_DB}")
        return False


def reset_test_database():
    """Reset test database to original state"""
    if os.path.exists(ORIGINAL_DB):
        shutil.copy2(ORIGINAL_DB, TEST_DB)
        print(f"✅ Reset test database from original")
        return True
    else:
        print(f"❌ Cannot reset: original database not found")
        return False


def compare_databases():
    """Compare original and test databases"""
    if not os.path.exists(ORIGINAL_DB) or not os.path.exists(TEST_DB):
        print("❌ Both original and test databases must exist for comparison")
        return
    
    original_engine = create_engine(f'sqlite:///{ORIGINAL_DB}')
    test_engine = create_engine(f'sqlite:///{TEST_DB}')
    
    print("🔍 Database Comparison:")
    
    for name, engine in [("Original", original_engine), ("Test", test_engine)]:
        with engine.connect() as conn:
            # Get row count
            result = conn.execute(text("SELECT COUNT(*) FROM TGVMAX"))
            row_count = result.fetchone()[0]
            
            # Get column info
            result = conn.execute(text("PRAGMA table_info(TGVMAX)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"  {name} DB: {row_count:,} rows, {len(columns)} columns")
            print(f"    Columns: {columns}")


def download_fresh_data():
    """Download fresh data from SNCF API"""
    print("📥 Downloading fresh data from SNCF...")
    try:
        engine = create_engine(f'sqlite:///{ORIGINAL_DB}')
        update_db(engine)
        print("✅ Fresh data downloaded successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to download fresh data: {e}")
        return False


def show_database_info(db_path=ORIGINAL_DB):
    """Show information about a database"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    engine = create_engine(f'sqlite:///{db_path}')
    
    print(f"📊 Database Info: {db_path}")
    print(f"   File size: {os.path.getsize(db_path) / 1024 / 1024:.1f} MB")
    print(f"   Modified: {datetime.fromtimestamp(os.path.getmtime(db_path))}")
    
    with engine.connect() as conn:
        # Get table info
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result.fetchall()]
        print(f"   Tables: {tables}")
        
        # For each table, show row count
        for table in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.fetchone()[0]
            print(f"     {table}: {count:,} rows")
        
        # Show column info for TGVMAX
        if 'TGVMAX' in tables:
            result = conn.execute(text("PRAGMA table_info(TGVMAX)"))
            columns = [(row[1], row[2]) for row in result.fetchall()]
            print(f"   TGVMAX columns:")
            for col_name, col_type in columns:
                print(f"     {col_name}: {col_type}")


def main():
    parser = argparse.ArgumentParser(description='Database Testing Helper')
    parser.add_argument('action', choices=[
        'create-test', 'reset-test', 'backup', 'compare', 
        'download', 'info', 'info-test'
    ], help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'create-test':
        create_test_database()
    elif args.action == 'reset-test':
        reset_test_database()
    elif args.action == 'backup':
        create_backup()
    elif args.action == 'compare':
        compare_databases()
    elif args.action == 'download':
        download_fresh_data()
    elif args.action == 'info':
        show_database_info(ORIGINAL_DB)
    elif args.action == 'info-test':
        show_database_info(TEST_DB)


if __name__ == '__main__':
    main()
