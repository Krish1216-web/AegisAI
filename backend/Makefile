.PHONY: install run test migrate migrations clean help

help:
	@echo "AegisAI Backend Console Commands:"
	@echo "  install    - Install packages using Poetry"
	@echo "  run        - Execute local FastAPI development server"
	@echo "  test       - Execute pytest test suites"
	@echo "  migrations - Generate database migration changes"
	@echo "  migrate    - Apply pending migrations to PostgreSQL database"
	@echo "  clean      - Clean pycache logs and coverage reports"

install:
	poetry install

run:
	poetry run python app/main.py

test:
	poetry run pytest --cov=app tests/

migrations:
	poetry run alembic revision --autogenerate -m "Auto migration"

migrate:
	poetry run alembic upgrade head

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov
