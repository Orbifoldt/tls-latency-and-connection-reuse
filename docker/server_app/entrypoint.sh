#!/bin/sh
set -eu

# Check we can read the certificate files (don't want to run your server and miss this)
test -r /run/tls/fullchain.cert.pem
test -r /run/tls/localhost.key.pem

nginx -g 'daemon off;' &
nginx_pid=$!

cleanup() {
    kill "$nginx_pid" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

exec uvicorn server_app.main:app --host 127.0.0.1 --port 9080
