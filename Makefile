# ─────────────────────────────────────────────────────────────────────────────
#  projectkusi / backend — Makefile
#
#  Works on Linux, macOS and Windows.
#  On Windows it is best run from Git Bash or WSL; native cmd.exe is supported
#  for the common targets too (env / clean use cmd-specific commands there).
# ─────────────────────────────────────────────────────────────────────────────

# ---- Tooling --------------------------------------------------------------- #
UV             ?= uv
DOCKER_COMPOSE ?= docker compose

# ---- Paths ----------------------------------------------------------------- #
ROOT           := $(CURDIR)
SRC            := $(ROOT)/src
ALEMBIC_INI    := src/infrastructure/database/alembic.ini

ENV_FILE       ?= .env
ENV_EXAMPLE    ?= .env.example

# ---- OS detection ---------------------------------------------------------- #
# PYTHONPATH uses ';' on Windows and ':' everywhere else.
ifeq ($(OS),Windows_NT)
    PATHSEP := ;
    DETECTED_OS := Windows
else
    PATHSEP := :
    DETECTED_OS := $(shell uname -s)
endif

# The codebase imports from two roots:
#   - backend/      (so `python -m src` can find the `src` package)
#   - backend/src/  (e.g. `from application ...`, `from domain ...`, `from config ...`)
export PYTHONPATH := $(ROOT)$(PATHSEP)$(SRC)

# Inject the .env into every `uv run` subprocess only when the file exists
# (the app reads os.environ directly, there is no dotenv autoload).
ENV_ARG := $(if $(wildcard $(ENV_FILE)),--env-file $(ENV_FILE),)

RUN     := $(UV) run $(ENV_ARG)
ALEMBIC := $(RUN) alembic -c $(ALEMBIC_INI)

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
#  Help
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@echo "projectkusi backend  (OS: $(DETECTED_OS))"
	@echo ""
	@echo "Setup:"
	@echo "  make install         Install all deps (prod + dev + test)"
	@echo "  make install-prod    Install production deps only"
	@echo "  make install-test    Install prod + test deps"
	@echo "  make lock            Refresh the uv.lock file"
	@echo "  make env             Create $(ENV_FILE) from $(ENV_EXAMPLE)"
	@echo ""
	@echo "Run / quality:"
	@echo "  make run             Start the API (python -m src)"
	@echo "  make lint            Ruff lint check"
	@echo "  make lint-fix        Ruff lint check with --fix"
	@echo "  make format          Ruff format"
	@echo "  make format-check    Ruff format --check"
	@echo "  make typecheck       mypy static type check"
	@echo "  make check           lint + format-check + typecheck"
	@echo "  make test            Run the test suite"
	@echo ""
	@echo "Migrations (alembic):"
	@echo "  make migration m=\"msg\"   Autogenerate a new revision"
	@echo "  make upgrade            Upgrade DB to head"
	@echo "  make downgrade          Downgrade DB by one revision"
	@echo "  make migrate-history    Show revision history"
	@echo "  make migrate-current    Show current revision"
	@echo "  make db-reset           Downgrade to base, then upgrade to head"
	@echo ""
	@echo "Docker:"
	@echo "  make up / down          Start / stop the stack (detached)"
	@echo "  make build              Build images"
	@echo "  make logs               Follow logs"
	@echo "  make ps                 Show running services"
	@echo "  make restart            down + up"
	@echo ""
	@echo "Housekeeping:"
	@echo "  make clean              Remove caches (__pycache__, .ruff_cache)"

# ─────────────────────────────────────────────────────────────────────────────
#  Setup
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: install
install: ## Install all deps (prod + dev + test)
	$(UV) sync

.PHONY: install-prod
install-prod: ## Install production deps only (no dev/test groups)
	$(UV) sync --no-default-groups

.PHONY: install-test
install-test: ## Install prod + test deps (no dev tooling)
	$(UV) sync --no-default-groups --group test

.PHONY: lock
lock: ## Refresh uv.lock
	$(UV) lock

