check:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/

accept:
	python3 acceptance/test_basic.py

format:
	uv run ruff check
	uv run ruff format
