SHELL:=/bin/bash
DOCKER_VERSION:=v1.0
DOCKER_REGISTRY_STAGE:=justonecommand/app-status-exporter
all: build upload

build:
	docker build -t ${DOCKER_REGISTRY_STAGE}:${DOCKER_VERSION} .
upload:
	docker tag ${DOCKER_REGISTRY_STAGE}:${DOCKER_VERSION} ${DOCKER_REGISTRY_STAGE}:latest
	docker push ${DOCKER_REGISTRY_STAGE}:${DOCKER_VERSION}
	docker push ${DOCKER_REGISTRY_STAGE}:latest
