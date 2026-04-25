FROM postgres:17.5-bookworm

# Install uv and curl
RUN apt-get update && apt install -y postgresql-17-pgvector
