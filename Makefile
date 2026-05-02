COMPOSE = docker compose
SMARTFIELD_URL = http://localhost:9988
SUBSCRIBER_URL = http://localhost:9987

# Auto-detect GPU: use Dockerfile.gpu if nvidia-smi is present, else Dockerfile.cpu
DOCKERFILE := $(shell nvidia-smi > /dev/null 2>&1 && echo Dockerfile.gpu || echo Dockerfile.cpu)
SMARTFIELD_IMAGE_TAG := $(shell nvidia-smi > /dev/null 2>&1 && echo smartfield:gpu || echo smartfield:cpu)

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  Smartfield — available commands"
	@echo ""
	@echo "  Start / Stop"
	@echo "    make up          Build images and start all services"
	@echo "    make up-detach   Start all services in background"
	@echo "    make down        Stop and remove containers"
	@echo "    make restart     Restart all services"
	@echo ""
	@echo "  Build"
	@echo "    make build       Rebuild all images without starting"
	@echo ""
	@echo "  Logs"
	@echo "    make logs        Tail logs for all services"
	@echo "    make logs-sf     Tail smartfield logs only"
	@echo "    make logs-mq     Tail mqtt_subscriber logs only"
	@echo ""
	@echo "  Detect / Field Distribution"
	@echo "    make detect      Show which Dockerfile and image tag will be used"
	@echo "    make export-gpu  Build GPU image and save to smartfield-gpu.tar.gz"
	@echo "    make export-cpu  Build CPU image and save to smartfield-cpu.tar.gz"
	@echo "    make load        Load the right tar.gz based on detected hardware"
	@echo ""
	@echo "  Status"
	@echo "    make status      Show running containers and health"
	@echo "    make health      Hit /health on both services"
	@echo ""
	@echo "  Mission"
	@echo "    make mission-live    Trigger a live mission (reads lat/long from config.toml)"
	@echo "    make mission-test    Trigger a test mission (YOLO runs, drone won't move)"
	@echo "    make mode-live       Switch config.toml to live mode"
	@echo "    make mode-test       Switch config.toml to test mode"
	@echo "    make mode-show       Show current mode_type in config.toml"
	@echo ""
	@echo "  Dashboard"
	@echo "    make ui          Launch the field operations dashboard (native)"
	@echo "    make logs-ui     Tail dashboard container logs"
	@echo ""
	@echo "  Cleanup"
	@echo "    make clean       Remove stopped containers and dangling images"
	@echo "    make clean-logs  Delete all mission log files"
	@echo ""

# ── Start / Stop ──────────────────────────────────────────────────────────────

up:
	@echo "Detected: $(DOCKERFILE) → tagging as $(SMARTFIELD_IMAGE_TAG)"
	SMARTFIELD_DOCKERFILE=$(DOCKERFILE) SMARTFIELD_IMAGE=$(SMARTFIELD_IMAGE_TAG) $(COMPOSE) up --build

up-detach:
	@echo "Detected: $(DOCKERFILE) → tagging as $(SMARTFIELD_IMAGE_TAG)"
	SMARTFIELD_DOCKERFILE=$(DOCKERFILE) SMARTFIELD_IMAGE=$(SMARTFIELD_IMAGE_TAG) $(COMPOSE) up --build -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

# ── Build ─────────────────────────────────────────────────────────────────────

build:
	@echo "Detected: $(DOCKERFILE) → tagging as $(SMARTFIELD_IMAGE_TAG)"
	SMARTFIELD_DOCKERFILE=$(DOCKERFILE) SMARTFIELD_IMAGE=$(SMARTFIELD_IMAGE_TAG) $(COMPOSE) build

detect:
	@echo "nvidia-smi: $$(nvidia-smi > /dev/null 2>&1 && echo found || echo not found)"
	@echo "Dockerfile : $(DOCKERFILE)"
	@echo "Image tag  : $(SMARTFIELD_IMAGE_TAG)"

# ── Logs ──────────────────────────────────────────────────────────────────────

logs:
	$(COMPOSE) logs -f

logs-sf:
	$(COMPOSE) logs -f smartfield

logs-mq:
	$(COMPOSE) logs -f mqtt_subscriber

logs-ui:
	$(COMPOSE) logs -f ui

# ── Dashboard ─────────────────────────────────────────────────────────────────

ui:
	@echo "Launching Smartfield Dashboard (native — requires conda)..."
	bash services/ui/run.sh

# ── Status ────────────────────────────────────────────────────────────────────

status:
	$(COMPOSE) ps

health:
	@echo "── smartfield ──"
	@curl -sf $(SMARTFIELD_URL)/health | python3 -m json.tool || echo "  UNREACHABLE"
	@echo "── mqtt_subscriber ──"
	@curl -sf $(SUBSCRIBER_URL)/health | python3 -m json.tool || echo "  UNREACHABLE"

# ── Mission ───────────────────────────────────────────────────────────────────

mission-live:
	@echo "Triggering LIVE mission..."
	@curl -sf -X POST $(SMARTFIELD_URL)/api/v1/mission/run \
		-H "Content-Type: application/json" \
		-d '{"mode_type": "live"}' | python3 -m json.tool

mission-test:
	@echo "Triggering TEST mission (drone will not move)..."
	@curl -sf -X POST $(SMARTFIELD_URL)/api/v1/mission/run \
		-H "Content-Type: application/json" \
		-d '{"mode_type": "test"}' | python3 -m json.tool

mode-live:
	@sed -i 's/mode_type = "test"/mode_type = "live"/' config.toml
	@echo "config.toml → mode_type = live"

mode-test:
	@sed -i 's/mode_type = "live"/mode_type = "test"/' config.toml
	@echo "config.toml → mode_type = test"

mode-show:
	@grep mode_type config.toml

# ── Field Distribution ────────────────────────────────────────────────────────
# Run once on a machine with internet to produce tarballs for USB transport.

export-gpu:
	@echo "Building and exporting smartfield:gpu → smartfield-gpu.tar.gz"
	SMARTFIELD_DOCKERFILE=Dockerfile.gpu SMARTFIELD_IMAGE=smartfield:gpu $(COMPOSE) build smartfield
	docker save smartfield:gpu | gzip > smartfield-gpu.tar.gz
	@echo "Done: smartfield-gpu.tar.gz ($$(du -sh smartfield-gpu.tar.gz | cut -f1))"

export-cpu:
	@echo "Building and exporting smartfield:cpu → smartfield-cpu.tar.gz"
	SMARTFIELD_DOCKERFILE=Dockerfile.cpu SMARTFIELD_IMAGE=smartfield:cpu $(COMPOSE) build smartfield
	docker save smartfield:cpu | gzip > smartfield-cpu.tar.gz
	@echo "Done: smartfield-cpu.tar.gz ($$(du -sh smartfield-cpu.tar.gz | cut -f1))"

load:
	@echo "Loading image for detected hardware: $(SMARTFIELD_IMAGE_TAG)"
	@if nvidia-smi > /dev/null 2>&1; then \
		docker load < smartfield-gpu.tar.gz; \
	else \
		docker load < smartfield-cpu.tar.gz; \
	fi

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	$(COMPOSE) down --remove-orphans
	docker image prune -f

clean-logs:
	@echo "Deleting mission logs under logs/mission/ ..."
	@rm -rf logs/mission/*
	@echo "Done."

.PHONY: help up up-detach down restart build detect \
        logs logs-sf logs-mq logs-ui \
        status health \
        mission-live mission-test mode-live mode-test mode-show \
        export-gpu export-cpu load \
        ui \
        clean clean-logs
