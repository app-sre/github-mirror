check:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run pytest -v --forked --cov=ghmirror --cov-report=term-missing tests/

accept:
	python3 acceptance/test_basic.py

format:
	uv run ruff check
	uv run ruff format

local-acceptance-test:
	docker build -t github-mirror-acceptance --target prod .
	docker run --rm -it -d -p 8080:8080 --name github-mirror-test github-mirror-acceptance
	CLIENT_TOKEN=$$(cat .github_client_token) GITHUB_MIRROR_URL=http://localhost:8080 python3 acceptance/test_basic.py; docker stop github-mirror-test
