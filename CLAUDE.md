# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Never read full files in the raw_data folder, they are huge files. Only read the first 200 lines if you need to check the structure/data

## Commands

**Development Setup:**
```bash
# Install dependencies
poetry install

# Initialize database (PostgreSQL with pgvector)
python init_db.py

# Start development server
uvicorn main:app --reload

# Start server on specific port
uvicorn main:app --host 127.0.0.1 --port 8000
```

**Database Management:**
```bash
# Recreate database from scratch
python recreate_db.py

# Add sample data for testing
python add_sample_data.py
```

**Testing:**
```bash
# Run comprehensive system validation
python validate_setup.py

# Final end-to-end test
python final_test.py

# Test specific components
python test_db.py
python test_llm_client.py
python test_matt_gpt.py
python test_retrieval.py
```

## Architecture

**Core System:**
- **FastAPI Application** (`main.py`): REST API with bearer token authentication, handles chat requests
- **MattGPT Module** (`matt_gpt.py`): DSPy-based conversational AI that mimics Matt's personality using RAG
- **Vector Retrieval** (`retrievers.py`): PostgreSQL with pgvector for semantic search across messages and personality docs
- **Database Models** (`models.py`): SQLModel definitions for Messages, PersonalityDocs, and QueryLogs

**Data Flow:**
1. Client sends authenticated chat request to `/chat` endpoint
2. MattGPT retrieves relevant context using vector similarity search
3. DSPy generates response using user's OpenRouter API key and retrieved context
4. Query and response logged asynchronously for analytics

**Key Components:**
- **Authentication**: Bearer token verification for API access
- **RAG System**: Combines Slack messages, personality documents for context
- **Dual API Key Support**: Users provide their own OpenRouter keys, system uses environment key for embeddings
- **Vector Search**: HNSW indexes with cosine similarity for optimal performance

**Database Schema:**
- `messages`: Slack messages with embeddings and metadata
- `personality_docs`: Curated personality information with embeddings  
- `query_logs`: All API interactions for analytics

## Environment Variables Required

```
DATABASE_URL=postgresql://user:pass@host:port/db
OPENROUTER_API_KEY=sk-or-v1-xxx  # System key for embeddings
OPENAI_API_KEY=sk-xxx            # For generating embeddings
MATT_GPT_BEARER_TOKEN=xxx        # API authentication
```

## Data Sources

**Raw Data Structure:**
- `raw_data/slack/`: Organized by channel name with daily JSON files
- `raw_data/texts/`: Text message exports in NDJSON format  
- `raw_data/twitter/`: Twitter data exports in JSONL format

**Important**: Raw data files are very large - use `limit=200` when reading for structure inspection only.

## Testing Strategy

The codebase includes comprehensive testing at multiple levels:
- Unit tests for individual components (test_*.py)
- Integration tests for database and API interactions
- End-to-end validation with running server
- Authentication and authorization testing