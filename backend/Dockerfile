# Backend API image.  Built by `docker compose --profile app up --build` (see README).
# Local models (BGE-M3, NLI, reranker) need PyTorch: build with INSTALL_ML=true (~2 GB more).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

ARG INSTALL_ML=false
COPY requirements.txt requirements-ml.txt ./
RUN pip install -r requirements.txt \
 && if [ "$INSTALL_ML" = "true" ]; then \
      pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-ml.txt; \
    fi

COPY alembic.ini ./
COPY alembic ./alembic
COPY alembic_auth ./alembic_auth
COPY app ./app
COPY scripts ./scripts

# Run as an unprivileged user; uploads and model caches live in mounted volumes
RUN useradd --create-home --uid 10001 app \
 && mkdir -p /data/uploads /home/app/.cache/huggingface \
 && chown -R app:app /data /home/app/.cache
USER app

ENV UPLOAD_DIR=/data/uploads \
    EXPERIMENTS_DIR=/experiments
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2)"

# Apply database migrations, then serve. One worker: rate limits and model caches are
# per process (see app/core/security.py).
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.migrate_auth && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
