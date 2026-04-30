.PHONY: help setup setup-backend setup-frontend backend frontend dev build

BACKEND_DIR := qr_code_generator/scaffold
FRONTEND_DIR := $(BACKEND_DIR)/frontend
BACKEND_PYTHON := ./.venv/bin/python
BACKEND_PIP := ./.venv/bin/pip
BACKEND_UVICORN := ./.venv/bin/uvicorn

help:
	@echo "Available targets:"
	@echo "  make setup           Install backend and frontend dependencies"
	@echo "  make backend         Run the FastAPI backend"
	@echo "  make frontend        Run the Vite frontend"
	@echo "  make dev             Run backend and frontend together"
	@echo "  make build           Build the frontend"

setup: setup-backend setup-frontend

setup-backend:
	cd $(BACKEND_DIR) && python3 -m venv .venv && $(BACKEND_PIP) install -r requirements.txt

setup-frontend:
	cd $(FRONTEND_DIR) && npm install

backend:
	cd $(BACKEND_DIR) && $(BACKEND_UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd $(FRONTEND_DIR) && npm run dev

dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd $(BACKEND_DIR) && $(BACKEND_UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000) & \
	(cd $(FRONTEND_DIR) && npm run dev) & \
	wait

build:
	cd $(FRONTEND_DIR) && npm run build
