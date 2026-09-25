# zikrflow-vakitler: Diyanet ilçe vakitlerini haftada bir çeker, statik JSON olarak servis eder.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY scripts ./scripts
COPY iller.json overrides.json ./
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /data/vakitler

ENV VAKITLER_DATA=/data \
    FETCH_INTERVAL_DAYS=7 \
    PYTHONUNBUFFERED=1

EXPOSE 80
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s CMD curl -fsS http://127.0.0.1/healthz || exit 1
CMD ["/entrypoint.sh"]
