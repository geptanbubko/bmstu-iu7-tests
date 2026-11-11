# Тестируемая система (стенд): Flask GUI + JSON API над SQLite-хранилищем в томе /data.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app
RUN pip install "flask>=3.0" "flask-wtf>=1.2"

COPY src ./src
COPY db ./db
COPY ci/stand_cleanup.py ./ci/stand_cleanup.py
COPY docker/app.config.ini ./config.ini
COPY docker/stand-entrypoint.sh ./stand-entrypoint.sh

VOLUME ["/data"]
EXPOSE 5000

HEALTHCHECK --interval=2s --timeout=3s --start-period=5s --retries=30 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/v1/health', timeout=2)"

ENTRYPOINT ["sh", "/app/stand-entrypoint.sh"]
