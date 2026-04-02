.PHONY: setup test lint format release mutate audit validate hassfest

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

mutate:
	@echo "Running mutation testing (this will take a while)..."
	@.venv/bin/python3 -m mutmut run

audit:
	@echo "Running vulnerability audit on dependencies..."
	@.venv/bin/python3 -m pip_audit -r requirements-dev.txt --ignore-vuln CVE-2025-67221 --ignore-vuln CVE-2026-32597 --ignore-vuln CVE-2026-27448 --ignore-vuln CVE-2026-27459 --ignore-vuln CVE-2026-4539 --ignore-vuln CVE-2026-25645 --ignore-vuln CVE-2026-34073

hassfest:
	@echo "Running Home Assistant Hassfest validation via Docker..."
	@docker run --rm -v $(PWD):/github/workspace ghcr.io/home-assistant/actions/hassfest:latest

validate:
	@echo "Validating translations..."
	@.venv/bin/python3 tools/check_translations.py
	@echo "Validating release notes..."
	@.venv/bin/python3 tools/check_release_notes.py custom_components/teltonika_rms/manifest.json CHANGELOG.md

release:
	@tools/publish_release.sh
