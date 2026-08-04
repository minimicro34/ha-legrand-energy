PYTHON ?= python3
.PHONY: help compile format format-check lint typecheck test check clean

help:
	@echo "Available targets:"
	@echo "  compile       Compile Python sources"
	@echo "  format        Format the code with Ruff"
	@echo "  format-check  Verify formatting without modifying files"
	@echo "  lint          Run Ruff lint"
	@echo "  typecheck     Run mypy"
	@echo "  test          Run pytest"
	@echo "  check         Run the complete CI locally"
	@echo "  clean         Remove Python cache files"

compile:
	$(PYTHON) -m compileall custom_components

format:
	ruff format .

format-check:
	ruff format --check .

lint:
	ruff check .

typecheck:
	mypy custom_components/legrand_energy

test:
	pytest -q

check: compile format-check lint typecheck test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type f -name ".DS_Store" -delete