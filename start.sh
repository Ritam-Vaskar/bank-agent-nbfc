#!/bin/bash

echo "🚀 Starting Bank Agent System..."
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Check if ports are available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "⚠️  Port $1 is already in use"
        return 1
    fi
    return 0
}

echo "Checking ports..."
check_port 3000
check_port 5000
check_port 8000
check_port 27017
check_port 6379

echo ""
echo "Building and starting services..."
docker-compose up --build -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo ""
echo "Checking service health..."

if curl -s http://localhost:5000/health > /dev/null; then
    echo "✅ Backend is running"
else
    echo "❌ Backend is not responding"
fi

if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Agent service is running"
else
    echo "❌ Agent service is not responding"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "🎉 Bank Agent is ready!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "📱 Frontend:  http://localhost:3000"
echo "🔧 Backend:   http://localhost:5000"
echo "🤖 Agents:    http://localhost:8000"
echo ""
echo "Demo Login:"
echo "  Email:    demo@example.com"
echo "  Password: demo123"
echo ""
echo "═══════════════════════════════════════════════════"
echo ""
echo "📋 Useful commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop all:     docker-compose down"
echo "  Restart:      docker-compose restart"
echo ""
