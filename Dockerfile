# Streamlit application container for the Smart Career Portal
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install system dependencies required to build Python packages
RUN for i in 1 2 3; do \
      apt-get update && break || (test $i -lt 3 && sleep 5); \
    done && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Copy requirements first for caching, then install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source and model assets
COPY . .

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/')" || exit 1

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0", "--server.headless", "true"]
