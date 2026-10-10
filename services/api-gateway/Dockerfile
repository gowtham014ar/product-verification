FROM python:3.12-slim

WORKDIR /app

COPY services/common /app/common
COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api-gateway/ .

RUN mkdir -p /app/logs

ENV SERVICE_NAME=api-gateway \
    LOG_DIR=/app/logs

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
