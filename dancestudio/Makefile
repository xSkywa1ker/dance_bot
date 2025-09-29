.PHONY: up down migrate seed fmt lint test

up:
	 docker compose -f deploy/docker-compose.yml up -d --build

down:
	 docker compose -f deploy/docker-compose.yml down

migrate:
	 docker compose -f deploy/docker-compose.yml run --rm backend alembic upgrade head

seed:
	 docker compose -f deploy/docker-compose.yml run --rm backend python -m app.services.seed

fmt:
	 poetry run black .

lint:
	 poetry run ruff check .

test:
	 docker compose -f deploy/docker-compose.yml run --rm backend pytest

