all:
	@echo
	@echo "Targets:"
	@echo "prepare:      Installs pipenv."
	@echo "install:      Installs the ghmirror package and its dependencies."
	@echo "develop:      Installs the ghmirror package, its dependencies and its development dependencies."
	@echo "check:        Runs the style check, the code check and the tests."
	@echo "run:          Runs the app server (debug mode)."
	@echo


prepare:
	pip install pipenv --upgrade

install: prepare
	pipenv install

develop: prepare
	pipenv install --dev

check:
	pipenv run flake8 ghmirror
	pipenv run pylint ghmirror
	pipenv run pipenv run pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/

run:
	pipenv run python ghmirror/app/__init__.py
