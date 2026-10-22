# Dockerfile
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

# Install dependencies with CPU-only torch to keep image size lean and builds fast
RUN pip install --no-cache-dir \
    'django>=4.2' \
    'numpy>=1.24.0' \
    'torch>=2.0.0' \
    --extra-index-url https://download.pytorch.org/whl/cpu
# Copy application source code
COPY pyproject.toml README.md manage.py ./
COPY config/ ./config/
COPY core/ ./core/
COPY mcp/ ./mcp/

# Install the application package
RUN pip install --no-cache-dir -e .

USER app

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"]
