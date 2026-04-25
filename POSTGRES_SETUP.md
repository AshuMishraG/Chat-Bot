# PostgreSQL Setup for ChatBot Application

## Quick Start

1. Copy the environment variables:
   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your actual values (especially OPENAI_API_KEY)

3. Start the services:
   ```bash
   docker-compose up -d
   ```

## What's been added:

### Docker Compose
- **postgres service**: PostgreSQL 15 Alpine container with health checks
- **Volume**: Persistent data storage for PostgreSQL
- **Init script**: Automatic database initialization with tables and indexes

### Environment Variables
- `DATABASE_URL`: Full PostgreSQL connection string
- `POSTGRES_DB`: Database name (default: chatbotdb)
- `POSTGRES_USER`: Database username (default: chatbotuser)
- `POSTGRES_PASSWORD`: Database password (default: chatbotpassword)
- `POSTGRES_HOST`: Database host (default: postgres)
- `POSTGRES_PORT`: Database port (default: 5432)

### Database Features
- **Automatic migration**: Creates tables if they don't exist
- **Performance indexes**: Optimized queries on user_id, session_id, and created_at
- **JSONB support**: Efficient JSON storage for message_history
- **Backward compatibility**: Falls back to SQLite if no DATABASE_URL is provided

## Database Tables

1. **chat_history**: Stores user conversations with JSONB message history
2. **chat_history_summary**: Stores conversation summaries

Both tables include proper indexing for optimal performance.
