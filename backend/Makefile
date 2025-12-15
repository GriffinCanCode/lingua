.PHONY: install migrate run kill clean build

install:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

migrate:
	. venv/bin/activate && alembic upgrade head

kill:
	./scripts/kill_port.sh

run: kill
	. venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

build:
	bldr build

clean:
	rm -rf venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
