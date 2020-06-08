develop:
	pip install --editable .
	pip install -r requirements-check.txt


check:
	flake8 ghmirror
	pylint ghmirror
	pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/
