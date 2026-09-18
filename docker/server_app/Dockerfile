FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y nginx \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY server_app ./server_app

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

COPY docker/server_app/nginx.conf /etc/nginx/nginx.conf
COPY docker/server_app/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

EXPOSE 8080 8442 8443

ENTRYPOINT ["/entrypoint.sh"]
