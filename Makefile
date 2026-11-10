.PHONY: install api web test lint format migrate up down backup

install:      ## Install backend and frontend dependencies
	cd apps/api && uv sync
	cd apps/web && npm install

api:          ## Run the API on :8000
	cd apps/api && uv run fastapi dev app/main.py --port 8000

web:          ## Run the web app on :3000
	cd apps/web && npm run dev

migrate:      ## Apply database migrations
	cd apps/api && uv run alembic upgrade head

test:         ## Run backend tests
	cd apps/api && uv run pytest

lint:         ## Lint + type-check backend and frontend
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd apps/web && npm run lint

format:       ## Auto-format backend
	cd apps/api && uv run ruff check . --fix && uv run ruff format .

up:           ## Start the production-shaped stack (Docker)
	docker compose up -d --build

down:         ## Stop it
	docker compose down

backup:       ## Back up the database and uploaded files
	./scripts/backup.sh
