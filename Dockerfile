FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends git build-essential && \
    pip install --no-cache-dir pyunifi requests schedule && \
    apt-get purge -y --auto-remove git build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY update_blocklist.py .

CMD ["python", "update_blocklist.py"]