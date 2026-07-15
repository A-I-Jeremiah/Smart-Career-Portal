# backend/Dockerfile
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first for better caching
COPY backend/requirements.txt backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code folders
COPY backend/ backend/
COPY models/ models/

# Expose port
EXPOSE 3000

# Health check using python urllib.request
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/')" || exit 1

# Run FastAPI with Uvicorn bound to all interfaces on port 3000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "3000", "--workers", "2"]
