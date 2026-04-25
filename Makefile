.PHONY: run-docker run-docker-postgres down-docker run-d run-dp down-dp down-d down

run-docker:
	docker-compose up --build

run-docker-postgres:
	docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up --build

down-docker:
	docker-compose down

run: run-docker

run-d: run-docker

run-dp: run-docker-postgres

down-dp: down-docker

down-d: down-docker

down: down-docker
