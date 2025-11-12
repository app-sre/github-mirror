FROM        registry.access.redhat.com/ubi9/python-311:1-1762229832@sha256:b0944e92caced75b386b8c4f9960e11010e2dad14ba329e7a93b8ff150af0a9a AS builder
COPY        --from=ghcr.io/astral-sh/uv:0.9.8@sha256:08f409e1d53e77dfb5b65c788491f8ca70fe1d2d459f41c89afa2fcbef998abe /uv /bin/uv
WORKDIR     /ghmirror
COPY        --chown=1001:0 pyproject.toml uv.lock ./
RUN         uv lock --locked
COPY        --chown=1001:0 ghmirror ./ghmirror
RUN         uv sync --frozen --no-cache --compile-bytecode --no-group dev --python /usr/bin/python3.11

FROM        registry.access.redhat.com/ubi9/ubi-minimal:9.7-1762180032@sha256:2ddd6e10383981c7d10e4966a7c0edce7159f8ca91b1691cafabc78bae79d8f8 AS prod
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
COPY        --from=ghcr.io/astral-sh/uv:0.9.8@sha256:08f409e1d53e77dfb5b65c788491f8ca70fe1d2d459f41c89afa2fcbef998abe /uv /bin/uv
USER        root
RUN         microdnf install -y make
USER        1001
COPY        --chown=1001:0 Makefile ./
COPY        --chown=1001:0 tests ./tests
ENV         UV_NO_CACHE=true
RUN         uv sync --frozen
RUN         make check

