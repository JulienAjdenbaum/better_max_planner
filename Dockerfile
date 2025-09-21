# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security and set up log directory permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5163

# Set environment variables
ENV FLASK_APP=main.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5163/ || exit 1

# Run the application
CMD ["python", "main.py"] 