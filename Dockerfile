FROM        registry.access.redhat.com/ubi8/python-311:1-56.1712880527 as builder
WORKDIR     /ghmirror
RUN         python3 -m venv venv
ENV         VIRTUAL_ENV=/ghmirror/venv
ENV         PATH="$VIRTUAL_ENV/bin:$PATH"
COPY        --chown=1001:0 setup.py VERSION ./
RUN         pip install .

FROM        builder as test
COPY        --chown=1001:0 requirements-check.txt ./
RUN         pip install -r requirements-check.txt
COPY        --chown=1001:0 . ./
ENTRYPOINT  ["make"]
CMD         ["check"]

FROM        registry.access.redhat.com/ubi8/ubi-minimal:8.9-1161.1715068733
RUN         microdnf upgrade -y && \
            microdnf install -y python3.11 && \
            microdnf clean all
USER        1001
WORKDIR     /ghmirror
ENV         VIRTUAL_ENV=/ghmirror/venv
ENV         PATH="$VIRTUAL_ENV/bin:$PATH"
COPY        --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY        --chown=1001:0 . ./
ENTRYPOINT  ["gunicorn", "ghmirror.app:APP"]
CMD         ["--workers", "1", "--threads",  "8", "--bind", "0.0.0.0:8080"]
