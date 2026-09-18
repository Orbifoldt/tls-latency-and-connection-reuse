IMAGE ?= tls-server
TAG ?= latest

.PHONY: server-build-docker server-run

server-build-docker:
	docker build \
		-f docker/server_app/Dockerfile \
		-t $(IMAGE):$(TAG) \
		.

server-run: server-build-docker
	docker run --rm \
		-p 8080:8080 \
		-p 8443:8443 \
		-v "$(CURDIR)/certs/leaf:/run/tls:ro" \
		$(IMAGE):$(TAG)
