-- Initialize the ChatBot application database
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create the main database tables
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    message_history JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_history_summary (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS home_cards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_home_cards_status ON home_cards(status);
CREATE INDEX IF NOT EXISTS idx_home_cards_id ON home_cards(id);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_created_at ON chat_history(created_at);

CREATE INDEX IF NOT EXISTS idx_chat_history_summary_user_id ON chat_history_summary(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_summary_session_id ON chat_history_summary(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_summary_created_at ON chat_history_summary(created_at);

-- Insert a welcome message (optional)
INSERT INTO chat_history (user_id, session_id, message_history)
VALUES ('system', 'init', '[]'::jsonb)
ON CONFLICT DO NOTHING;

-- Enable pgvector extension for vector search
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for device documentation chunks and embeddings
CREATE TABLE IF NOT EXISTS device_docs (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    source text,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1536) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for conversation messages and analytics
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100) NOT NULL,
    bot_message TEXT NOT NULL, 
    user_message TEXT NOT NULL,                    
    message_turn_status VARCHAR(20) DEFAULT 'success',  -- 'success' or 'failed'
    action_cards JSONB,                -- nullable
    ai_generated_recipe JSONB,         -- nullable 
    chatbot_recipe JSONB,               -- nullable 
    chatbot_mixlist JSONB,              -- nullable 
    response_time INTEGER,
    device_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for conversation_messages table
CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_id ON conversation_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_id ON conversation_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_status ON conversation_messages(message_turn_status);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at ON conversation_messages(created_at);

-- Table for scraped ChatBot website content
CREATE TABLE IF NOT EXISTS chatbot_scraped_content (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL UNIQUE,
    page_title TEXT,
    content TEXT,
    content_embedding vector(1536),  -- Content embedding
    url_embedding vector(1536),  -- URL embedding
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for chatbot_scraped_content table
CREATE INDEX IF NOT EXISTS idx_chatbot_scraped_content_url ON chatbot_scraped_content(url);
CREATE INDEX IF NOT EXISTS idx_chatbot_scraped_content_page_title ON chatbot_scraped_content(page_title);
CREATE INDEX IF NOT EXISTS idx_chatbot_scraped_content_created_at ON chatbot_scraped_content(created_at);

-- HNSW index for efficient vector similarity search on content embeddings
CREATE INDEX IF NOT EXISTS idx_chatbot_scraped_content_content_embedding 
ON chatbot_scraped_content USING hnsw (content_embedding vector_cosine_ops);

-- HNSW index for efficient vector similarity search on URL embeddings
CREATE INDEX IF NOT EXISTS idx_chatbot_scraped_content_url_embedding 
ON chatbot_scraped_content USING hnsw (url_embedding vector_cosine_ops);

-- Table for user feedback on AI responses
-- Collects feedback from multiple branches for analytics and model improvement
CREATE TABLE IF NOT EXISTS chatbot_feedback_01 (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL UNIQUE,
    comment TEXT,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    rating TEXT NOT NULL,
    reason TEXT,
    conversation_turn TEXT,
    branch TEXT,
    locale TEXT,
    app_version TEXT,
    platform TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for chatbot_feedback_01 table for efficient querying
CREATE INDEX IF NOT EXISTS idx_chatbot_feedback_session_id ON chatbot_feedback_01(session_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_feedback_user_id ON chatbot_feedback_01(user_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_feedback_rating ON chatbot_feedback_01(rating);
CREATE INDEX IF NOT EXISTS idx_chatbot_feedback_branch ON chatbot_feedback_01(branch);
CREATE INDEX IF NOT EXISTS idx_chatbot_feedback_created_at ON chatbot_feedback_01(created_at);
