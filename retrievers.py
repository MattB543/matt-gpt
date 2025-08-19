import dspy
from typing import List, Dict, Any
import logging
import numpy as np
from pgvector.psycopg import register_vector
import psycopg
from datetime import datetime, timedelta
from database import get_session
from models import Message, PersonalityDoc
from sqlmodel import select
from sqlalchemy import text

# Configure logging
logger = logging.getLogger(__name__)


class PostgreSQLVectorRetriever(dspy.Retrieve):
    """Custom retriever using PostgreSQL with pgvector"""

    def __init__(self, connection_string: str, k: int = 20):
        super().__init__(k=k)
        self.conn_string = connection_string
        self.k = k
        logger.info(f"Initializing PostgreSQL Vector Retriever with k={k}")

    def forward(self, query: str, **kwargs) -> dspy.Prediction:
        """Retrieve relevant passages from PostgreSQL"""
        logger.info(f"Retrieving context for query: {query[:100]}...")
        
        # Generate query embedding using environment key (for retrieval only)
        logger.debug("Generating query embedding...")
        from llm_client import OpenRouterClient
        client = OpenRouterClient()  # Use environment key for embeddings
        query_embedding = client.generate_embedding(query)
        logger.debug(f"Query embedding generated: {len(query_embedding)} dimensions")

        results = []

        try:
            with psycopg.connect(self.conn_string) as conn:
                register_vector(conn)
                logger.debug("Connected to PostgreSQL with pgvector")

                # 1. Find relevant messages with context
                logger.debug("Retrieving relevant messages with context...")
                messages = self._retrieve_messages_with_context(
                    conn, query_embedding, limit=10, context_window=10
                )
                results.extend(messages)
                logger.info(f"Retrieved {len(messages)} message contexts")

                # 2. Find relevant personality docs
                logger.debug("Retrieving relevant personality documents...")
                docs = self._retrieve_personality_docs(
                    conn, query_embedding, limit=5
                )
                results.extend(docs)
                logger.info(f"Retrieved {len(docs)} personality documents")

        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            raise

        logger.info(f"Total context items retrieved: {len(results)}")
        return dspy.Prediction(passages=results)

    def _retrieve_messages_with_context(
        self, conn, embedding: list, limit: int = 10, context_window: int = 10
    ) -> List[str]:
        """Retrieve messages with surrounding context"""
        logger.debug(f"Searching for {limit} most relevant messages with {context_window}min context window")

        # Use HNSW index with cosine similarity (best practice for normalized vectors)
        query = """
        WITH relevant_messages AS (
            SELECT
                id, thread_id, message_text, timestamp,
                (embedding <=> %s::vector) as distance
            FROM messages
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        ),
        context_messages AS (
            SELECT DISTINCT m.message_text, m.timestamp, rm.distance
            FROM messages m
            INNER JOIN relevant_messages rm ON m.thread_id = rm.thread_id
            WHERE m.timestamp BETWEEN rm.timestamp - interval '%s minutes'
                  AND rm.timestamp + interval '%s minutes'
        )
        SELECT message_text, timestamp, distance
        FROM context_messages
        ORDER BY distance, timestamp;
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query, (embedding, embedding, limit,
                                  context_window, context_window))
                results = cur.fetchall()
                logger.debug(f"Found {len(results)} contextual messages")

        except Exception as e:
            logger.error(f"Message retrieval query failed: {e}")
            return []

        # Format as conversational context
        formatted = []
        for text, timestamp, distance in results:
            formatted.append(f"[{timestamp}] {text}")

        logger.debug(f"Formatted {len(formatted)} message contexts")
        return formatted

    def _retrieve_personality_docs(
        self, conn, embedding: list, limit: int = 5
    ) -> List[str]:
        """Retrieve relevant personality documents"""
        logger.debug(f"Searching for {limit} most relevant personality documents")

        query = """
        SELECT title, content, (embedding <=> %s::vector) as distance
        FROM personality_docs
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """

        try:
            with conn.cursor() as cur:
                cur.execute(query, (embedding, embedding, limit))
                results = cur.fetchall()
                logger.debug(f"Found {len(results)} personality documents")

        except Exception as e:
            logger.error(f"Personality doc retrieval query failed: {e}")
            return []

        formatted = []
        for title, content, distance in results:
            formatted.append(f"=== {title} ===\n{content}")

        logger.debug(f"Formatted {len(formatted)} personality documents")
        return formatted