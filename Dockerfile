FROM python:3.11-slim

# Install uv and curl
RUN pip install uv && apt-get update && apt-get install -y git curl libavif-dev --no-install-recommends && rm -rf /var/lib/apt/lists/

# Create app directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies via uv
RUN uv pip install --editable . --system
RUN pip install autopep8

# Start app with live-reload
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-config", "log_config.yaml"]
