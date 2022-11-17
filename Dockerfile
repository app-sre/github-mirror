FROM        registry.access.redhat.com/ubi8/ubi-minimal

RUN         microdnf install python3.9 && microdnf clean all
RUN         python3 -m pip install --no-cache-dir --upgrade pip setuptools

USER        root

WORKDIR     /ghmirror

COPY        . ./

RUN         pip install .
RUN         pip install gunicorn

ENTRYPOINT  ["gunicorn", "ghmirror.app:APP"]
CMD         ["--workers", "1", "--threads",  "8", "--bind", "0.0.0.0:8080"]
