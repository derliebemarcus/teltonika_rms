.PHONY: setup test lint format release

setup:
	@echo "Setting up development environment..."
	@python3 -m venv .venv
	@.venv/bin/python3 -m pip install -r requirements-dev.txt
	@tools/install_git_hooks.sh
	@echo "Setup complete. Git hooks are activated."

test:
	@.venv/bin/python3 -m pytest tests/unit tests/ha

lint:
	@.venv/bin/python3 -m ruff check .
	@.venv/bin/python3 -m mypy .

format:
	@.venv/bin/python3 -m ruff format .
	@.venv/bin/python3 -m ruff check --fix .

release:
	@tools/publish_release.sh
