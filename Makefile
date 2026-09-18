IMAGE ?= tls-server
TAG ?= latest

.PHONY: server-build-docker server-run ca-server-run client-run

server-build-docker:
	docker build \
		-f docker/server_app/Dockerfile \
		-t $(IMAGE):$(TAG) \
		.

server-run: server-build-docker
	docker run --rm \
		-p 8080:8080 \
		-p 8442:8442 \
		-p 8443:8443 \
		-v "$(CURDIR)/certs/leaf:/run/tls:ro" \
		-v "$(CURDIR)/certs/leaf_revoked_crl:/run/tls-revoked:ro" \
		$(IMAGE):$(TAG)

ca-server-run:
	uv run --with watchfiles uvicorn ca_server.main:app \
		--host 127.0.0.1 \
		--port 6080 \
		--reload \
		--reload-dir ca_server \
		--reload-dir certs/ca_server \
		--reload-include '*.py' \
		--reload-include '*.pem'

client-run:
	uv run --with watchfiles uvicorn client_app.main:app \
		--host 127.0.0.1 \
		--port 7000 \
		--reload \
		--reload-dir client_app \
		--reload-dir certs \
		--reload-include '*.py' \
		--reload-include '*.pem'
