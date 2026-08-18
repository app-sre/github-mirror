FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1787002610@sha256:b6cc4d6c56a139b763af6cb9cd6b838d0f8ed5a67caadfa3418e68dec6ab755f AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /bin/uv
ENV         UV_PROJECT_ENVIRONMENT=$APP_ROOT \
            UV_COMPILE_BYTECODE=true \
            UV_NO_CACHE=true
COPY        pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        ghmirror ./ghmirror
RUN         uv sync --frozen --no-group dev

FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1787002610@sha256:b6cc4d6c56a139b763af6cb9cd6b838d0f8ed5a67caadfa3418e68dec6ab755f AS prod
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
