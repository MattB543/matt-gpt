# Matt-GPT API Usage Guide

## Authentication Requirements

### Bearer Token Authentication

All API requests (except `/health`) require a bearer token:

```bash
Authorization: Bearer matt-gpt-secure-bearer-token-2025
```

### OpenRouter API Key

Users must provide their own OpenRouter API key in each chat request to pay for LLM costs:

```json
{
  "message": "Your question here",
  "openrouter_api_key": "sk-or-v1-your-key-here",
  "model": "anthropic/claude-sonnet-4"
}
```

## API Endpoints

### POST /chat

Generate a response using Matt's AI avatar.

**Headers:**

```
Authorization: Bearer matt-gpt-secure-bearer-token-2025
Content-Type: application/json
```

**Request Body:**

```json
{
  "message": "What's your approach to software development?",
  "openrouter_api_key": "sk-or-v1-your-openrouter-key",
  "model": "anthropic/claude-sonnet-4",
  "context": {}
}
```

**Response:**

```json
{
  "response": "I'm a strong believer in iterative development...",
  "query_id": "uuid-here",
  "latency_ms": 3500.0,
  "context_items_used": 20
}
```

### GET /health

Check system health (no authentication required).

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-08-19T16:54:00.916931"
}
```

## Example Usage

### Python Example

```python
import requests

headers = {
    "Authorization": "Bearer matt-gpt-secure-bearer-token-2025",
    "Content-Type": "application/json"
}

data = {
    "message": "How do you prefer to communicate with your team?",
    "openrouter_api_key": "sk-or-v1-your-key-here"
}

response = requests.post(
    "http://your-server.com/chat",
    headers=headers,
    json=data
)

print(response.json())
```

### Curl Example

```bash
curl -X POST "http://your-server.com/chat" \
  -H "Authorization: Bearer matt-gpt-secure-bearer-token-2025" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What matters most when building products?",
    "openrouter_api_key": "sk-or-v1-your-key-here"
  }'
```

## Cost Management

- **Embeddings**: Paid by Matt-GPT (for context retrieval)
- **LLM Generation**: Paid by the user via their OpenRouter API key
- **Average Cost**: ~$0.01-0.05 per request depending on model and response length

## Available Models

All OpenRouter models are supported. Popular choices:

- `anthropic/claude-sonnet-4` (recommended)
- `openai/gpt-4o`
- `openai/gpt-4o-mini` (cost-effective)

## Error Codes

- `401 Unauthorized`: Invalid or missing bearer token
- `400 Bad Request`: Invalid OpenRouter API key format
- `500 Internal Server Error`: System error (check server logs)

## Performance Notes

- First request may take 10-15 seconds (system initialization)
- Subsequent requests: 3-8 seconds average
- Context retrieval: ~20 relevant items per query
- Response length: Typically 200-800 characters
