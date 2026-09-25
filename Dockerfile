FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1790163097@sha256:6ea702d478f66cf78fb694d2fc2634f353c3f49c54fbbe58ba39288a59c83aa7 AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 /uv /bin/uv
ENV         UV_PROJECT_ENVIRONMENT=$APP_ROOT \
            UV_COMPILE_BYTECODE=true \
            UV_NO_CACHE=true
COPY        pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        ghmirror ./ghmirror
RUN         uv sync --frozen --no-group dev

FROM        registry.access.redhat.com/ubi10/python-314-minimal:10.2-1790163097@sha256:6ea702d478f66cf78fb694d2fc2634f353c3f49c54fbbe58ba39288a59c83aa7 AS prod
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
