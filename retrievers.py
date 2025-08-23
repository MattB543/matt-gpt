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


def get_current_trace():
    """Get current trace context from FastAPI app state"""
    # Removed circular import - this function is no longer needed
    # since we removed all tracing functionality
    return None


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
        
        # Generate query embedding using environment key
        logger.debug("Generating query embedding...")
        from llm_client import OpenRouterClient
        client = OpenRouterClient()
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
                    conn, query_embedding, limit=15, context_window=10
                )
                results.extend(messages)
                logger.info(f"Retrieved {len(messages)} message contexts")

                # === RAG MESSAGE RETRIEVAL LOGGING ===
                logger.info("=" * 60)
                logger.info("RAG MESSAGE RETRIEVAL DETAILS:")
                logger.info("=" * 60)
                for i, msg in enumerate(messages[:5]):  # Log first 5 messages
                    logger.info(f"MESSAGE {i+1}:")
                    logger.info(f"  Content: {msg[:150]}...")
                    if len(msg) > 150:
                        logger.info(f"  (truncated from {len(msg)} chars)")
                    logger.info("-" * 30)
                if len(messages) > 5:
                    logger.info(f"... and {len(messages) - 5} more messages")
                logger.info("=" * 60)

                # 2. Find relevant personality docs
                logger.debug("Retrieving relevant personality documents...")
                docs = self._retrieve_personality_docs(
                    conn, query_embedding, limit=3
                )
                results.extend(docs)
                logger.info(f"Retrieved {len(docs)} personality documents")

                # === RAG PERSONALITY DOCS LOGGING ===
                logger.info("=" * 60)
                logger.info("RAG PERSONALITY DOCS DETAILS:")
                logger.info("=" * 60)
                for i, doc in enumerate(docs):
                    logger.info(f"PERSONALITY DOC {i+1}:")
                    logger.info(f"  Content: {doc[:150]}...")
                    if len(doc) > 150:
                        logger.info(f"  (truncated from {len(doc)} chars)")
                    logger.info("-" * 30)
                logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            raise

        # Log to trace if available
        trace = get_current_trace()
        if trace:
            trace.log_context_retrieval(messages, docs)

        logger.info(f"Total context items retrieved: {len(results)}")
        return dspy.Prediction(passages=results)

    def _retrieve_messages_with_context(
        self, conn, embedding: list, limit: int = 15, context_window: int = 10
    ) -> List[str]:
        """Retrieve the top N most relevant individual messages, then get full thread context for each"""
        logger.debug(f"Searching for {limit} most relevant individual messages, then retrieving full thread context")

        # First, find the most relevant individual messages (only those with >20 chars)
        relevant_query = """
        SELECT id, thread_id, message_text, timestamp, (embedding <=> %s::vector) as distance
        FROM messages
        WHERE embedding IS NOT NULL 
        AND LENGTH(message_text) > 20
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """

        try:
            with conn.cursor() as cur:
                # Get the top N most relevant individual messages
                cur.execute(relevant_query, (embedding, embedding, limit))
                relevant_messages = cur.fetchall()
                logger.debug(f"Found {len(relevant_messages)} most relevant individual messages")

                if not relevant_messages:
                    return []

                # Get unique thread_id and date combinations from these specific messages
                thread_dates = set()
                for _, thread_id, _, timestamp, _ in relevant_messages:
                    if thread_id:
                        date_str = timestamp.date()
                        thread_dates.add((thread_id, date_str))

                logger.debug(f"Will retrieve full context from {len(thread_dates)} thread/date combinations")

                # Now get ALL messages from those thread/date combinations for full context
                all_context_messages = []
                for thread_id, date in thread_dates:
                    context_query = """
                    SELECT message_text, timestamp, thread_id, meta_data
                    FROM messages
                    WHERE thread_id = %s 
                    AND DATE(timestamp) = %s
                    ORDER BY timestamp
                    """
                    cur.execute(context_query, (thread_id, date))
                    thread_messages = cur.fetchall()
                    all_context_messages.extend(thread_messages)

                logger.debug(f"Found {len(all_context_messages)} total contextual messages from {len(thread_dates)} thread/date groups")

        except Exception as e:
            logger.error(f"Message retrieval query failed: {e}")
            raise

        # Log search results to trace if available
        trace = get_current_trace()
        if trace:
            search_results = []
            for _, _, text, timestamp, distance in relevant_messages:
                search_results.append({
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "timestamp": str(timestamp),
                    "similarity_distance": float(distance),
                    "similarity_score": 1.0 - float(distance)
                })
            trace.log_vector_search(embedding, search_results)

        # Group and format messages by thread and date
        from collections import defaultdict
        grouped_messages = defaultdict(list)
        thread_display_names = {}
        
        for text, timestamp, thread_id, meta_data in all_context_messages:
            date_str = timestamp.date().strftime("%Y-%m-%d")
            
            # Get display name from meta_data if available for thread header
            thread_display_name = thread_id
            if meta_data and isinstance(meta_data, dict) and 'display_name' in meta_data:
                thread_display_name = meta_data['display_name']
                thread_display_names[thread_id] = thread_display_name
            elif thread_id in thread_display_names:
                thread_display_name = thread_display_names[thread_id]
            
            # Get sender name for message prefix
            sender_name = "Unknown"
            if meta_data and isinstance(meta_data, dict):
                if 'display_name' in meta_data:
                    sender_name = meta_data['display_name']
                elif 'phone_number' in meta_data:
                    sender_name = meta_data['phone_number']
            
            key = f"{thread_display_name} - {date_str}"
            grouped_messages[key].append((timestamp, text, sender_name))

        # Format chronologically with thread/date headers
        formatted = []
        for thread_date, messages in sorted(grouped_messages.items()):
            formatted.append(f"\n=== {thread_date} ===")
            for timestamp, text, sender_name in sorted(messages):
                formatted.append(f"{sender_name}: {text}")
            formatted.append("")  # Add blank line between groups

        logger.debug(f"Formatted {len(formatted)} message contexts in {len(grouped_messages)} thread/date groups")
        return formatted

    def _retrieve_personality_docs(
        self, conn, embedding: list, limit: int = 3
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
            raise

        formatted = []
        for title, content, distance in results:
            formatted.append(f"=== {title} ===\n{content}")

        logger.debug(f"Formatted {len(formatted)} personality documents")
        return formatted