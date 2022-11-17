FROM        registry.access.redhat.com/ubi8/ubi-minimal

RUN         microdnf install python3.9 make shadow-utils && microdnf clean all
RUN         python3 -m pip install --no-cache-dir --upgrade pip setuptools

ARG         CONTAINER_UID=1000
RUN         adduser --uid ${CONTAINER_UID} --user-group ghmirror
RUN         mkdir /ghmirror && chown ghmirror:ghmirror /ghmirror

USER        ghmirror
ENV         PATH=${PATH}:/home/ghmirror/.local/bin

WORKDIR     /ghmirror

COPY        --chown=ghmirror:ghmirror . ./

RUN         pip install --no-cache-dir --user .
RUN         pip install --no-cache-dir --user gunicorn

ENTRYPOINT  ["gunicorn", "ghmirror.app:APP"]
CMD         ["--workers", "1", "--threads",  "8", "--bind", "0.0.0.0:8080"]
