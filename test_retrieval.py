#!/usr/bin/env python3
"""Test the vector retrieval system."""

import os
import logging
from matt_gpt import setup_dspy
from retrievers import PostgreSQLVectorRetriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_vector_retrieval():
    """Test vector similarity retrieval"""
    logger.info("=== Testing Vector Retrieval System ===")
    
    # Test queries that should match our sample data
    test_queries = [
        "What's your approach to software development?",
        "How do you prefer to communicate with your team?", 
        "What matters most when building products?",
        "Can we schedule a meeting?"
    ]
    
    try:
        # Setup retriever
        logger.info("Setting up PostgreSQL vector retriever...")
        database_url = os.getenv("DATABASE_URL")
        retriever = PostgreSQLVectorRetriever(database_url, k=10)
        logger.info("Retriever setup complete")
        
        # Test each query
        for i, query in enumerate(test_queries):
            logger.info(f"\n--- Test Query {i+1}: {query} ---")
            
            try:
                result = retriever.forward(query)
                passages = result.passages
                
                logger.info(f"Retrieved {len(passages)} passages")
                
                # Show first few results
                for j, passage in enumerate(passages[:3]):
                    logger.info(f"  Passage {j+1}: {passage[:100]}...")
                    
            except Exception as e:
                logger.error(f"Query {i+1} failed: {e}")
                
        logger.info("\n=== Vector Retrieval Test Complete ===")
        
    except Exception as e:
        logger.error(f"Vector retrieval test failed: {e}")
        raise


if __name__ == "__main__":
    test_vector_retrieval()