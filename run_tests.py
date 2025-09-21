#!/usr/bin/env python3
"""
Test Runner for TGV Max Trip Planner
Run this from the project root directory
"""

import sys
import os
import subprocess

def run_test(test_file):
    """Run a single test file and capture output"""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              cwd=os.path.dirname(os.path.abspath(__file__)),
                              capture_output=True, 
                              text=True, 
                              timeout=60)
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {test_file} - PASSED")
            return True
        else:
            print(f"❌ {test_file} - FAILED (exit code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_file} - TIMEOUT (>60s)")
        return False
    except Exception as e:
        print(f"💥 {test_file} - ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("🚄 TGV Max Trip Planner - Test Suite")
    print("="*60)
    
    # List of test files to run
    test_files = [
        "tests/test_travel_time.py",
        "tests/test_duration_fix.py", 
        "tests/test_api.py",
        "tests/test_connection.py",
        "tests/test_trip_connection.py",
        "tests/test_trip.py"
    ]
    
    # Track results
    passed = 0
    failed = 0
    
    # Run each test
    for test_file in test_files:
        if os.path.exists(test_file):
            if run_test(test_file):
                passed += 1
            else:
                failed += 1
        else:
            print(f"⚠️  {test_file} - FILE NOT FOUND")
            failed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Results Summary")
    print(f"{'='*60}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        print(f"\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n💥 {failed} test(s) failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
