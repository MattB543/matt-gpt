#!/usr/bin/env python3
"""
Enhanced RAG Retrieval System with Query Expansion and Context Filtering
Based on 2025 RAG best practices and research
"""

import time
import logging
import asyncio
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import hashlib

from llm_client import OpenRouterClient
from retrievers import PostgreSQLVectorRetriever
from models import RagAnalytics
from database import get_session

logger = logging.getLogger(__name__)

# Simple in-memory cache for query expansions
_expansion_cache = {}

@dataclass
class EnhancedRagMetrics:
    """Track detailed metrics for enhanced RAG pipeline"""
    original_query: str
    expanded_queries: List[str]
    
    # Timing metrics
    query_expansion_ms: float
    retrieval_ms: float
    filtering_ms: float
    total_rag_ms: float
    
    # Retrieval metrics
    total_messages_retrieved: int
    unique_messages_after_dedup: int
    threads_reconstructed: int
    
    # Filtering metrics
    messages_before_filtering: int
    messages_after_filtering: int
    filtering_ratio: float
    
    # Context data
    raw_retrieved_context: List[str]
    filtered_context: List[str]
    
    # Quality metrics
    context_relevance_score: Optional[float] = None
    fallback_used: bool = False


class EnhancedRAGRetriever:
    """
    Enhanced RAG system with query expansion and context filtering
    Implements 2025 best practices for improved retrieval accuracy
    """
    
    def __init__(self, connection_string: str, k: int = 20):
        self.base_retriever = PostgreSQLVectorRetriever(connection_string, k=k)
        self.conn_string = connection_string
        self.k = k
        self.system_client = None  # Will be initialized with system API key
        logger.info(f"Enhanced RAG Retriever initialized with k={k}")
    
    def _get_system_client(self) -> OpenRouterClient:
        """Get system OpenRouter client for internal operations"""
        if self.system_client is None:
            import os
            system_key = os.getenv("OPENROUTER_API_KEY")
            if not system_key:
                raise ValueError("System OPENROUTER_API_KEY required for enhanced RAG")
            logger.debug("Initializing system OpenRouter client for enhanced RAG operations")
            self.system_client = OpenRouterClient(api_key=system_key)
            logger.debug("System OpenRouter client initialized successfully")
        return self.system_client
    
    def expand_query(self, original_query: str) -> Tuple[List[str], float]:
        """
        Expand user query into semantic variations for improved retrieval coverage.
        Uses 2025 best practices: temperature 0.3, semantic focus, synonym expansion.
        
        Returns:
            Tuple of (expanded_queries, processing_time_ms)
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = hashlib.md5(original_query.encode('utf-8')).hexdigest()
        if cache_key in _expansion_cache:
            logger.debug(f"Using cached query expansion for: {original_query[:50]}...")
            expansion_time = (time.time() - start_time) * 1000
            return _expansion_cache[cache_key], expansion_time
        
        logger.info(f"Expanding query: {original_query}")
        
        # Optimized prompt based on 2025 RAG research
        expansion_prompt = f"""You are a message simulation specialist. Your task is to generate plausible unique text messages that would answer the original question.

Generate 5 example one sentence text messages that answer the original question in different and unique ways. Focus on generating answers that use:
- Synonyms and alternative terminology 
- Specific sub-questions
- Related concepts that would contain useful context
- Different perspectives on the same topic
- Domain-specific terms if applicable

IMPORTANT: Return ONLY the 5 example responses, one per line, with no numbering, bullets, or extra text.

Original query: {original_query}

