# TGV Max Trip Planner

A web application for finding optimal day trips using TGV Max passes. The app helps users discover the best destinations with maximum time at destination and detailed trip information.

## Features

- 🚄 Find optimal day trip destinations from any TGV station
- 📅 Date picker with Monday-first calendar
- 🎯 Grouped destinations with average travel time and max time at destination
- 📊 Detailed trip information with train numbers and axes
- 🎨 Modern, responsive UI with searchable station dropdown
- 🔍 Strict day trip filtering (no overnight trips)

## Docker Deployment

### Quick Start

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **Or use the deployment script:**
   ```bash
   ./deploy.sh
   ```

3. **Access the application:**
   ```
   http://localhost:5000
   ```

### Manual Docker Commands

**Build the image:**
```bash
docker build -t tgvmax-planner .
```

**Run the container:**
```bash
docker run -d \
  --name tgvmax-planner \
  -p 5000:5000 \
  -v $(pwd)/tgvmax.db:/app/tgvmax.db \
  --restart unless-stopped \
  tgvmax-planner
```

**Stop the container:**
```bash
docker stop tgvmax-planner
docker rm tgvmax-planner
```

## Safety Benefits of Docker

### 🔒 Security
- **Isolation**: The app runs in its own container, isolated from the host system
- **Non-root user**: Container runs as a non-privileged user (appuser)
- **Reduced attack surface**: Only necessary dependencies are included
- **Resource limits**: Container has limited access to host resources

### 🛡️ Production Features
- **Health checks**: Automatic monitoring of application health
- **Restart policy**: Container automatically restarts on failure
- **Volume persistence**: Database is mounted as a volume for data persistence
- **Environment variables**: Configurable via environment variables
- **Port mapping**: Only necessary port (5000) is exposed

### 📦 Consistency
- **Same environment**: Identical runtime environment across development and production
- **Dependency management**: All Python packages are bundled
- **Version control**: Exact versions of all dependencies are locked

## Development

### Local Development
```bash
pip install -r requirements.txt
python app.py
```

### Database Updates
The application uses a SQLite database (`tgvmax.db`) that can be updated by running:
```python
from utils import update_db, engine
update_db(engine)
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

## Logging System

The application implements a comprehensive logging system that captures detailed information about every request and response for monitoring, debugging, and performance analysis.

### Log Files

The application creates two separate log files:

1. **Main Application Log**: `/var/log/tgvmax_app.log`
   - Contains application-level logs, processing details, and errors
   - Includes endpoint-specific timing and processing information

2. **Request Timing Log**: `/var/log/tgvmax_requests.log`
   - Dedicated file for request/response timing data
   - Contains complete request and response information for every HTTP request

### Logging Configuration

The logging system is configured in `logging_config.py` with the following features:

- **Rotating file handlers**: Logs are automatically rotated when they reach 1MB
- **Backup retention**: Keeps 5 backup files for historical analysis
- **Separate loggers**: Different loggers for application logs vs. request timing
- **Detailed formatting**: Includes timestamps, log levels, and source information

### What Gets Logged

#### Request Information
- **HTTP Method**: GET, POST, etc.
- **Request Path**: The endpoint being accessed
- **Status Code**: HTTP response status (200, 404, 500, etc.)
- **Duration**: Total request processing time in seconds
- **Client IP**: Remote address of the client
- **User Agent**: Browser/client information
- **Query String**: URL parameters
- **Request Headers**: All headers (excluding Authorization and Cookie for privacy)
- **Request Body**: JSON data for POST/PUT requests

#### Response Information
- **JSON Responses**: Complete JSON response data for API endpoints
- **HTML Responses**: First 500 characters of HTML responses for web pages
- **Error Responses**: Full error information including stack traces

#### Processing Details
- **Endpoint-specific timing**: Time spent in specific endpoint logic
- **Database query timing**: Time for database operations
- **Processing results**: Number of results found, processing statistics

### Example Log Entries

#### Request Timing Log Entry
```
2025-07-11 03:49:52,610 - INFO - request_timing - [app.py:42] - Request: POST /get_destinations - Status: 200 - Duration: 0.122s - IP: 127.0.0.1 - User-Agent: curl/7.88.1 - Query:  - JSON: {'date': '2025-07-11', 'stations': ['PARIS (intramuros)']} - Headers: {'Host': 'localhost:5001', 'User-Agent': 'curl/7.88.1', 'Accept': '*/*', 'Content-Type': 'application/json', 'Content-Length': '58'} - Response: {'destinations': [...], 'success': True}
```

#### Application Log Entry
```
2025-07-11 03:49:52,366 - INFO - utils - Planification d'un voyage à la journée le 2025-07-11
2025-07-11 03:49:52,528 - INFO - __main__ - Found 2 destinations in 0.161s
```

### Logging Middleware

The application uses Flask middleware to automatically log every request:

```python
@app.before_request
def before_request():
    request.start_time = time.time()

@app.after_request
def after_request(response):
    # Log complete request/response information
    # Including timing, headers, body, and response data
```

### Performance Monitoring

The logging system enables:

- **Response Time Analysis**: Track which endpoints are slowest
- **Error Tracking**: Identify which requests fail and why
- **Usage Patterns**: See which endpoints are most used
- **Client Analysis**: Monitor different user agents and IPs
- **Data Flow**: Complete audit trail of all requests and responses

### Log Analysis

To analyze the logs:

```bash
# View recent requests
tail -f /var/log/tgvmax_requests.log

# Find slow requests (>1 second)
grep "Duration: [1-9]\." /var/log/tgvmax_requests.log

# Count requests by endpoint
grep "Request:" /var/log/tgvmax_requests.log | awk '{print $8}' | sort | uniq -c

# Find errors
grep "Status: [4-5]" /var/log/tgvmax_requests.log
```

### Privacy Considerations

The logging system is designed with privacy in mind:
- **Sensitive headers excluded**: Authorization and Cookie headers are not logged
- **Configurable redaction**: Additional fields can be excluded as needed
- **Local storage**: Logs are stored locally and not transmitted externally

## Monitoring

Check container health:
```bash
docker ps
docker logs tgvmax-planner
```

## Troubleshooting

1. **Port already in use**: Change the port mapping in docker-compose.yml
2. **Database issues**: Ensure tgvmax.db file exists and is writable
3. **Build failures**: Check that all files are present and requirements.txt is up to date 