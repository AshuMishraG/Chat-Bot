# Conversational Chatbot Backend

This repository contains an agent-first, multi-turn conversational chatbot backend built with FastAPI and [pydantic-ai](https://github.com/pydantic/pydantic-ai). It is designed for web and mobile experiences and supports structured responses, conversational memory, and optional image-aware workflows.

---

## Features

- OpenAI-powered multi-turn conversation system
- Typed request and response schema via Pydantic
- Session context tracking with user and assistant turns
- JSON-first API surface for client apps
- Structured agent orchestration with `pydantic-ai`
- Debug endpoint to inspect session state

---

## Run Locally

### 1) Clone the repository

```bash
git clone https://github.com/<your-org-or-user>/Chat-Bot.git
cd Chat-Bot
```

### 2) Create a `.env` file

```env
OPENAI_API_KEY=sk-xxx
ENVIRONMENT=development
DEBUG=true
```

### 3) Start with Docker Compose

```bash
docker compose up --build
```

This starts the backend (default: `http://localhost:8000`) with logs in your terminal.

---

## Makefile Shortcuts

Run app containers without Postgres:

```shell
make run
```

Run app containers with Postgres:

```shell
make run-dp
```

Shut down containers:

```shell
make down
```

---

## API Endpoints

### `POST /chat`

**Request:**
```json
{
  "session_id": "abc123",
  "message": "Help me draft a friendly onboarding message"
}
```

**Response:**
```json
{
  "response": "Sure — welcome aboard! I can help you get started in a few steps."
}
```

---

### `GET /status`

Returns service health:

```json
{
  "status": "ok",
  "message": "Service is healthy"
}
```

---

### `GET /session/{session_id}/debug`

Returns full message history for the session:

```json
{
  "session_id": "abc123",
  "turns": [
    { "role": "user", "text": "I want a strong cocktail" },
    { "role": "assistant", "text": "Try a Negroni." }
  ]
}
```

---

## Project Structure

```
app/
├── api/            # FastAPI route handlers
├── agents/         # LLM agent definitions
├── core/           # Core utilities like memory, config
├── models/         # Pydantic request/response models
├── main.py         # FastAPI entry point
```

---

## Tech Stack

- [FastAPI](https://fastapi.tiangolo.com/) — high-performance web framework
- [pydantic-ai](https://github.com/pydantic/pydantic-ai) — strongly typed agent orchestration
- [OpenAI models](https://platform.openai.com/docs/models) — conversation model(s)
- Docker + Compose — dev & deployment

---

## Notes

- Update CORS and deployment settings for your target environments.
- Configure `.env` values before production deployment.
