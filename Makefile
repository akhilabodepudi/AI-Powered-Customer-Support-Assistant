.PHONY: dev test lint seed docker

dev:
	docker compose up --build

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

seed:
	cd backend && python -m app.seed

docker:
	docker compose config && docker compose build

