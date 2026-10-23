.PHONY: help install up down logs test test-docker lint fmt eval migrate smoke leads

API ?= http://localhost:8000

help:
	@echo "make install      install deps locally (dev extras)"
	@echo "make test         run pytest locally"
	@echo "make test-docker  run pytest inside the api container"
	@echo "make lint         ruff check"
	@echo "make fmt          ruff format + autofix"
	@echo "make up / down    start / stop the stack"
	@echo "make logs         tail api + worker logs"
	@echo "make migrate      run alembic migrations in the container"
	@echo "make smoke        POST a sample lead and fetch the result (stack must be up)"
	@echo "make leads        list recent leads"
	@echo "make eval         run the eval set in the container"

install:
	pip install -e ".[dev]"

test:
	python3 -m pytest -q tests

test-docker:
	docker compose run --rm api pytest -q

lint:
	ruff check app tests eval migrations

fmt:
	ruff check --fix app tests eval migrations
	ruff format app tests eval migrations

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	docker compose run --rm api alembic upgrade head

smoke:
	@curl -fsS $(API)/health && echo
	@id=$$(curl -fsS -X POST $(API)/leads \
		-H "Content-Type: application/json" \
		-d '{"from":"jane.doe@acme.com","subject":"Pricing for 200 seats","body":"Hi, we are a logistics company in Singapore looking for pricing on 200 seats."}' \
		| python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"); \
	echo "lead id: $$id"; sleep 5; \
	curl -fsS $(API)/leads/$$id | python3 -m json.tool

leads:
	@curl -fsS $(API)/leads | python3 -m json.tool

eval:
	docker compose run --rm api python eval/run_eval.py
