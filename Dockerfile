### Multi-stage Dockerfile
### Builder: install build deps and dependencies into a venv
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# Install system build dependencies (only in builder)
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install into an isolated venv
COPY requirements.txt ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# Copy the full application into the builder (so bytecode can be generated if needed)
COPY . /app

### Final image: copy the venv and app files only, keep image small
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production
WORKDIR /app

# Copy runtime virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app

# Create an unprivileged user and set ownership
RUN useradd --create-home appuser \
 && chown -R appuser /app /opt/venv


COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

USER appuser

EXPOSE 5000

# Use the start script instead of directly calling gunicorn
CMD ["./start.sh"]