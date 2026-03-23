FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY agents/ ./agents/
COPY config/ ./config/
COPY vault/ ./vault/
COPY frontend/ ./frontend/
COPY run_prod.py ./

# Runtime data directory (mount a volume here to persist across containers)
RUN mkdir -p data

EXPOSE 8300

# Use run_prod.py if it exists, otherwise fall back to run.py
CMD ["python", "run_prod.py"]