Example messages:"""

        try:
            client = self._get_system_client()
            messages = [{"role": "user", "content": expansion_prompt}]
            
            # Use temperature 0.3 for focused expansion (2025 best practice)
            response = client.chat_completion(
                messages=messages,
                model="anthropic/claude-sonnet-4",
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response into individual queries
            expanded_queries = []
            for line in response_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('-') and not line.startswith('•'):
                    # Remove any numbering
                    clean_line = line.lstrip('0123456789. ').strip()
                    if clean_line:
                        expanded_queries.append(clean_line)
            
            # Ensure we have exactly 5 queries, pad with original if needed
            while len(expanded_queries) < 5:
                expanded_queries.append(original_query)
            expanded_queries = expanded_queries[:5]  # Cap at 5
            
            # Cache the result
            _expansion_cache[cache_key] = expanded_queries
            
            # Basic cache size management
            if len(_expansion_cache) > 50:
                keys_to_remove = list(_expansion_cache.keys())[:25]
                for key in keys_to_remove:
                    del _expansion_cache[key]
                logger.debug("Cleaned query expansion cache")
            
            expansion_time = (time.time() - start_time) * 1000
            logger.info(f"Query expansion completed in {expansion_time:.2f}ms")
            logger.debug(f"Expanded queries: {expanded_queries}")
            
            return expanded_queries, expansion_time
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            # Fallback to original query repeated
            expansion_time = (time.time() - start_time) * 1000
            return [original_query] * 5, expansion_time
    
    def multi_query_retrieval(
        self, 
        expanded_queries: List[str], 
        messages_per_query: int = 10
    ) -> Tuple[List[str], float, Dict]:
        """
        Retrieve context using multiple query variations with deduplication.
        
        Returns:
            Tuple of (context_passages, processing_time_ms, retrieval_stats)
        """
        start_time = time.time()
        
        logger.info(f"Multi-query retrieval with {len(expanded_queries)} queries")
        
        all_message_ids = set()
        retrieval_stats = {
            'total_queries': len(expanded_queries),
            'messages_per_query': messages_per_query,
            'total_raw_retrievals': 0,
            'unique_messages': 0,
            'threads_found': 0
        }
        
        try:
            # Use parallel processing for multiple queries where possible
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_query = {}
                
                for i, query in enumerate(expanded_queries):
                    logger.debug(f"Submitting retrieval for query {i+1}: {query[:50]}...")
                    # Submit each query for parallel processing
                    future = executor.submit(self._retrieve_single_query, query, messages_per_query)
                    future_to_query[future] = query
                
                # Collect results as they complete
                for future in future_to_query:
                    try:
                        query = future_to_query[future]
                        message_ids = future.result()
                        retrieval_stats['total_raw_retrievals'] += len(message_ids)
                        all_message_ids.update(message_ids)
                        logger.debug(f"Query '{query[:30]}...' returned {len(message_ids)} messages")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve for query '{future_to_query[future]}': {e}")
            
            # Update stats after deduplication
            retrieval_stats['unique_messages'] = len(all_message_ids)
            
            # DEBUG: Log the exact message IDs that were found
            message_id_list = list(all_message_ids)
            logger.info(f"DEBUG: Found {len(message_id_list)} unique message IDs:")
            for i, msg_id in enumerate(sorted(message_id_list)[:20], 1):  # Show first 20 IDs
                logger.info(f"  {i}. {msg_id}")
            if len(message_id_list) > 20:
                logger.info(f"  ... and {len(message_id_list) - 20} more message IDs")
            
            # Now rebuild thread contexts for all unique messages
            logger.debug(f"Rebuilding thread contexts for {len(all_message_ids)} unique messages")
            context_passages = self._rebuild_thread_contexts(list(all_message_ids))
            
            # Count unique threads
            thread_ids = set()
            for passage in context_passages:
                # Extract thread ID from passage headers
                if "Thread " in passage or "Matt-GPT Conversation" in passage:
                    lines = passage.split('\n')
                    header_line = [line for line in lines if "Thread " in line or "Matt-GPT Conversation" in line]
                    if header_line:
                        thread_ids.add(header_line[0].strip())
            
            retrieval_stats['threads_found'] = len(thread_ids)
            
            retrieval_time = (time.time() - start_time) * 1000
            logger.info(f"Multi-query retrieval completed in {retrieval_time:.2f}ms")
            logger.info(f"Retrieved {len(context_passages)} context passages from {len(thread_ids)} threads")
            
            return context_passages, retrieval_time, retrieval_stats
            
        except Exception as e:
            logger.error(f"Multi-query retrieval failed: {e}")
            retrieval_time = (time.time() - start_time) * 1000
            return [], retrieval_time, retrieval_stats
    
    def _retrieve_single_query(self, query: str, limit: int) -> List[str]:
        """Retrieve message IDs for a single query"""
        try:
            # Generate embedding for the query
            client = self._get_system_client()
            embedding = client.generate_embedding(query)
            logger.debug(f"Generated embedding for query: '{query[:50]}...'")
            
            # Use the base retriever's database connection logic
            import psycopg
            from pgvector.psycopg import register_vector
            
            with psycopg.connect(self.conn_string) as conn:
                register_vector(conn)
                
                # Get the most relevant message IDs (not full context yet)
                # FILTER: Only include matt-gpt conversation sources for debugging
                relevant_query = """
                SELECT id
                FROM messages
                WHERE embedding IS NOT NULL 
                AND LENGTH(message_text) > 20
                AND source = 'matt-gpt conversation'
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """
                
                with conn.cursor() as cur:
                    cur.execute(relevant_query, (embedding, limit))
                    results = cur.fetchall()
                    message_ids = [str(row[0]) for row in results]  # Return message IDs as strings
                    logger.debug(f"Query '{query[:30]}...' retrieved {len(message_ids)} message IDs")
                    return message_ids
                    
        except Exception as e:
            logger.error(f"Single query retrieval failed for '{query[:50]}...': {e}")
            return []
    
    def _rebuild_thread_contexts(self, message_ids: List[str]) -> List[str]:
        """Rebuild full thread contexts for the given message IDs"""
        if not message_ids:
            logger.warning("No message IDs provided to rebuild thread contexts")
            return []
            
        logger.debug(f"Rebuilding thread contexts for {len(message_ids)} message IDs")
        try:
            import psycopg
            from pgvector.psycopg import register_vector
            from collections import defaultdict
            
            with psycopg.connect(self.conn_string) as conn:
                register_vector(conn)
                
                with conn.cursor() as cur:
                    # Get thread_id and date for each message
                    thread_dates = set()
                    id_placeholders = ','.join(['%s'] * len(message_ids))
                    
                    thread_query = f"""
                    SELECT DISTINCT thread_id, DATE(timestamp) as date
                    FROM messages
                    WHERE id::text IN ({id_placeholders})
                    AND thread_id IS NOT NULL
                    """
                    
                    cur.execute(thread_query, message_ids)
                    thread_results = cur.fetchall()
                    for thread_id, date in thread_results:
                        thread_dates.add((thread_id, date))
                    
                    logger.debug(f"Found {len(thread_dates)} unique thread/date combinations from {len(message_ids)} message IDs")
                    
                    # Now get ALL messages from those thread/date combinations
                    all_context_messages = []
                    for thread_id, date in thread_dates:
                        context_query = """
                        SELECT message_text, timestamp, thread_id, meta_data, source, from_matt_gpt
                        FROM messages
                        WHERE thread_id = %s 
                        AND DATE(timestamp) = %s
                        ORDER BY timestamp
                        """
                        cur.execute(context_query, (thread_id, date))
                        thread_messages = cur.fetchall()
                        all_context_messages.extend(thread_messages)
                        logger.debug(f"Retrieved {len(thread_messages)} messages from thread {thread_id} on {date}")
                    
                    logger.debug(f"Total context messages retrieved: {len(all_context_messages)}")
            
            # Format messages using the same logic as the base retriever
            return self._format_messages_as_context(all_context_messages)
            
        except Exception as e:
            logger.error(f"Thread context rebuild failed: {e}")
            return []
    
    def _format_messages_as_context(self, all_context_messages: List[Tuple]) -> List[str]:
        """Format messages with the same logic as base retriever"""
        
        # Helper function to filter names for family only (copied from base retriever)
        def filter_sender_name(display_name: str, phone_number: str = "") -> str:
            """Filter sender names to only show family members, others become 'Someone:'"""
            if not display_name:
                display_name = phone_number
            
            # Replace Sisterr<3 with Danielle Brooks
            if display_name == "Sisterr<3":
                display_name = "Danielle Brooks"
            
            # Family names to keep
            family_names = {"Natalie Brooks", "Sarah Brooks", "Mom", "Dad", "Danielle Brooks"}
            
            if display_name in family_names:
                return display_name
            else:
                return "Someone"
        
        # Group and format messages by thread, date, and source type
        from collections import defaultdict
        grouped_messages = defaultdict(list)
        
        for text, timestamp, thread_id, meta_data, source, from_matt_gpt in all_context_messages:
            date_str = timestamp.date().strftime("%Y-%m-%d")
            
            # Determine sender name based on message source
            if source == "matt-gpt conversation":
                # Matt-GPT conversation message
                if from_matt_gpt:
                    sender_name = "Matt"
                else:
                    sender_name = "User"
                key = f"Matt-GPT Conversation {thread_id[-5:]} - {date_str}"
            else:
                # Text/Slack message
                if meta_data and isinstance(meta_data, dict):
                    display_name = meta_data.get('display_name', '')
                    sender_name = filter_sender_name(display_name)
                else:
                    sender_name = "Unknown"
                key = f"Thread {thread_id} - {date_str}"
            
            grouped_messages[key].append((timestamp, text, sender_name, source))

        # Format chronologically with thread/date headers
        formatted = []
        for thread_date, messages in sorted(grouped_messages.items()):
            formatted.append(f"\n=== {thread_date} ===")
            for timestamp, text, sender_name, source in sorted(messages):
                formatted.append(f"{sender_name}: {text}")
            formatted.append("")  # Add blank line between groups

        logger.debug(f"Formatted {len(formatted)} message contexts in {len(grouped_messages)} thread/date groups")
        return formatted
    
    def filter_relevant_context(
        self, 
        original_query: str, 
        all_context: List[str]
    ) -> Tuple[List[str], float, Optional[float]]:
        """
        Filter retrieved context to only include information relevant to answering the query.
        Uses 2025 SELF-RAG approach for intelligent relevance assessment.
        
        Returns:
            Tuple of (filtered_context, processing_time_ms, relevance_score)
        """
        start_time = time.time()
        
        if not all_context:
            return [], 0.0, None
        
        logger.info(f"Filtering {len(all_context)} context passages for relevance")
        
        # Format context for evaluation
        context_formatted = "\n\n---CONTEXT_SEPARATOR---\n\n".join(all_context)
        
        # Optimized filtering prompt based on 2025 SELF-RAG research
        filtering_prompt = f"""You are an intelligent context filter for a conversational AI system. Your task is to evaluate retrieved context and determine what would be helpful for answering the user's query.

