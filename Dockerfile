FROM        registry.access.redhat.com/ubi9/python-311:1-1749631027@sha256:ae0aa0e09d9e8fb585a019f0f1e7031d53b0def2bf1934291928b9b52aa465d5 AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.7.14@sha256:cda0fdc9b6066975ba4c791597870d18bc3a441dfc18ab24c5e888c16e15780c /uv /bin/uv
WORKDIR     /ghmirror
COPY        --chown=1001:0 pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        --chown=1001:0 ghmirror ./ghmirror
RUN         uv sync --frozen --no-cache --compile-bytecode --no-group dev --python /usr/bin/python3.11

FROM        registry.access.redhat.com/ubi9/ubi-minimal:9.6-1749489516@sha256:f172b3082a3d1bbe789a1057f03883c1113243564f01cd3020e27548b911d3f8 AS prod
RUN         microdnf upgrade -y && \
            microdnf install -y python3.11 && \
            microdnf clean all
COPY        LICENSE /licenses/LICENSE
WORKDIR     /ghmirror
RUN         chown -R 1001:0 /ghmirror
USER        1001
ENV         VIRTUAL_ENV=/ghmirror/.venv
ENV         PATH="$VIRTUAL_ENV/bin:$PATH"
COPY        --from=builder /ghmirror /ghmirror
COPY        acceptance ./acceptance
ENTRYPOINT  ["gunicorn", "ghmirror.app:APP"]
CMD         ["--workers", "1", "--threads",  "8", "--bind", "0.0.0.0:8080"]

FROM        prod AS test
COPY        --from=ghcr.io/astral-sh/uv:0.7.14@sha256:cda0fdc9b6066975ba4c791597870d18bc3a441dfc18ab24c5e888c16e15780c /uv /bin/uv
USER        root
RUN         microdnf install -y make
USER        1001
COPY        --chown=1001:0 Makefile ./
COPY        --chown=1001:0 tests ./tests
ENV         UV_NO_CACHE=true
RUN         uv sync --frozen
RUN         make check

