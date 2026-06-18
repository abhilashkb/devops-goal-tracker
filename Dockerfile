FROM python:3.11-slim

# Set a working directory
WORKDIR /app

# Environment: prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Create an unprivileged user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Expose the port
EXPOSE 5000

# Use gunicorn for production; bind to all interfaces
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
