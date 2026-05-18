.PHONY: help init up down logs restart ps clean seed benchmark test backend-shell db-shell migrate makemigrations db-migrate-status smoke-test ci-test prometheus grafana

help:
	@echo "ComplianceOS — Available commands:"
	@echo ""
	@echo "  make init        - Bootstrap .env from .env.example (first-time setup)"
	@echo "  make up          - Start all services (db, qdrant, redis, backend, frontend)"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - Tail logs from all services"
	@echo "  make ps          - Show running containers"
	@echo "  make restart     - Restart all services"
	@echo "  make clean       - Stop + remove volumes (WIPES DATA)"
	@echo ""
	@echo "  make seed        - Load demo regulatory data"
	@echo "  make benchmark   - Run NVIDIA NIM benchmark with your API key"
	@echo "  make test        - Run backend tests"
	@echo ""
	@echo "  make migrate              - Apply all pending Alembic migrations"
	@echo "  make makemigrations msg=  - Generate a new Alembic migration (provide msg=)"
	@echo "  make db-migrate-status    - Show current Alembic revision"
	@echo ""
	@echo "  make backend-shell - Shell into backend container"
	@echo "  make db-shell      - psql into database"
	@echo ""
	@echo "## Testing"
	@echo "  make smoke-test  - Trigger crawler + verify DB (requires running stack)"
	@echo "  make ci-test     - Run pytest inside backend container"

init:
	@if [ -f .env ]; then echo "⚠ .env already exists — skipping"; else cp .env.example .env && echo "✓ .env created. Set NVIDIA_API_KEY in .env before running make up"; fi

up:
	@test -f .env || (echo "⚠️  .env not found. Run: cp .env.example .env  and add your NVIDIA_API_KEY"; exit 1)
	docker compose up -d --build
	@echo ""
	@echo "✓ Services starting:"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  API docs:  http://localhost:8000/docs"
	@echo "  Qdrant:    http://localhost:6333/dashboard"
	@echo ""
	@echo "  Run 'make logs' to follow logs."

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

restart:
	docker compose restart

clean:
	docker compose down -v
	@echo "⚠️  All data wiped."

seed:
	docker compose exec backend python -m scripts.seed_demo

benchmark:
	@test -f .env || (echo "⚠️  .env not found"; exit 1)
	docker compose exec backend python -m scripts.run_benchmark

test:
	docker compose exec backend pytest -v

backend-shell:
	docker compose exec backend bash

db-shell:
	docker compose exec db psql -U complianceos -d complianceos

migrate:
	docker compose exec backend alembic upgrade head

makemigrations:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

db-migrate-status:
	docker compose exec backend alembic current

## Testing

smoke-test:
	@echo "▶  Triggering crawler run..."
	@curl -s -X POST http://localhost:8000/api/v1/crawler/run-now \
		-H "Content-Type: application/json" \
		-H "X-Tenant-Id: polkorp" \
		-d '{"regulator": "all"}' | python3 -m json.tool; \
	CURL_EXIT=$$?; \
	echo ""; \
	echo "⏳ Waiting 5s for crawler to finish..."; \
	sleep 5; \
	echo ""; \
	echo "▶  Latest regulations in DB:"; \
	docker compose exec db psql -U complianceos -c \
		"SELECT id, regulator, code, created_at FROM regulations ORDER BY created_at DESC LIMIT 5;"; \
	DB_EXIT=$$?; \
	echo ""; \
	if [ $$CURL_EXIT -eq 0 ] && [ $$DB_EXIT -eq 0 ]; then \
		echo "✅ smoke-test PASSED"; \
	else \
		echo "❌ smoke-test FAILED (curl=$$CURL_EXIT db=$$DB_EXIT)"; \
		exit 1; \
	fi

ci-test:
	docker compose exec backend python -m pytest tests/ -x -q --tb=short

## Observability

prometheus:  ## Open Prometheus UI
	open http://localhost:9090 || xdg-open http://localhost:9090

grafana:  ## Open Grafana UI (admin / complianceos)
	open http://localhost:3001 || xdg-open http://localhost:3001
