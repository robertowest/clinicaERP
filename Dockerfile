FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# se invoca con "sh" (no "./docker-entrypoint.sh") porque docker-compose monta el proyecto
# como bind volume en desarrollo: el bit +x del build no sobrevive al montaje del host.
ENTRYPOINT ["sh", "docker-entrypoint.sh"]
