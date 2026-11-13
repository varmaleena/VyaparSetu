.PHONY: install lint typecheck test run-local infra migrate seed check-redis docker-build deploy-cloud-run

install:
	uv sync --extra lint

lint:
	uv run --extra lint ruff check .

typecheck:
	uv run --extra lint mypy --follow-imports=silent app migrations invoice_intake_playground

test:
	uv run pytest

run-local:
	uv run uvicorn app.fast_api_app:app

infra:
	docker compose up -d --wait

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m app.services.seed_data

check-redis:
	uv run python -m app.services.redis_service

docker-build:
	docker build -t vyaparsetu .

deploy-cloud-run:
	gcloud run deploy vyaparsetu --source .
