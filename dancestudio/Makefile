.PHONY: up down migrate seed fmt lint test ensure-env

ENV_FILE=deploy/env/.env
ENV_EXAMPLE=deploy/env/.env.example

ensure-env:
	@if [ ! -f $(ENV_FILE) ]; then \
		if [ -f $(ENV_EXAMPLE) ]; then \
			cp $(ENV_EXAMPLE) $(ENV_FILE); \
			echo "Created $(ENV_FILE) from $(ENV_EXAMPLE). Update secrets as needed."; \
		else \
			echo "Missing $(ENV_EXAMPLE). Please create $(ENV_FILE) manually."; \
			exit 1; \
		fi; \
	fi
up: ensure-env
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

