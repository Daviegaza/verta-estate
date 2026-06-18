FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /usr/local

COPY . .

RUN mkdir -p /app/uploads && chown -R nobody:nogroup /app/uploads

USER nobody

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use Gunicorn with Uvicorn workers in production,
# fall back to uvicorn if GUNICORN_WORKERS is not set
CMD ["sh", "-c", "if [ \"$GUNICORN_WORKERS\" ]; then exec gunicorn -c app/core/gunicorn_conf.py app.main:app; else exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4; fi"]
