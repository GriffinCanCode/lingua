.PHONY: install run kill clean build

install:
	npm install

kill:
	./scripts/kill_port.sh

run: kill
	npm run dev

build:
	bldr build

clean:
	rm -rf node_modules dist
