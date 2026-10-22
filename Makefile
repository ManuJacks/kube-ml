PYTHON ?= python3
VENV ?= .venv
BIN = $(VENV)/bin

.PHONY: help venv install run-dev test lint clean docker-build

help:
	@echo "Available commands:"
	@echo "  make venv        Create Python virtual environment"
	@echo "  make install     Install package and dependencies in venv"
	@echo "  make run-dev     Run Django development server"
	@echo "  make test        Execute automated test suite"
	@echo "  make docker-build Build Docker container image"
	@echo "  make clean       Remove temporary build and cache files"

venv:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

install: venv
	$(BIN)/pip install -e .

run-dev:
	set -a; [ ! -f .env.local ] || . ./.env.local; set +a; $(BIN)/python manage.py runserver 0.0.0.0:8000

test:
	$(BIN)/python manage.py test core

docker-build:
	docker build -t kube-ml-app:v1 .

clean:
	rm -rf build/ dist/ *.egg-info __pycache__ */__pycache__ */*/__pycache__ .pytest_cache
