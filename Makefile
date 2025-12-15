.PHONY: install-all backend frontend kill-all dev

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
