FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1788191076@sha256:1184f0930506ef3c5d2b6c34d3dee04f5cd82f6960db5ea182f7559763da144d AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.12.7@sha256:95f2aa1fe59274951cfe9b0cbc7972e879ff1004bc8945d130a32eb0dbd85945 /uv /bin/uv
ENV         UV_PROJECT_ENVIRONMENT=$APP_ROOT \
            UV_COMPILE_BYTECODE=true \
            UV_NO_CACHE=true
COPY        pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        ghmirror ./ghmirror
RUN         uv sync --frozen --no-group dev

FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1788191076@sha256:1184f0930506ef3c5d2b6c34d3dee04f5cd82f6960db5ea182f7559763da144d AS prod
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
