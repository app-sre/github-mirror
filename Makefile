all:
	@echo
	@echo "Targets:"
	@echo "check:        Runs the style check, the code check and the tests."
	@echo "run-app:      Runs the app server (debug mode)."
	@echo

install:
	pip install pipenv

check: install
	pipenv install --dev
	pipenv run flake8 ghmirror
	pipenv run pylint ghmirror
	pipenv run pipenv run pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/

run-app: install
	pipenv install
	pipenv run python ghmirror/app/__init__.py
