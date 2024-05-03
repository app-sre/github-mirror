FROM        registry.access.redhat.com/ubi8/python-311:1-25

WORKDIR     /ghmirror

COPY        --chown=1001:0 . ./

RUN         pip install .
RUN         pip install gunicorn

ENTRYPOINT  ["gunicorn", "ghmirror.app:APP"]
CMD         ["--workers", "1", "--threads",  "8", "--bind", "0.0.0.0:8080"]
