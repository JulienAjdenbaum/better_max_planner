# TGV Max Trip Planner

A web application for finding optimal day trips using TGV Max passes. The app helps users discover the best destinations with maximum time at destination and detailed trip information.

## Project Structure

```
better_max_planner/
├── src/                    # Core application source code
│   ├── __init__.py        # Package initialization
│   ├── app.py             # Main Flask application
│   ├── utils.py           # Utility functions and database operations
│   └── logging_config.py  # Logging configuration
├── tests/                  # Test files
│   ├── test_api.py
│   ├── test_connection.py
│   ├── test_duration_fix.py
│   ├── test_travel_time.py
│   ├── test_trip_connection.py
│   ├── test_trip.py
│   └── Untitled.ipynb     # Jupyter notebook for testing
├── scripts/               # Utility and maintenance scripts
│   ├── check_connections.py
│   ├── check_data.py
│   ├── debug_travel_time.py
│   ├── update_database.py
│   └── deploy.sh          # Docker deployment script
├── config/                # Configuration files
│   ├── station_groups.json
│   └── crontab_entry
├── data/                  # Data files
│   └── tgvmax.db         # SQLite database
├── docs/                  # Documentation
│   └── TODO.md           # Task list
├── templates/             # Flask templates
│   └── index.html
├── logs/                  # Log files (auto-generated)
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose configuration
└── README.md           # This file
```

## Features

- 🚄 Find optimal day trip destinations from any TGV station
- 📅 Date picker with Monday-first calendar
- 🎯 Grouped destinations with average travel time and max time at destination
- 📊 Detailed trip information with train numbers and axes
- 🎨 Modern, responsive UI with searchable station dropdown
- 🔍 Strict day trip filtering (no overnight trips)

## Quick Start

### Using Docker (Recommended)

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **Or use the deployment script:**
   ```bash
   ./scripts/deploy.sh
   ```

3. **Access the application:**
   ```
   http://localhost:5000
   ```

### Local Development

```bash
pip install -r requirements.txt
python main.py
```

## Architecture

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript with modern UI
- **Container**: Docker with Python 3.11-slim base image

## Environment Variables

- `FLASK_ENV`: Set to 'production' for production mode
- `PORT`: Port number (default: 5000)
- `PYTHONUNBUFFERED`: Set to 1 for immediate log output

## Database Updates

The application uses a SQLite database (`data/tgvmax.db`) that can be updated by running:

```bash
python scripts/update_database.py
```

## Logging System

The application implements a comprehensive logging system:

- **Main Application Log**: `logs/tgvmax_app.log`
- **Request Timing Log**: `logs/tgvmax_requests.log`

Both logs use rotating file handlers with 5 backup files.

## Monitoring

Check container health:
```bash
docker ps
docker logs tgvmax-planner
```

## Development

### Running Tests

```bash
# Run all tests (recommended)
python run_tests.py

# Or run individual test files
python tests/test_travel_time.py
python tests/test_trip_connection.py
python tests/test_connection.py
```

See [docs/TESTING.md](docs/TESTING.md) for detailed testing documentation.

### Maintenance Scripts

```bash
# Check data integrity
python scripts/check_data.py

# Check connections
python scripts/check_connections.py

# Debug travel time calculations
python scripts/debug_travel_time.py
```

## Troubleshooting

1. **Port already in use**: Change the port mapping in docker-compose.yml
2. **Database issues**: Ensure `data/tgvmax.db` file exists and is writable
3. **Build failures**: Check that all files are present and requirements.txt is up to date
4. **Import errors**: Ensure you're running from the project root directory
