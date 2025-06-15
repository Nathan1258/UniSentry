FROM python:3.9-slim

WORKDIR /app

RUN pip install --no-cache-dir requests schedule

COPY update_blocklist.py .

CMD ["python", "update_blocklist.py"]
