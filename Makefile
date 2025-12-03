# Use zsh explicitly, ensuring consistent behavior on macOS
SHELL := /bin/zsh

VENV := ./.venv/bin
UVICORN := $(VENV)/uvicorn
CELERY := $(VENV)/celery
PYTHON := $(VENV)/python

# Services
REDIS_SERVER := redis-server

# Env - you can put these in a .env file and load them
MYSQL_USER := root
MYSQL_PASSWORD := Shivam@12345
MYSQL_HOST := localhost
MYSQL_PORT := 3306
MYSQL_DATABASE := school
SECRET_KEY := your-secret-key
ALGORITHM := HS256
ACCESS_TOKEN_EXPIRE_MINUTES := 30

# Make tasks run quietly; set DEBUG=1 to show commands
MAKEFLAGS += --silent

export MYSQL_USER MYSQL_PASSWORD MYSQL_HOST MYSQL_PORT MYSQL_DATABASE SECRET_KEY ALGORITHM ACCESS_TOKEN_EXPIRE_MINUTES

.PHONY: start-fastapi start-celery start-redis check-ollama start-all stop-all restart-fastapi status

start-fastapi:
	@mkdir -p logs
	@echo "Starting FastAPI (uvicorn)..."
	[ -x "$(UVICORN)" ] || (echo "Error: uvicorn not found in venv" && exit 1)
	nohup $(UVICORN) student.api.main:app --reload --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 & echo $$! > .uvicorn.pid
	@echo "FastAPI started, logs -> logs/uvicorn.log"

start-celery:
	@mkdir -p logs
	@echo "Starting Celery worker..."
	[ -x "$(CELERY)" ] || (echo "Error: celery not found in venv" && exit 1)
	nohup $(CELERY) -A student.core.celerey_app.celery_app worker --loglevel=info > logs/celery.log 2>&1 & echo $$! > .celery.pid
	@echo "Celery started, logs -> logs/celery.log"

start-redis:
	@echo "Ensure Redis server is running..."
	redis-cli ping > /dev/null 2>&1 && echo 'Redis already running' || $(REDIS_SERVER) --daemonize yes && echo 'Redis started'

check-ollama:
	@pgrep -f ollama > /dev/null && echo 'Ollama is running' || echo 'Warning: Ollama is not running. Start it with: ollama serve'

start-all: start-redis check-ollama start-celery start-fastapi
	@echo "All services started (start-redis, start-celery, start-fastapi)."

stop-fastapi:
	@echo "Stopping FastAPI..."
	@if [ -f .uvicorn.pid ]; then kill -9 $$(cat .uvicorn.pid) 2>/dev/null || true; rm -f .uvicorn.pid; fi

stop-celery:
	@echo "Stopping Celery..."
	@if [ -f .celery.pid ]; then kill -9 $$(cat .celery.pid) 2>/dev/null || true; rm -f .celery.pid; fi

stop-all: stop-fastapi stop-celery
	@echo "Stopped FastAPI & Celery (Redis and Ollama left untouched)."

restart-fastapi: stop-fastapi start-fastapi

status:
	@echo "FastAPI:"; [ -f .uvicorn.pid ] && echo "PID: $$(cat .uvicorn.pid)" || echo "Not running"
	@echo "Celery:"; [ -f .celery.pid ] && echo "PID: $$(cat .celery.pid)" || echo "Not running"
	@pgrep -f ollama > /dev/null && echo "Ollama: running" || echo "Ollama: not running"
	@redis-cli ping > /dev/null 2>&1 && echo "Redis: running" || echo "Redis: not running"
