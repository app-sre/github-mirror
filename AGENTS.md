# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GitHub Mirror is a Python Flask application that caches GitHub API responses and implements conditional requests. It serves as a proxy to reduce API quota consumption by serving cached responses when GitHub returns a 304 (Not Modified) status code.

## Setup
- **Install dependencies**: `uv sync --dev` or use the legacy method described in `docs/devel_guide.md`
- **Run development server**: `python ghmirror/app/__init__.py` (starts on http://127.0.0.1:8080)

## Formatting

To format code, run `make format`.

## Unit and Linting Tests

To run unit and linting tests, you can use `make check`

## Acceptance Test

Make sure the file `.github_client_token` exists in the project. It must be provided by the user.

Before running any acceptance test, make sure that the `.github_client_token` file was created by the user. If not, prompt the user to set it with the secret stored in our vault at `app-interface/app-sre-stage-01/github-mirror-stage/acceptance-tests`.

Once `.github_client_token` file was created by the user, you can execute acceptance tests locally by using `make local-acceptance-test`.

The acceptance test can be considered successful, if every command in the make target exits successfully.

## Architecture

### Core Components
- **`ghmirror/app/`**: Flask application entry point and route handlers
- **`ghmirror/core/`**: Core business logic for mirror requests and responses
- **`ghmirror/data_structures/`**: Cache implementations (in-memory and Redis)
- **`ghmirror/decorators/`**: Request validation decorators (user authentication)
- **`ghmirror/utils/`**: Utility modules including request session management

### Key Features
- **Conditional Requests**: Implements GitHub's conditional request pattern using ETags
- **Cache Backends**: Supports both in-memory and Redis caching (controlled by `CACHE_TYPE` env var)
- **User Validation**: Optional user authorization via `GITHUB_USERS` environment variable
- **Offline Mode**: Built-in detection for GitHub API outages with cache fallback
- **Metrics**: Prometheus metrics endpoint at `/metrics`

### Configuration
- Uses `pyproject.toml` for Python packaging and tool configuration
- Ruff for linting/formatting with comprehensive rule set
- Coverage threshold set to 98%
- Python 3.11 required

### Cache Architecture
The application uses a monostate pattern for cache management with separate implementations for in-memory and Redis backends. Cache keys are based on request URLs and ETags from GitHub responses.

## Commit Standards
- First, before adding or committing anything, always make sure that Unit, Format and Acceptance tests have been run successfully
- Use `Assisted-by:` instead of `Co-Authored-By:`
- Remove whitespace-only lines
- Use double newlines for EOF
