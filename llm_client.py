from openai import OpenAI
import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


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
        """Generate embeddings using OpenAI directly"""
        logger.debug(f"Generating embedding for text: {text[:50]}...")
        
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
            logger.debug(f"Embedding generated successfully, dimensions: {len(response.data[0].embedding)}")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise