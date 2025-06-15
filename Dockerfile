FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends git build-essentials && \
    pip install --upgrade pip && \
    pip install --no-cache-dir requests schedule && \
    git clone https://github.com/ubiquiti-community/py-unifi.git /tmp/py-unifi && \
    cd /tmp/py-unifi && python setup.py install && \
    cd / && rm -rf /tmp/py-unifi && \
    apt-get purge -y --auto-remove git && \
    rm -rf /var/lib/apt/lists/*

COPY update_blocklist.py .

CMD ["python", "update_blocklist.py"]
