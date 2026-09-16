FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1789015071@sha256:1f0d7848ed6c8f9e051ff14675ffcc8c98eaf2a66fc7a473d20ba8a4efefc408 AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.12.15@sha256:62f8c047d0a0e9ece6b53fc63df902585a67a47a7f318ddec4a37db586edc8e3 /uv /bin/uv
ENV         UV_PROJECT_ENVIRONMENT=$APP_ROOT \
            UV_COMPILE_BYTECODE=true \
            UV_NO_CACHE=true
COPY        pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        ghmirror ./ghmirror
RUN         uv sync --frozen --no-group dev

FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1789015071@sha256:1f0d7848ed6c8f9e051ff14675ffcc8c98eaf2a66fc7a473d20ba8a4efefc408 AS prod
USER        0
RUN         microdnf upgrade -y && \
            microdnf clean all
COPY        LICENSE /licenses/LICENSE
USER        1001
COPY        --from=builder /opt/app-root /opt/app-root
COPY        acceptance ./acceptance
ENTRYPOINT  ["gunicorn", "ghmirror.app:APP"]
CMD         ["--workers", "1", "--threads",  "8", "--bind", "0.0.0.0:8080"]

FROM        builder AS test
USER        root
RUN         microdnf install -y make
USER        1001
COPY        Makefile ./
RUN         uv sync --frozen
COPY        tests ./tests
RUN         make check
