from openai import OpenAI
import os
import logging
import hashlib
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Simple in-memory cache for embeddings to avoid API calls
_embedding_cache = {}


class OpenRouterClient:
    """Wrapper for OpenRouter API using OpenAI SDK"""

    def __init__(self, api_key: Optional[str] = None):
        logger.info("Initializing OpenRouter client...")
        
        # Use provided key or fall back to environment
        openrouter_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            logger.error("No OpenRouter API key provided")
            raise ValueError("OpenRouter API key required")
        
        if api_key:
            logger.info("Using user-provided OpenRouter API key")
        else:
            logger.info("Using environment OpenRouter API key")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            default_headers={
                "HTTP-Referer": "https://matt-gpt.app",
                "X-Title": "Matt-GPT",
            }
        )
        logger.info("OpenRouter client initialized successfully")

    def chat_completion(
        self,
        messages: list,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        """Get chat completion from OpenRouter"""
        logger.info(f"Requesting chat completion with model: {model}")
        logger.debug(f"Message count: {len(messages)}, max_tokens: {max_tokens}")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            logger.info(f"Chat completion successful, tokens used: {response.usage.total_tokens if response.usage else 'unknown'}")
            return response
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            raise

    def generate_embedding(self, text: str) -> list[float]:
        """Generate embeddings using OpenAI directly with caching"""
        # Create cache key from text hash
        cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # Check cache first
        if cache_key in _embedding_cache:
            logger.debug(f"Using cached embedding for text: {text[:50]}...")
            return _embedding_cache[cache_key]
        
        logger.debug(f"Generating new embedding for text: {text[:50]}...")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("OPENAI_API_KEY not found in environment")
            raise ValueError("OPENAI_API_KEY required for embeddings")
        
        try:
            # Use OpenAI client for embeddings (more reliable)
            openai_client = OpenAI(api_key=openai_key)
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            _embedding_cache[cache_key] = embedding
            logger.debug(f"Embedding generated and cached, dimensions: {len(embedding)}")
            
            # Basic cache size management - keep only recent 100 entries
            if len(_embedding_cache) > 100:
                # Remove oldest half of cache entries
                keys_to_remove = list(_embedding_cache.keys())[:50]
                for key in keys_to_remove:
                    del _embedding_cache[key]
                logger.debug("Cleaned embedding cache")
            
            return embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise