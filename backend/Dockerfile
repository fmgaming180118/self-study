FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install native dependencies used by Python packages and circuit simulations.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ngspice \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Run the API as an unprivileged user
RUN adduser --disabled-password --gecos '' appuser

COPY --chown=appuser:appuser . .
RUN chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Health check using python urllib
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live', timeout=2)"]

ENTRYPOINT ["./docker-entrypoint.sh"]

# Production ASGI server with Gunicorn multi-worker
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
