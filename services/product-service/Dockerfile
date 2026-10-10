FROM python:3.12-slim

WORKDIR /app

COPY services/common /app/common
COPY services/product-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/product-service/ .

RUN mkdir -p /app/logs

ENV SERVICE_NAME=product-service \
    LOG_DIR=/app/logs

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
