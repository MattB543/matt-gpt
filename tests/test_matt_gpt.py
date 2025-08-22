#!/usr/bin/env python3
"""Test the complete MattGPT DSPy system."""

import logging
from matt_gpt import setup_dspy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_matt_gpt_responses():
    """Test MattGPT end-to-end response generation"""
    logger.info("=== Testing MattGPT Response Generation ===")
    
    # Test questions that should trigger different types of responses
    test_questions = [
        "What's your philosophy on software development?",
        "How do you like to communicate with team members?",
        "What do you think about when building products for users?"
    ]
    
    try:
        # Setup MattGPT
        logger.info("Setting up MattGPT system...")
        matt_gpt = setup_dspy()
        logger.info("MattGPT system ready for testing")
        
        # Test each question
        for i, question in enumerate(test_questions):
            logger.info(f"\n--- Test Question {i+1}: {question} ---")
            
            try:
                logger.debug(f"Processing question: {question}")
                result = matt_gpt(question)
                
                response = result.response
                context_used = result.context_used
                
                logger.info(f"Response generated successfully")
                logger.info(f"Context items used: {len(context_used)}")
                logger.info(f"Response: {response[:200]}...")
                
                if len(response) > 10:  # Basic sanity check
                    logger.info("+ Response appears valid")
                else:
                    logger.warning("- Response seems too short")
                    
            except Exception as e:
                logger.error(f"Question {i+1} failed: {e}")
                
        logger.info("\n=== MattGPT Response Test Complete ===")
        
    except Exception as e:
        logger.error(f"MattGPT test failed: {e}")
        raise


if __name__ == "__main__":
    test_matt_gpt_responses()