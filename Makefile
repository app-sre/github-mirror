develop:
	pip install --editable .
	pip install -r requirements-check.txt


check:
	black --check ghmirror tests
	isort --check-only ghmirror tests
	flake8 --ignore=E203,E501,W503 ghmirror tests
	pylint ghmirror
	python3 -m pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/

accept:
	python3 acceptance/test_basic.py

format:
	isort ghmirror tests
	black ghmirror tests