.PHONY: env
env: ## Create .env from the example if it does not exist
ifeq ($(OS),Windows_NT)
	@if not exist $(ENV_FILE) ( copy $(ENV_EXAMPLE) $(ENV_FILE) && echo Created $(ENV_FILE) ) else ( echo $(ENV_FILE) already exists )
else
	@if [ -f $(ENV_FILE) ]; then \
		echo "$(ENV_FILE) already exists"; \
	else \
		cp $(ENV_EXAMPLE) $(ENV_FILE) && echo "Created $(ENV_FILE)"; \
	fi
endif

# ─────────────────────────────────────────────────────────────────────────────
#  Run / quality
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: run
run: ## Start the API
	$(RUN) python -m src

.PHONY: lint
lint: ## Ruff lint check
	$(RUN) ruff check .

.PHONY: lint-fix
lint-fix: ## Ruff lint check with autofix
	$(RUN) ruff check --fix .

.PHONY: format
format: ## Ruff format
	$(RUN) ruff format .

.PHONY: format-check
format-check: ## Ruff format check only
	$(RUN) ruff format --check .

.PHONY: typecheck
typecheck: ## Static type check (mypy)
	$(RUN) mypy src

.PHONY: check
check: lint format-check typecheck ## Lint + format check + type check

.PHONY: test
test: ## Run the test suite
	$(RUN) pytest

# ---- CI entrypoints -------------------------------------------------------- #
.PHONY: develop
develop: ## CI: install all deps (prod + dev + test)
	$(UV) sync

.PHONY: lint-ci
lint-ci: check ## CI: lint + format check + type check

.PHONY: test-ci
test-ci: ## CI: run tests with coverage + junit reports (exit 5 = no tests yet, treated as success)
	$(RUN) pytest \
		--cov=src --cov-report=term --cov-report=xml \
		--junitxml=junit.xml; \
	rc=$$?; [ $$rc -eq 5 ] && exit 0 || exit $$rc

# ─────────────────────────────────────────────────────────────────────────────
#  Migrations
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: migration
migration: ## Autogenerate a revision:  make migration m="add users"
ifeq ($(strip $(m)),)
	$(error Provide a message, e.g.  make migration m="add users table")
endif
	$(ALEMBIC) revision --autogenerate -m "$(m)"

.PHONY: upgrade
upgrade: ## Upgrade DB to head (REV=<id> to target a specific revision)
	$(ALEMBIC) upgrade $(if $(REV),$(REV),head)

.PHONY: downgrade
downgrade: ## Downgrade DB by one revision (REV=<id> to override)
	$(ALEMBIC) downgrade $(if $(REV),$(REV),-1)

.PHONY: migrate-history
migrate-history: ## Show migration history
	$(ALEMBIC) history --verbose

.PHONY: migrate-current
migrate-current: ## Show the current revision
	$(ALEMBIC) current --verbose

.PHONY: db-reset
db-reset: ## Downgrade to base then upgrade to head
	$(ALEMBIC) downgrade base
	$(ALEMBIC) upgrade head

# ─────────────────────────────────────────────────────────────────────────────
#  Docker
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: up
up: ## Start the stack (detached)
	$(DOCKER_COMPOSE) up -d

.PHONY: down
down: ## Stop the stack
	$(DOCKER_COMPOSE) down

.PHONY: build
build: ## Build images
	$(DOCKER_COMPOSE) build

.PHONY: logs
logs: ## Follow logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: ps
ps: ## Show running services
	$(DOCKER_COMPOSE) ps

.PHONY: restart
restart: down up ## Restart the stack

# ─────────────────────────────────────────────────────────────────────────────
#  Housekeeping
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Remove Python / tooling caches
ifeq ($(OS),Windows_NT)
	@for /d /r . %%d in (__pycache__ .ruff_cache .pytest_cache) do @if exist "%%d" rd /s /q "%%d"
else
	@find . -type d \( -name __pycache__ -o -name .ruff_cache -o -name .pytest_cache \) -prune -exec rm -rf {} + 2>/dev/null || true
endif
	@echo "Cleaned caches"
