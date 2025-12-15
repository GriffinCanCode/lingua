.PHONY: install-all backend frontend kill-all dev build db db-up db-down db-logs migrate

build:
	bldr build

db-up:
	docker-compose up -d

db-down:
	docker-compose down

db-logs:
	docker-compose logs -f

db: db-up

migrate:
	cd backend && $(MAKE) migrate

install-all:
	cd backend && $(MAKE) install
	cd frontend && $(MAKE) install

backend:
	cd backend && $(MAKE) run

frontend:
	cd frontend && $(MAKE) run

kill-all:
	cd backend && $(MAKE) kill
	cd frontend && $(MAKE) kill

dev: kill-all
	@echo "Starting backend and frontend..."
	@$(MAKE) -j 2 backend frontend
