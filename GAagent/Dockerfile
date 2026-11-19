FROM python:3.12-slim AS builder
WORKDIR /src
COPY pyproject.toml MANIFEST.in requirements-core.txt requirements-personal.txt README.md ./
COPY virtual_lover_agent/ virtual_lover_agent/
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels .

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    GA_HTTP_HOST=0.0.0.0 \
    GA_HTTP_PORT=8081 \
    GA_DATA_DIR=/data

RUN groupadd --gid 10001 ga && useradd --uid 10001 --gid ga --no-create-home ga \
    && mkdir /data && chown ga:ga /data
RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels \
    python -m pip install --no-cache-dir --no-index --find-links=/wheels ga-personal-agent

USER ga
VOLUME ["/data"]
EXPOSE 8081
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health/ready', timeout=3).close()"
ENTRYPOINT ["ga"]
