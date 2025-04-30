FROM        registry.access.redhat.com/ubi9/python-311:1-1745945598@sha256:37dd30f6013d1cc6c14383486f5fbcf805aae67cf243ca842a216b2cde7f02de AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.7.1@sha256:20e139613bb5dd402d6e514e8e373180f9dbb776e55a2ed225f668b096e512c9 /uv /bin/uv
WORKDIR     /ghmirror
COPY        --chown=1001:0 pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        --chown=1001:0 ghmirror ./ghmirror
RUN         uv sync --frozen --no-cache --compile-bytecode --no-group dev --python /usr/bin/python3.11

FROM        registry.access.redhat.com/ubi9/ubi-minimal:9.5-1745855087@sha256:e1c4703364c5cb58f5462575dc90345bcd934ddc45e6c32f9c162f2b5617681c AS prod
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
COPY        --from=ghcr.io/astral-sh/uv:0.7.1@sha256:20e139613bb5dd402d6e514e8e373180f9dbb776e55a2ed225f668b096e512c9 /uv /bin/uv
USER        root
RUN         microdnf install -y make
USER        1001
COPY        --chown=1001:0 Makefile ./
COPY        --chown=1001:0 tests ./tests
ENV         UV_NO_CACHE=true
RUN         uv sync --frozen
RUN         make check

