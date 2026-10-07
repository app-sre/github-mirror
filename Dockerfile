FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1791290410@sha256:06f7f76a5a718f240534d62974d1708b2985ecddb245e8c9e69eac792e075293 AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /bin/uv
ENV         UV_PROJECT_ENVIRONMENT=$APP_ROOT \
            UV_COMPILE_BYTECODE=true \
            UV_NO_CACHE=true
COPY        pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        ghmirror ./ghmirror
RUN         uv sync --frozen --no-group dev

FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1791290410@sha256:06f7f76a5a718f240534d62974d1708b2985ecddb245e8c9e69eac792e075293 AS prod
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
