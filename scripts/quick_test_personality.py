#!/usr/bin/env python3
"""Quick test of personality document retrieval system."""

import sys
from pathlib import Path
import logging

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from matt_gpt import setup_dspy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_personality_system():
    """Quick test of the personality document system"""
    
    logger.info("Setting up MattGPT system...")
    try:
        matt_gpt = setup_dspy()
        logger.info("✓ Setup successful")
    except Exception as e:
        logger.error(f"✗ Setup failed: {e}")
        return False
    
    # Test queries that should retrieve different personality docs
    test_queries = [
        ("What are your fundamental values?", "fundamental_values"),
        ("How do you approach learning?", "learning_and_development_style"), 
        ("What's your political philosophy?", "politics"),
        ("How do you handle trauma?", "trauma_and_healing_approach"),
        ("What's your spiritual approach?", "spiritual")
    ]
    
    passed_tests = 0
    total_tests = len(test_queries)
    
    for query, expected_doc_type in test_queries:
        logger.info(f"\nTesting: {query}")
        
        try:
            result = matt_gpt(query)
            
            # Count personality docs in the retrieved context
            personality_docs = [item for item in result.context_used 
                              if item.startswith("=== ") and " ===" in item]
            
            logger.info(f"  Response length: {len(result.response)} chars")
            logger.info(f"  Total context items: {len(result.context_used)}")
            logger.info(f"  Personality docs retrieved: {len(personality_docs)}")
            
            # Show which personality docs were retrieved
            if personality_docs:
                logger.info("  Personality docs:")
                for doc in personality_docs:
                    title = doc.split("=== ")[1].split(" ===")[0]
                    logger.info(f"    - {title}")
                passed_tests += 1
                logger.info("  ✓ Success: Retrieved personality docs")
            else:
                logger.warning("  ✗ No personality docs retrieved")
                
            # Show first 200 chars of response
            response_preview = result.response[:200] + "..." if len(result.response) > 200 else result.response
            logger.info(f"  Response preview: {response_preview}")
            
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
    
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"Tests passed: {passed_tests}/{total_tests}")
    logger.info(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Personality document system is working!")
        return True
    else:
        logger.warning(f"⚠️ {total_tests - passed_tests} tests failed")
        return False

if __name__ == "__main__":
    success = test_personality_system()
    sys.exit(0 if success else 1)