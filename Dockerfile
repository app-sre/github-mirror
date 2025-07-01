FROM        registry.access.redhat.com/ubi9/python-311:1-1750969934@sha256:47f3998eaf36beb97789d1fe52db4811e02338cc55266638ebb992df48adea86 AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.7.18@sha256:1bf08b18814f11cc37b5a1566c11570b4bf660f59225cd4e0f3b18d9fb04c277 /uv /bin/uv
WORKDIR     /ghmirror
COPY        --chown=1001:0 pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        --chown=1001:0 ghmirror ./ghmirror
RUN         uv sync --frozen --no-cache --compile-bytecode --no-group dev --python /usr/bin/python3.11

FROM        registry.access.redhat.com/ubi9/ubi-minimal:9.6-1751286687@sha256:383329bf9c4f968e87e85d30ba3a5cb988a3bbde28b8e4932dcd3a025fd9c98c AS prod
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
COPY        --from=ghcr.io/astral-sh/uv:0.7.18@sha256:1bf08b18814f11cc37b5a1566c11570b4bf660f59225cd4e0f3b18d9fb04c277 /uv /bin/uv
USER        root
RUN         microdnf install -y make
USER        1001
COPY        --chown=1001:0 Makefile ./
COPY        --chown=1001:0 tests ./tests
ENV         UV_NO_CACHE=true
RUN         uv sync --frozen
RUN         make check