EVALUATION CRITERIA:
✅ INCLUDE context that does any of the following:
- Relates to the query topic
- Provides relevant background or examples
- Contains Matt's perspective or experience on the topic
- Offers supporting details or explanations
- Shows similar situations or related discussions

❌ EXCLUDE context that:
- Is completely unrelated to the query
- Would confuse or dilute the response
- Discusses entirely different topics

ORIGINAL QUERY:
"{original_query}"

CONTEXT TO EVALUATE:
{context_formatted}

INSTRUCTIONS:
- For each piece of relevant context, output it EXACTLY as provided
- Separate each relevant piece with "---CONTEXT_SEPARATOR---"
- If no context is relevant, output "NO_RELEVANT_CONTEXT"
- Do not add commentary, explanations, or modifications
- Focus on context that would actually help answer the query"""

        try:
            client = self._get_system_client()
            messages = [{"role": "user", "content": filtering_prompt}]
            
            # Use temperature 0.1 for consistent, focused filtering
            response = client.chat_completion(
                messages=messages,
                model="anthropic/claude-sonnet-4", 
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse the filtered results
            if response_text == "NO_RELEVANT_CONTEXT":
                filtered_context = []
                relevance_score = 0.0
            else:
                # Split by separator and clean up
                filtered_parts = response_text.split("---CONTEXT_SEPARATOR---")
                filtered_context = []
                
                for part in filtered_parts:
                    cleaned = part.strip()
                    if cleaned and cleaned != "NO_RELEVANT_CONTEXT":
                        filtered_context.append(cleaned)
                
                # Calculate relevance score as ratio of kept vs original
                relevance_score = len(filtered_context) / len(all_context) if all_context else 0.0
            
            filtering_time = (time.time() - start_time) * 1000
            logger.info(f"Context filtering completed in {filtering_time:.2f}ms")
            logger.info(f"Filtered {len(all_context)} → {len(filtered_context)} contexts (relevance: {relevance_score:.2f})")
            
            return filtered_context, filtering_time, relevance_score
            
        except Exception as e:
            logger.error(f"Context filtering failed: {e}")
            # Fallback to original context
            filtering_time = (time.time() - start_time) * 1000
            return all_context, filtering_time, None
    
    def enhanced_retrieve(self, query: str, query_id: str) -> Tuple[List[str], EnhancedRagMetrics]:
        """
        Main enhanced RAG pipeline with query expansion, multi-retrieval, and context filtering.
        
        Returns:
            Tuple of (final_filtered_context, detailed_metrics)
        """
        pipeline_start = time.time()
        
        logger.info("=" * 60)
        logger.info(f"ENHANCED RAG PIPELINE STARTED: {query}")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Query Expansion
            logger.info("PHASE 1: Query Expansion")
            expanded_queries, expansion_time = self.expand_query(query)
            all_queries = [query] + expanded_queries  # Include original query
            logger.info(f"Generated {len(expanded_queries)} expanded queries in {expansion_time:.1f}ms:")
            for i, eq in enumerate(expanded_queries, 1):
                logger.info(f"  {i}. {eq}")
            
            # Phase 2: Multi-Query Retrieval  
            logger.info("PHASE 2: Multi-Query Retrieval")
            logger.info(f"Searching with {len(all_queries)} queries ({len(expanded_queries)} expanded + 1 original)")
            raw_context, retrieval_time, retrieval_stats = self.multi_query_retrieval(
                all_queries, messages_per_query=10
            )
            logger.info(f"Multi-query retrieval stats:")
            logger.info(f"  • Raw retrievals: {retrieval_stats['total_raw_retrievals']}")
            logger.info(f"  • Unique after dedup: {retrieval_stats['unique_messages']}")
            logger.info(f"  • Threads reconstructed: {retrieval_stats['threads_found']}")
            logger.info(f"  • Context passages created: {len(raw_context)}")
            
            # Phase 3: Context Filtering
            logger.info("PHASE 3: Context Filtering")
            if not raw_context:
                logger.warning("No raw context to filter - skipping filtering phase")
                filtered_context, filtering_time, relevance_score = [], 0.0, None
            else:
                logger.info(f"Filtering {len(raw_context)} context passages for relevance")
                filtered_context, filtering_time, relevance_score = self.filter_relevant_context(
                    query, raw_context
                )
                logger.info(f"Context filtering result:")
                logger.info(f"  • Before filtering: {len(raw_context)} passages")
                logger.info(f"  • After filtering: {len(filtered_context)} passages") 
                logger.info(f"  • Filtering ratio: {len(filtered_context)/len(raw_context)*100:.1f}%")
                logger.info(f"  • Relevance score: {relevance_score:.2f}" if relevance_score else "  • Relevance score: N/A")
            
            # Calculate total pipeline time
            total_time = (time.time() - pipeline_start) * 1000
            
            # Create comprehensive metrics
            metrics = EnhancedRagMetrics(
                original_query=query,
                expanded_queries=expanded_queries,
                query_expansion_ms=expansion_time,
                retrieval_ms=retrieval_time,
                filtering_ms=filtering_time,
                total_rag_ms=total_time,
                total_messages_retrieved=retrieval_stats['total_raw_retrievals'],
                unique_messages_after_dedup=retrieval_stats['unique_messages'],
                threads_reconstructed=retrieval_stats['threads_found'],
                messages_before_filtering=len(raw_context),
                messages_after_filtering=len(filtered_context),
                filtering_ratio=len(filtered_context) / len(raw_context) if raw_context else 0.0,
                raw_retrieved_context=raw_context,
                filtered_context=filtered_context,
                context_relevance_score=relevance_score,
                fallback_used=False
            )
            
            logger.info("=" * 60)
            logger.info("ENHANCED RAG PIPELINE COMPLETED")
            logger.info(f"Total Time: {total_time:.2f}ms")
            logger.info(f"Context: {len(raw_context)} → {len(filtered_context)} passages")
            logger.info(f"Relevance Score: {relevance_score:.2f}" if relevance_score else "Relevance Score: N/A")
            logger.info("=" * 60)
            
            return filtered_context, metrics
            
        except Exception as e:
            logger.error(f"Enhanced RAG pipeline failed: {e}")
            
            # Fallback to basic retrieval
            logger.warning("Falling back to basic RAG retrieval")
            try:
                basic_result = self.base_retriever(query)
                basic_context = basic_result.passages
                
                fallback_time = (time.time() - pipeline_start) * 1000
                
                # Create fallback metrics
                metrics = EnhancedRagMetrics(
                    original_query=query,
                    expanded_queries=[],
                    query_expansion_ms=0.0,
                    retrieval_ms=fallback_time,
                    filtering_ms=0.0,
                    total_rag_ms=fallback_time,
                    total_messages_retrieved=len(basic_context),
                    unique_messages_after_dedup=len(basic_context),
                    threads_reconstructed=0,
                    messages_before_filtering=len(basic_context),
                    messages_after_filtering=len(basic_context),
                    filtering_ratio=1.0,
                    raw_retrieved_context=basic_context,
                    filtered_context=basic_context,
                    fallback_used=True
                )
                
                logger.info(f"Fallback RAG completed in {fallback_time:.2f}ms")
                return basic_context, metrics
                
            except Exception as fallback_error:
                logger.error(f"Even fallback RAG failed: {fallback_error}")
                return [], EnhancedRagMetrics(
                    original_query=query,
                    expanded_queries=[],
                    query_expansion_ms=0.0,
                    retrieval_ms=0.0, 
                    filtering_ms=0.0,
                    total_rag_ms=0.0,
                    total_messages_retrieved=0,
                    unique_messages_after_dedup=0,
                    threads_reconstructed=0,
                    messages_before_filtering=0,
                    messages_after_filtering=0,
                    filtering_ratio=0.0,
                    raw_retrieved_context=[],
                    filtered_context=[],
                    fallback_used=True
                )
    
    def save_analytics(self, query_id: str, metrics: EnhancedRagMetrics):
        """Save detailed analytics to database for analysis and optimization"""
        try:
            with get_session() as session:
                analytics = RagAnalytics(
                    query_id=query_id,
                    original_query=metrics.original_query,
                    expanded_queries=metrics.expanded_queries,
                    total_messages_retrieved=metrics.total_messages_retrieved,
                    unique_messages_after_dedup=metrics.unique_messages_after_dedup,
                    threads_reconstructed=metrics.threads_reconstructed,
                    messages_before_filtering=metrics.messages_before_filtering,
                    messages_after_filtering=metrics.messages_after_filtering,
                    filtering_ratio=metrics.filtering_ratio,
                    raw_retrieved_context=metrics.raw_retrieved_context,
                    filtered_context=metrics.filtered_context,
                    query_expansion_ms=metrics.query_expansion_ms,
                    retrieval_ms=metrics.retrieval_ms,
                    filtering_ms=metrics.filtering_ms,
                    total_rag_ms=metrics.total_rag_ms,
                    context_relevance_score=metrics.context_relevance_score,
                    fallback_used=metrics.fallback_used
                )
                
                session.add(analytics)
                session.commit()
                logger.info(f"RAG analytics saved for query_id: {query_id}")
                
        except Exception as e:
            logger.error(f"Failed to save RAG analytics: {e}")
            # Don't raise - analytics failure shouldn't break the main flow
    
    def get_personality_docs_only(self, query: str) -> List[str]:
        """
        Get only personality documents, skipping message retrieval entirely.
        For personality-only mode when other_conversation_context=False.
        """
        logger.info(f"Retrieving personality docs only for query: {query}")
        
        try:
            # Use base retriever's logic but only for personality documents
            import psycopg
            from pgvector.psycopg import register_vector
            
            # Generate embedding for the query
            client = self._get_system_client()
            embedding = client.generate_embedding(query)
            
            with psycopg.connect(self.conn_string) as conn:
                register_vector(conn)
                
                # Query only personality documents
                personality_query = """
                SELECT message_text, timestamp, thread_id, meta_data, source
                FROM messages
                WHERE source = 'personality_docs'
                AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 20
                """
                
                with conn.cursor() as cur:
                    cur.execute(personality_query, (embedding,))
                    results = cur.fetchall()
                    
                    logger.info(f"Found {len(results)} personality documents")
                    
                    # Format as context passages
                    personality_docs = []
                    for text, timestamp, thread_id, meta_data, source in results:
                        # Format similar to regular context but mark as personality doc
                        formatted_doc = f"=== Personality Document ===\n{text}"
                        personality_docs.append(formatted_doc)
                    
                    return personality_docs
                    
        except Exception as e:
            logger.error(f"Failed to retrieve personality docs: {e}")
            return []