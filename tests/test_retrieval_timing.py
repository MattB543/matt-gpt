#!/usr/bin/env python3

import time
import logging
from database import get_session
from retrievers import PostgreSQLVectorRetriever
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_retrieval_performance():
    """Test how long retrieval takes"""
    logger.info("Testing retrieval performance...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found")
        return
    
    try:
        # Initialize retriever
        logger.info("Initializing retriever...")
        retriever = PostgreSQLVectorRetriever(connection_string=database_url, k=20)
        
        # Test query
        test_query = "How do you approach product development?"
        
        logger.info(f"Testing retrieval for query: {test_query}")
        start_time = time.time()
        
        # This is where the timeout might be happening
        result = retriever.forward(test_query)
        
        end_time = time.time()
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        
        logger.info(f"✅ Retrieval completed in {duration:.2f}ms")
        logger.info(f"Retrieved {len(result.passages)} passages")
        
        # Show first passage for verification
        if result.passages:
            logger.info(f"First passage preview: {result.passages[0][:100]}...")
        
        return duration
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Retrieval failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    test_retrieval_performance()