#!/bin/bash

# TGV Max Planner Docker Deployment Script

echo "🚄 Building TGV Max Planner Docker image..."

# Build the Docker image
docker build -t tgvmax-planner .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    
    echo "🚀 Starting TGV Max Planner container..."
    
    # Stop existing container if running
    docker stop tgvmax-planner 2>/dev/null || true
    docker rm tgvmax-planner 2>/dev/null || true
    
    # Run the container
    docker run -d \
        --name tgvmax-planner \
        -p 5000:5000 \
        -v $(pwd)/tgvmax.db:/app/tgvmax.db \
        --restart unless-stopped \
        tgvmax-planner
    
    if [ $? -eq 0 ]; then
        echo "✅ TGV Max Planner is now running!"
        echo "🌐 Access the application at: http://localhost:5000"
        echo ""
        echo "📊 Container status:"
        docker ps --filter name=tgvmax-planner
    else
        echo "❌ Failed to start container"
        exit 1
    fi
else
    echo "❌ Failed to build Docker image"
    exit 1
fi 