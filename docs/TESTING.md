# Testing Guide - TGV Max Trip Planner

This document explains how to run tests for the TGV Max Trip Planner application.

## Test Structure

The test suite is organized as follows:

```
tests/
├── test_api.py              # API endpoint testing
├── test_connection.py       # Database connection and query testing
├── test_day_trips.py        # Day trips functionality testing
├── test_duration_fix.py     # Duration calculation testing
├── test_travel_time.py      # Travel time calculation testing
├── test_trip_connection.py  # Trip connection search testing
├── test_trip.py            # Complex trip planning testing
└── Untitled.ipynb         # Jupyter notebook for interactive testing
```

## Running Tests

### Option 1: Run All Tests (Recommended)

Use the test runner script to run all tests:

```bash
python run_tests.py
```

This will:
- Run all test files automatically
- Show progress and results for each test
- Provide a summary with pass/fail counts
- Exit with status 0 if all tests pass, 1 if any fail

### Option 2: Run Individual Tests

Run specific test files directly:

```bash
# Test travel time calculations
python tests/test_travel_time.py

# Test trip connections
python tests/test_trip_connection.py

# Test duration calculations
python tests/test_duration_fix.py

# Test day trips functionality
python tests/test_day_trips.py

# Test database connections
python tests/test_connection.py

# Test API endpoints (requires running application)
python tests/test_api.py

# Test complex trip planning
python tests/test_trip.py
```

### Option 3: Run from Tests Directory

You can also run tests from within the tests directory:

```bash
cd tests
python test_travel_time.py
python test_trip_connection.py
# ... etc
```

## Test Requirements

### Prerequisites

1. **Database**: The application database (`data/tgvmax.db`) must exist
2. **Python Environment**: All dependencies from `requirements.txt` must be installed
3. **Project Structure**: Tests expect the hierarchical file structure with `src/` directory

### Environment Setup

If running tests in a new environment:

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure database exists (or run the application once to create it)
ls data/tgvmax.db
```

## Test Descriptions

### `test_travel_time.py`
- Tests travel time calculations between stations
- Validates handling of overnight trips (crossing midnight)
- Tests multi-segment journey duration calculations

### `test_duration_fix.py`  
- Tests duration calculation fixes for edge cases
- Validates proper handling of negative duration calculations
- Tests formatting of duration strings

### `test_connection.py`
- Tests database connectivity and queries
- Validates station data availability
- Tests connection search functionality with real database data

### `test_day_trips.py`
- Tests the main day trips functionality (`find_optimal_destinations`)
- Uses today's date and PARIS (intramuros) as origin
- Validates day trip destination finding and optimization
- Tests multiple Paris area stations for comparison

### `test_trip_connection.py`
- Tests the main trip connection search function
- Uses real search parameters (ILE DE FRANCE → AVIGNON TGV)
- Validates trip results formatting and data structure

### `test_trip.py`
- Tests complex trip planning scenarios
- Tests multi-connection trip searches
- Validates afternoon trip filtering
- Tests station group expansion

### `test_api.py`
- Tests API endpoints (requires running application)
- Validates HTTP response codes and JSON formatting
- Tests error handling

## Understanding Test Output

### Successful Test Run
```
🚄 TGV Max Trip Planner - Test Suite
============================================================
✅ tests/test_travel_time.py - PASSED
✅ tests/test_duration_fix.py - PASSED
...
============================================================
✅ Passed: 6
❌ Failed: 0
📊 Total:  6
🎉 All tests passed!
```

### Failed Test Run
```
❌ tests/test_example.py - FAILED (exit code: 1)
============================================================
✅ Passed: 5
❌ Failed: 1
📊 Total:  6
💥 1 test(s) failed!
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: 
   - Ensure you're running from the project root directory
   - Check that the `src/` directory structure is intact

2. **Database Errors**:
   - Verify `data/tgvmax.db` exists
   - Check database permissions

3. **API Test Failures**:
   - Ensure the application is running on port 5163
   - Check that the Docker container is healthy

### Debug Mode

For detailed debugging, run individual tests with Python's verbose mode:

```bash
python -v tests/test_trip_connection.py
```

## Integration with Development

### Before Committing Code
Always run the full test suite:

```bash
python run_tests.py
```

### Continuous Integration
The test runner returns appropriate exit codes for CI/CD integration:
- Exit code 0: All tests passed
- Exit code 1: One or more tests failed

### Adding New Tests
When adding new test files:
1. Place them in the `tests/` directory
2. Use the naming convention `test_*.py`
3. Add appropriate imports for the `src/` module structure
4. Update the `run_tests.py` file to include the new test

## Performance Notes

- Individual tests typically run in 1-5 seconds
- Full test suite completes in under 30 seconds
- Database-heavy tests may take longer depending on data size
- API tests require the application to be running
