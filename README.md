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