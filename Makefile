.PHONY: install api web test lint format migrate up down backup gen-api

install:      ## Install backend and frontend dependencies
	cd apps/api && uv sync
	cd apps/web && npm install

api:          ## Run the API on :8000
	cd apps/api && uv run fastapi dev app/main.py --port 8000

web:          ## Run the web app on :3000
	cd apps/web && npm run dev

migrate:      ## Apply database migrations
	cd apps/api && uv run alembic upgrade head

gen-api:      ## Re-export the OpenAPI description and regenerate the web types
	cd apps/api && .venv/bin/python scripts/export_openapi.py
	cd apps/web && npm run gen:api

test:         ## Run backend tests
	cd apps/api && uv run pytest

lint:         ## Lint + type-check backend and frontend
	cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
	cd apps/web && npm run lint

docs-links:   ## Check that Markdown links point to real files and headings
	python3 scripts/check-doc-links.py

format:       ## Auto-format backend
	cd apps/api && uv run ruff check . --fix && uv run ruff format .

up:           ## Start the production-shaped stack (Docker)
	docker compose up -d --build

down:         ## Stop it
	docker compose down

backup:       ## Back up the database and uploaded files
	./scripts/backup.sh
