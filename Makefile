develop:
	pip install --editable .
	pip install -r requirements-check.txt


check:
	ruff check --no-fix
	ruff format --check
	python3 -m pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/

accept:
	python3 acceptance/test_basic.py

format:
	ruff check
	ruff format
