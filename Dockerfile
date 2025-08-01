FROM        registry.access.redhat.com/ubi9/python-311:1-1753967630@sha256:617152a2d5600081b00f3d4bb0e430b681d932e53e3053fa6a4c54861d3fec83 AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.8.4@sha256:40775a79214294fb51d097c9117592f193bcfdfc634f4daa0e169ee965b10ef0 /uv /bin/uv
WORKDIR     /ghmirror
COPY        --chown=1001:0 pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        --chown=1001:0 ghmirror ./ghmirror
RUN         uv sync --frozen --no-cache --compile-bytecode --no-group dev --python /usr/bin/python3.11

FROM        registry.access.redhat.com/ubi9/ubi-minimal:9.6-1754000177@sha256:0d7cfb0704f6d389942150a01a20cb182dc8ca872004ebf19010e2b622818926 AS prod
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
COPY        --from=ghcr.io/astral-sh/uv:0.8.4@sha256:40775a79214294fb51d097c9117592f193bcfdfc634f4daa0e169ee965b10ef0 /uv /bin/uv
USER        root
RUN         microdnf install -y make
USER        1001
COPY        --chown=1001:0 Makefile ./
COPY        --chown=1001:0 tests ./tests
ENV         UV_NO_CACHE=true
RUN         uv sync --frozen
RUN         make check

