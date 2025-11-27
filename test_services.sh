#!/bin/bash
# Test script to verify all services and API endpoints

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          FastAPI Student Management - Service Check          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test Redis
echo -n "1. Redis Service......... "
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not Running${NC}"
fi

# Test Ollama
echo -n "2. Ollama Service........ "
if pgrep -f ollama > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running (PID $(pgrep -f ollama))${NC}"
else
    echo -e "${YELLOW}⚠ Not Running (AI Q&A will not work)${NC}"
fi

# Test Celery
echo -n "3. Celery Worker......... "
if pgrep -f 'celery.*worker' > /dev/null 2>&1; then
    WORKER_COUNT=$(pgrep -f 'celery.*worker' | wc -l | xargs)
    echo -e "${GREEN}✓ Running ($WORKER_COUNT processes)${NC}"
else
    echo -e "${RED}✗ Not Running${NC}"
fi

# Test FastAPI
echo -n "4. FastAPI Server........ "
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Running on http://localhost:8000${NC}"
else
    echo -e "${RED}✗ Not Running${NC}"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    API Endpoint Tests                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Test root endpoint
echo -n "5. Root Endpoint......... "
RESPONSE=$(curl -s http://localhost:8000/)
if echo "$RESPONSE" | grep -q "Student API"; then
    echo -e "${GREEN}✓ Responding${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
fi

# Test docs endpoint
echo -n "6. API Documentation..... "
if curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Available at /docs${NC}"
else
    echo -e "${RED}✗ Not Available${NC}"
fi

# Test OpenAPI schema
echo -n "7. OpenAPI Schema........ "
if curl -s http://localhost:8000/openapi.json | grep -q "openapi"; then
    echo -e "${GREEN}✓ Valid${NC}"
else
    echo -e "${RED}✗ Invalid${NC}"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                         Summary                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo "API Root:          http://localhost:8000/"
echo ""
echo "Available Endpoints:"
echo "  • POST /api/register      - Register new user"
echo "  • POST /api/login         - Login and get JWT token"
echo "  • GET  /api/students      - List all students (requires JWT)"
echo "  • POST /api/students      - Create student (requires JWT)"
echo "  • POST /api/bulk-upload   - Upload CSV/Excel (requires JWT)"
echo "  • POST /api/upload-and-process - Upload document with AI"
echo "  • POST /api/ask           - Ask questions about documents"
echo ""
