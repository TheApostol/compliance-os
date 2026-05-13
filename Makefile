.PHONY: help up down logs restart ps clean seed benchmark test backend-shell db-shell

help:
	@echo "ComplianceOS — Available commands:"
	@echo ""
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
	@echo "  make backend-shell - Shell into backend container"
	@echo "  make db-shell      - psql into database"

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
